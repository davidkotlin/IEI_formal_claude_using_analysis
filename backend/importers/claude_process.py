import json
import csv
import io
import sqlite3
from datetime import datetime, timedelta

from ..config import Config
DB_DIR = Config.DB_DIR
DB_PATH = Config.CLAUDE_DB_PATH

# ============================================================================
# ⚠️ group 編號對應（釘死，匯入時務必對應正確，否則排除名單會擋錯人）
#     group 1 = A 組     （iei.com.tw，ash/qsh 前綴，約 28 人）
#     group 2 = B 組     （ieiworld.com 為主，約 64 人）
#     group 3 = user1 組 （ieiworld.com + britemed，約 145 人，含 Alex Chien）
#   下方 EXCLUDED 的 key 依此對應；改動編號對應時，EXCLUDED 也要一起改。
# ============================================================================
# 臨時排除名單（待 IT 退帳號後移除）。key=group_id, value=該組要完全屏蔽的 email（不寫入 users，也不寫入 conversations/messages）
# 這 8 人跨兩組，各自歸屬已定：被排除的那組當空氣。Silver 兩組都排除。
EXCLUDED = {
    1: set(),
    2: {  # B 組（group2）：這些人歸 user1，從 B 屏蔽
        "duncanchiang@ieiworld.com",
        "harrietkao@ieiworld.com",
        "sam2cheng@ieiworld.com",
        "silverchu@ieiworld.com",
    },
    3: {  # user1 組（group3）：這些人歸 B，從 user1 屏蔽
        "dennishsu@ieiworld.com",
        "shinefan@ieiworld.com",
        "thomasliu@ieiworld.com",
        "evachang@ieiworld.com",
        "silverchu@ieiworld.com",
    },
}


def get_connection():
    DB_DIR.mkdir(exist_ok=True)
    return sqlite3.connect(DB_PATH)


def get_roster_emails(group: int) -> set:
    """取這組現有基準名單的 email 集合（users 表 group_id=該組）。"""
    conn = get_connection()
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT email FROM users WHERE group_id = ?", (group,)
    ).fetchall()
    conn.close()
    return {r[0].strip().lower() for r in rows if r[0]}


# 匯錯組防呆門檻：進來的名單，須有 >= 此比例在現有基準裡，否則視為匯錯組拒絕
ROSTER_MATCH_THRESHOLD = 0.80


def check_roster_match(users_data: list, group: int) -> dict:
    """
    檢查這批 users.json 是否屬於 group（防匯錯組）。
    規則：
      - 先套排除名單（被排除的人不算入分母）。
      - 現有基準為空 → 第一次匯入，直接放行（這批即初始基準）。
      - 基準非空 → 符合率 = 進來的人在基準裡的比例；>= 門檻放行，否則拒絕。
    回傳 {"ok": bool, "reason": str, "match_rate": float, "existing": int, "incoming": int}
    """
    excluded = EXCLUDED.get(group, set())
    incoming = {
        u["email_address"].strip().lower()
        for u in users_data
        if u.get("email_address") and u["email_address"].strip().lower() not in excluded
    }
    existing = get_roster_emails(group)

    # 第一次：基準空 → 放行建立基準
    if not existing:
        return {"ok": True, "reason": "first_import", "match_rate": 1.0,
                "existing": 0, "incoming": len(incoming)}

    if not incoming:
        return {"ok": False, "reason": "empty_after_exclude", "match_rate": 0.0,
                "existing": len(existing), "incoming": 0}

    matched = len(incoming & existing)
    rate = matched / len(incoming)
    ok = rate >= ROSTER_MATCH_THRESHOLD
    return {"ok": ok, "reason": "match" if ok else "low_match",
            "match_rate": round(rate, 3), "existing": len(existing), "incoming": len(incoming)}


