"""
openai_process.py
OpenAI（Business 方案）使用分析的資料庫層，與 Claude 的 db_process.py 平行、互不干擾。

設計重點：
- 獨立資料庫檔 openai.db，完全不碰 Claude 的 monitor.db。
- 三張表：users（手動維護的名單，母體）、codex_daily、web_daily。
- 跨三個來源（名單 / Codex CSV / web CSV）唯一共同欄位是 email，故以 email 為主鍵與 join key。
- user_id（user-XXXX）為選填屬性，從使用資料自動回填，沒用過的人可為空。
- total token = uncached + cached + output，屬衍生值，不落表，查詢時再算。
- 名單是母體：使用資料中 email 不在 users 者，視為 unknown 直接略過
  （對應 Claude pipeline 的 skipped_unknown，柳絮那類 gmail 會自動被擋掉）。
"""

import sqlite3

from ..config import Config

DB_DIR = Config.DB_DIR
DB_PATH = Config.OPENAI_DB_PATH


def get_connection():
    DB_DIR.mkdir(exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    """建立資料表（若不存在）"""
    conn = get_connection()
    cur = conn.cursor()

    cur.executescript("""
        -- 名單 / 母體，由人工維護（Excel 匯入或前端輸入框皆走同一組 CRUD）
        CREATE TABLE IF NOT EXISTS users (
            email    TEXT PRIMARY KEY,
            name     TEXT,
            user_id  TEXT,              -- user-XXXX，OpenAI 內部 id，選填，自使用資料回填
            active   INTEGER DEFAULT 1  -- 1=在職/在追蹤，0=停用（保留歷史但排除於母體）
        );

        -- Codex 每日用量（CSV 每列自帶 date）
        CREATE TABLE IF NOT EXISTS codex_daily (
            email          TEXT,
            date           TEXT,        -- YYYY-MM-DD
            uncached_input INTEGER DEFAULT 0,
            cached_input   INTEGER DEFAULT 0,
            output         INTEGER DEFAULT 0,
            n_sessions     INTEGER DEFAULT 0,
            n_messages     INTEGER DEFAULT 0,
            PRIMARY KEY (email, date),
            FOREIGN KEY (email) REFERENCES users(email)
        );

        -- 網頁版每日用量（CSV 無日期欄，date 由匯入時從檔名帶入）
        CREATE TABLE IF NOT EXISTS web_daily (
            email  TEXT,
            date   TEXT,                -- YYYY-MM-DD
            tokens INTEGER DEFAULT 0,
            PRIMARY KEY (email, date),
            FOREIGN KEY (email) REFERENCES users(email)
        );

        CREATE INDEX IF NOT EXISTS idx_codex_daily_date ON codex_daily(date);
        CREATE INDEX IF NOT EXISTS idx_web_daily_date   ON web_daily(date);
    """)

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# users 表 CRUD
#   名單是人工維護的，故提供完整增/查/改/刪。
#   Excel 匯入與（未來的）前端輸入框都應呼叫這組函式，不各自寫 SQL。
# ---------------------------------------------------------------------------

def add_user(email: str, name: str = "", user_id: str = None, active: int = 1) -> bool:
    """新增一位使用者。email 已存在則不動（回傳 False）。"""
    email = (email or "").strip()
    if not email:
        return False
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO users (email, name, user_id, active) VALUES (?, ?, ?, ?)",
        (email, (name or "").strip(), user_id, active),
    )
    inserted = cur.rowcount == 1
    conn.commit()
    conn.close()
    return inserted


def upsert_user_from_roster(email: str, name: str = "") -> str:
    """
    名單匯入專用：email 不存在則新增；已存在則以名單的 name 為準覆寫。
    名單是 name 的權威來源（使用資料裡的 name 較髒，不拿來覆寫）。
    回傳 'inserted' 或 'updated'。
    """
    email = (email or "").strip()
    name = (name or "").strip()
    if not email:
        return "skipped"
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM users WHERE email = ?", (email,))
    exists = cur.fetchone() is not None
    if exists:
        cur.execute("UPDATE users SET name = ? WHERE email = ?", (name, email))
        result = "updated"
    else:
        cur.execute(
            "INSERT INTO users (email, name, active) VALUES (?, ?, 1)",
            (email, name),
        )
        result = "inserted"
    conn.commit()
    conn.close()
    return result


def backfill_user_id(cur, email: str, user_id: str):
    """
    使用資料回填 user_id：僅在目前為空時填入，不覆寫既有值。
    傳入既有 cursor 以便包在同一個交易內（供匯入迴圈呼叫）。
    """
    if not user_id:
        return
    cur.execute(
        "UPDATE users SET user_id = ? WHERE email = ? AND (user_id IS NULL OR user_id = '')",
        (user_id, email),
    )


def get_user(email: str) -> dict:
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = ?", ((email or "").strip(),))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_users(active_only: bool = False) -> list:
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    sql = "SELECT * FROM users"
    if active_only:
        sql += " WHERE active = 1"
    sql += " ORDER BY email"
    cur.execute(sql)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def update_user(email: str, name: str = None, active: int = None) -> bool:
    """更新姓名或啟用狀態；只更新有帶入的欄位。"""
    email = (email or "").strip()
    fields, params = [], []
    if name is not None:
        fields.append("name = ?")
        params.append(name.strip())
    if active is not None:
        fields.append("active = ?")
        params.append(int(active))
    if not fields:
        return False
    params.append(email)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"UPDATE users SET {', '.join(fields)} WHERE email = ?", params)
    changed = cur.rowcount == 1
    conn.commit()
    conn.close()
    return changed