def init_db():
    """建立資料表（若不存在）"""
    conn = get_connection()
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            uuid      TEXT PRIMARY KEY,
            full_name TEXT,
            email     TEXT,
            group_id  INTEGER,
            department TEXT
        );

        CREATE TABLE IF NOT EXISTS conversations (
            uuid           TEXT PRIMARY KEY,
            user_uuid      TEXT,
            name           TEXT,
            created_at_tw  TEXT,
            updated_at_tw  TEXT,
            duration_min   REAL,
            total_messages INTEGER,
            tool_use_count INTEGER,
            weekday        INTEGER,
            hour           INTEGER,
            date           TEXT,
            group_id       INTEGER,
            FOREIGN KEY (user_uuid) REFERENCES users(uuid)
        );

        CREATE TABLE IF NOT EXISTS messages (
            uuid              TEXT PRIMARY KEY,
            conversation_uuid TEXT,
            sender            TEXT,
            created_at_tw     TEXT,
            date              TEXT,
            hour              INTEGER,
            tool_use_count    INTEGER DEFAULT 0,
            group_id          INTEGER,
            FOREIGN KEY (conversation_uuid) REFERENCES conversations(uuid)
        );

        -- 索引：加速依日期篩選訊息
        CREATE INDEX IF NOT EXISTS idx_messages_date
            ON messages(date);

        -- 索引：加速依對話 UUID 查詢訊息
        CREATE INDEX IF NOT EXISTS idx_messages_conversation_uuid
            ON messages(conversation_uuid);

        -- 索引：加速依日期篩選對話
        CREATE INDEX IF NOT EXISTS idx_conversations_date
            ON conversations(date);

        -- 索引：加速依組別篩選（三組切換的核心）
        CREATE INDEX IF NOT EXISTS idx_users_group ON users(group_id);
        CREATE INDEX IF NOT EXISTS idx_conversations_group ON conversations(group_id);
        CREATE INDEX IF NOT EXISTS idx_messages_group ON messages(group_id);

        -- CSV 修正資料（members-analytics 官方後台匯出，用來修正 json 漏抓）。
        -- 旁掛參照表，與 users/conversations/messages 無關聯、不影響主流程；整批覆蓋（全量快照）。
        CREATE TABLE IF NOT EXISTS member_analytics (
            email           TEXT PRIMARY KEY,
            last_active     TEXT,           -- YYYY-MM-DD，官方後台的「最後有動作日」
            chats           INTEGER DEFAULT 0,
            code_sessions   INTEGER DEFAULT 0,
            cowork_sessions INTEGER DEFAULT 0
        );
    """)

    conn.commit()
    conn.close()


def import_users(users_data: list, group: int) -> tuple:
    """
    寫入 users（帶 group_id），已存在的跳過，排除名單的 email 直接屏蔽不寫。
    回傳 (mapping, inserted, skipped, excluded)。mapping = {uuid: full_name}（不含被排除者）。
    """
    conn = get_connection()
    cur = conn.cursor()

    excluded_emails = EXCLUDED.get(group, set())
    inserted = 0
    skipped = 0
    excluded = 0
    mapping = {}

    for user in users_data:
        uuid = user.get("uuid")
        if not uuid:
            continue
        full_name = user.get("full_name", "")
        email = user.get("email_address", "")

        # 排除名單：這組要屏蔽的人，連基準名單都不寫（之後對話也會因不在 mapping 而自動跳過）
        if email.strip().lower() in excluded_emails:
            excluded += 1
            continue

        mapping[uuid] = full_name

        cur.execute(
            "INSERT OR IGNORE INTO users (uuid, full_name, email, group_id) VALUES (?, ?, ?, ?)",
            (uuid, full_name, email, group)
        )
        if cur.rowcount == 1:
            inserted += 1
        else:
            skipped += 1

    conn.commit()
    conn.close()
    return mapping, inserted, skipped, excluded


def import_conversations(conv_data: list, user_mapping: dict, group: int) -> tuple:
    """
    寫入 conversations 與 messages（帶 group_id），已存在的跳過，不在 user_mapping 的跳過。
    被排除名單屏蔽的人已不在 user_mapping，故其對話會自動落入 skipped_unknown 被跳過。
    只處理週一至週五。
    """
    conn = get_connection()
    cur = conn.cursor()

    inserted = 0
    skipped_dup = 0
    skipped_unknown = 0
    skipped_weekend = 0
    skipped_empty = 0

    for chat in conv_data:
        uuid = chat.get("uuid")
        if not uuid:
            continue

        account_uuid = chat.get("account", {}).get("uuid", "")
        if account_uuid not in user_mapping:
            skipped_unknown += 1
            continue

        created_at = chat.get("created_at", "")
        updated_at = chat.get("updated_at", "")
        if not created_at or not updated_at:
            continue

        t_start = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        t_end = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        t_start_tw = t_start + timedelta(hours=8)
        t_end_tw = t_end + timedelta(hours=8)

        # 註：原本會排除週末對話，現已移除——目的是看員工是否有在使用，
        #     假日使用同樣算數，不應被過濾（skipped_weekend 保留為 0 以相容回傳格式）。

        messages = chat.get("chat_messages", [])
        total_messages = len(messages)
        tool_use_count = 0
        human_char_length = 0

        for m in messages:
            if m.get("sender") == "human":
                human_char_length += len(m.get("text", ""))
            for block in m.get("content", []):
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    tool_use_count += 1

        # 剃除空對話
        name = chat.get("name", "")
        if not name and human_char_length == 0 and tool_use_count == 0:
            skipped_empty += 1
            continue

        duration_min = round((t_end - t_start).total_seconds() / 60, 1)

        cur.execute(
            """INSERT OR IGNORE INTO conversations
               (uuid, user_uuid, name, created_at_tw, updated_at_tw,
                duration_min, total_messages, tool_use_count, weekday, hour, date, group_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                uuid,
                account_uuid,
                name if name else "未命名對話",
                t_start_tw.strftime("%Y-%m-%d %H:%M:%S"),
                t_end_tw.strftime("%Y-%m-%d %H:%M:%S"),
                duration_min,
                total_messages,
                tool_use_count,
                t_start_tw.weekday(),
                t_start_tw.hour,
                t_start_tw.strftime("%Y-%m-%d"),
                group,
            )
        )

        if cur.rowcount == 1:
            inserted += 1
            # 寫入 messages
            for m in messages:
                msg_uuid = m.get("uuid")
                if not msg_uuid:
                    continue

                sender = m.get("sender", "")
                msg_created = m.get("created_at", "")
                if not msg_created:
                    continue

                t_msg = datetime.fromisoformat(msg_created.replace("Z", "+00:00"))
                t_msg_tw = t_msg + timedelta(hours=8)

                msg_tool_count = sum(
                    1 for block in m.get("content", [])
                    if isinstance(block, dict) and block.get("type") == "tool_use"
                )

                cur.execute(
                    """INSERT OR IGNORE INTO messages
                       (uuid, conversation_uuid, sender, created_at_tw, date, hour, tool_use_count, group_id)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        msg_uuid,
                        uuid,
                        sender,
                        t_msg_tw.strftime("%Y-%m-%d %H:%M:%S"),
                        t_msg_tw.strftime("%Y-%m-%d"),
                        t_msg_tw.hour,
                        msg_tool_count,
                        group,
                    )
                )
        else:
            skipped_dup += 1

    conn.commit()
    conn.close()
    return inserted, skipped_dup, skipped_unknown, skipped_weekend, skipped_empty


def db_exists() -> bool:
    return DB_PATH.exists()


def import_member_analytics_from_bytes(csv_bytes: bytes) -> dict:
    """
    匯入 members-analytics CSV（官方後台匯出，用來修正 json 漏抓，手動上傳、不進 cron）。
    整批覆蓋（全量快照）：先清空 member_analytics 再寫入。
    只留分類會用到的欄位：Email / Last Active / Chats / Code sessions / Cowork Sessions。
    用表頭名定位（不寫死欄號、大小寫容忍），缺 Chats/Code/Cowork 欄者以 0 計。
    回傳 {"rows": 寫入筆數, "with_activity": 有活動筆數}。
    """
    init_db()   # 保底：確保 member_analytics 表存在

    text = csv_bytes.decode("utf-8-sig", errors="replace")   # utf-8-sig 吃掉 BOM
    reader = csv.reader(io.StringIO(text))
    header = next(reader, [])
    norm = [(h or "").strip().lower() for h in header]

    def col(name):
        n = name.strip().lower()
        return norm.index(n) if n in norm else None

    ci_email = col("email")
    ci_la = col("last active")
    ci_chats = col("chats")
    ci_code = col("code sessions")
    ci_cowork = col("cowork sessions")
    if ci_email is None or ci_la is None:
        raise ValueError(f"CSV 缺少必要欄位（需要 Email 與 Last Active），實際表頭：{header}")

    def _int(v):
        try:
            return int(float(str(v).strip() or 0))
        except (ValueError, TypeError):
            return 0

    def _get(row, idx):
        return row[idx] if idx is not None and idx < len(row) else None

    rows = []
    for r in reader:
        if not r:
            continue
        email = (_get(r, ci_email) or "").strip().lower()
        if not email:
            continue
        rows.append((
            email,
            (_get(r, ci_la) or "").strip(),
            _int(_get(r, ci_chats)),
            _int(_get(r, ci_code)),
            _int(_get(r, ci_cowork)),
        ))

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM member_analytics")   # 全量快照：先清空再寫
    cur.executemany(
        """INSERT OR REPLACE INTO member_analytics
           (email, last_active, chats, code_sessions, cowork_sessions)
           VALUES (?, ?, ?, ?, ?)""",
        rows,
    )
    conn.commit()
    conn.close()

    with_activity = sum(
        1 for (_e, la, c, cs, cw) in rows if la and (c > 0 or cs > 0 or cw > 0)
    )
    return {"rows": len(rows), "with_activity": with_activity}


def update_user_name(uuid: str, full_name: str, group: int) -> bool:
    """改名：更新某人在該組的 full_name。回傳是否有更新到（找得到人）。"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET full_name = ? WHERE uuid = ? AND group_id = ?",
        (full_name, uuid, group)
    )
    changed = cur.rowcount
    conn.commit()
    conn.close()
    return changed > 0


def update_user_department(uuid: str, department: str, group: int) -> bool:
    """改部門：更新某人在該組的 department（手動單筆）。空字串視為清空。"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET department = ? WHERE uuid = ? AND group_id = ?",
        (department or None, uuid, group)
    )
    changed = cur.rowcount
    conn.commit()
    conn.close()
    return changed > 0


def delete_user_cascade(uuid: str, group: int) -> dict:
    """
    級聯全刪：刪除某人在該組的 messages -> conversations -> user 本身。
    依外鍵順序（由子到父）刪，全部限定 group，不影響其他組。
    回傳各層刪除筆數。
    """
    conn = get_connection()
    cur = conn.cursor()

    # 先找出這人在這組的所有對話 uuid（messages 要靠它刪）
    conv_uuids = [r[0] for r in cur.execute(
        "SELECT uuid FROM conversations WHERE user_uuid = ? AND group_id = ?",
        (uuid, group)
    ).fetchall()]

    msg_deleted = 0
    if conv_uuids:
        placeholders = ",".join("?" * len(conv_uuids))
        cur.execute(
            f"DELETE FROM messages WHERE conversation_uuid IN ({placeholders}) AND group_id = ?",
            (*conv_uuids, group)
        )
        msg_deleted = cur.rowcount

    cur.execute(
        "DELETE FROM conversations WHERE user_uuid = ? AND group_id = ?",
        (uuid, group)
    )
    conv_deleted = cur.rowcount

    cur.execute(
        "DELETE FROM users WHERE uuid = ? AND group_id = ?",
        (uuid, group)
    )
    user_deleted = cur.rowcount

    conn.commit()
    conn.close()
    return {"user_deleted": user_deleted, "conv_deleted": conv_deleted, "msg_deleted": msg_deleted}


def load_all_data() -> tuple:
    """
    從 db 讀取所有資料，回傳：
    - users: list of dict
    - conversations: list of dict
    """
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM users")
    users = [dict(row) for row in cur.fetchall()]

    cur.execute("""
        SELECT c.*, u.full_name, u.email
        FROM conversations c
        LEFT JOIN users u ON c.user_uuid = u.uuid
    """)
    conversations = [dict(row) for row in cur.fetchall()]

    conn.close()
    return users, conversations


def import_from_bytes(users_bytes: bytes, conv_bytes: bytes, group: int) -> dict:
    """
    接收上傳的 bytes，解析 JSON 並寫入 db（指定 group）。
    先做基準符合率防呆：不符（疑似匯錯組）則整批拒絕，什麼都不寫。
    回傳各項統計數字（或 ok=False 的拒絕結果）。
    """
    init_db()

    users_data = json.loads(users_bytes)
    conv_data = json.loads(conv_bytes)

    # --- 防呆：這批 users 是否屬於 group ---
    chk = check_roster_match(users_data, group)
    if not chk["ok"]:
        return {
            "ok": False,
            "group": group,
            "match_rate": chk["match_rate"],
            "reason": chk["reason"],
            "existing_roster": chk["existing"],
            "incoming": chk["incoming"],
            "message": (
                f"匯入被拒絕：這批名單只有 {chk['match_rate']*100:.0f}% 符合 group{group} 的基準名單"
                f"（現有基準 {chk['existing']} 人）。可能匯錯組，或忘了更新基準名單。"
                if chk["reason"] == "low_match"
                else "匯入被拒絕：排除名單套用後沒有可匯入的人。"
            ),
        }

    user_mapping, u_inserted, u_skipped, u_excluded = import_users(users_data, group)

    c_inserted, c_dup, c_unknown, c_weekend, c_empty = import_conversations(
        conv_data, user_mapping, group
    )

    return {
        "ok": True,
        "group": group,
        "match_rate": chk["match_rate"],
        "first_import": chk["reason"] == "first_import",
        "users_inserted": u_inserted,
        "users_skipped": u_skipped,
        "users_excluded": u_excluded,
        "conv_inserted": c_inserted,
        "conv_skipped_dup": c_dup,
        "conv_skipped_unknown": c_unknown,
        "conv_skipped_weekend": c_weekend,
        "conv_skipped_empty": c_empty,
    }