def delete_user(email: str, cascade: bool = False) -> bool:
    """
    刪除名單中的一位使用者。
    cascade=True 時連同其 codex_daily / web_daily 用量一併刪除；
    預設 False（保留歷史用量，只把人從名單移除）。
    """
    email = (email or "").strip()
    conn = get_connection()
    cur = conn.cursor()
    if cascade:
        cur.execute("DELETE FROM codex_daily WHERE email = ?", (email,))
        cur.execute("DELETE FROM web_daily WHERE email = ?", (email,))
    cur.execute("DELETE FROM users WHERE email = ?", (email,))
    deleted = cur.rowcount == 1
    conn.commit()
    conn.close()
    return deleted


def _known_emails(cur) -> set:
    cur.execute("SELECT email FROM users")
    return {r[0] for r in cur.fetchall()}


# ---------------------------------------------------------------------------
# 用量匯入
#   接收「已解析好的列」（解析與檔名日期邏輯放在 openai_import.py）。
#   email 不在 users（名單）者一律略過並計入 skipped_unknown。
# ---------------------------------------------------------------------------

def import_codex_daily(rows: list) -> dict:
    """
    寫入 codex_daily。每列 dict 需含：
      email, date, uncached_input, cached_input, output, n_sessions, n_messages, user_id(選填)
    以 (email, date) 為主鍵，重複則略過。
    """
    conn = get_connection()
    cur = conn.cursor()
    known = _known_emails(cur)

    inserted = skipped_dup = skipped_unknown = 0

    for r in rows:
        email = (r.get("email") or "").strip()
        date = (r.get("date") or "").strip()
        if not email or not date:
            continue
        if email not in known:
            skipped_unknown += 1
            continue

        cur.execute(
            """INSERT OR IGNORE INTO codex_daily
               (email, date, uncached_input, cached_input, output, n_sessions, n_messages)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                email, date,
                int(r.get("uncached_input", 0) or 0),
                int(r.get("cached_input", 0) or 0),
                int(r.get("output", 0) or 0),
                int(r.get("n_sessions", 0) or 0),
                int(r.get("n_messages", 0) or 0),
            ),
        )
        if cur.rowcount == 1:
            inserted += 1
            backfill_user_id(cur, email, r.get("user_id"))
        else:
            skipped_dup += 1

    conn.commit()
    conn.close()
    return {
        "codex_inserted": inserted,
        "codex_skipped_dup": skipped_dup,
        "codex_skipped_unknown": skipped_unknown,
    }


def import_web_daily(rows: list) -> dict:
    """
    寫入 web_daily。每列 dict 需含：email, date, tokens, user_id(選填)
    date 由 openai_import.py 從檔名帶入後放進每列。
    """
    conn = get_connection()
    cur = conn.cursor()
    known = _known_emails(cur)

    inserted = skipped_dup = skipped_unknown = 0

    for r in rows:
        email = (r.get("email") or "").strip()
        date = (r.get("date") or "").strip()
        if not email or not date:
            continue
        if email not in known:
            skipped_unknown += 1
            continue

        cur.execute(
            "INSERT OR IGNORE INTO web_daily (email, date, tokens) VALUES (?, ?, ?)",
            (email, date, int(r.get("tokens", 0) or 0)),
        )
        if cur.rowcount == 1:
            inserted += 1
            backfill_user_id(cur, email, r.get("user_id"))
        else:
            skipped_dup += 1

    conn.commit()
    conn.close()
    return {
        "web_inserted": inserted,
        "web_skipped_dup": skipped_dup,
        "web_skipped_unknown": skipped_unknown,
    }


def db_exists() -> bool:
    return DB_PATH.exists()


# ---------------------------------------------------------------------------
# 讀取（統計與 route 之後再擴充；此處先給基本 load 與一個「誰沒用」範例）
# ---------------------------------------------------------------------------

def load_all_data() -> tuple:
    """回傳 (users, codex_daily, web_daily) 三個 list of dict。"""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM users ORDER BY email")
    users = [dict(r) for r in cur.fetchall()]

    cur.execute("SELECT * FROM codex_daily ORDER BY date, email")
    codex = [dict(r) for r in cur.fetchall()]

    cur.execute("SELECT * FROM web_daily ORDER BY date, email")
    web = [dict(r) for r in cur.fetchall()]

    conn.close()
    return users, codex, web


def who_didnt_use(date: str, source: str = "codex") -> list:
    """
    回傳指定日期「有在名單(active)但當天該來源沒用」的人。
    source: 'codex' 或 'web'。這是顯示層「誰沒用」的核心查詢雛形。
    """
    table = "codex_daily" if source == "codex" else "web_daily"
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT u.email, u.name
        FROM users u
        WHERE u.active = 1
          AND u.email NOT IN (
              SELECT email FROM {table} WHERE date = ?
          )
        ORDER BY u.email
        """,
        (date,),
    )
    result = [dict(r) for r in cur.fetchall()]
    conn.close()
    return result
