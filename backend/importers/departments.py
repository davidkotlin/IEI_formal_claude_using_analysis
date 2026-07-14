"""
部門匯入：讀 employee Excel，依規則(A)填 users.department。
規則優先序：
  1. ASH 組（iei.com.tw 的 ash*/qsh*/iei_it）→ 上海
  2. @usa.ieiworld.com → 美國
  3. 特殊 8 人（ieiXXX@iei.com.tw）→ 轉成 XXX@ieiworld.com 查 Excel
  4. 其餘 @ieiworld.com → 直接查 Excel
  5. Excel 查無 → 不動（保留原值）
覆蓋原則：Excel 有的 email 以 Excel 為準覆蓋；Excel 沒有的（usa/ASH/查無）不受 Excel 影響，
          usa/ASH 由規則 1、2 主動填。
"""
import io
import openpyxl

from ..config import Config
import sqlite3

DB_PATH = Config.CLAUDE_DB_PATH

# 特殊 8 人：iei.com.tw 帳號 → 對應的 ieiworld.com（用來查 Excel）
SPECIAL_MAP = {
    "ieikevinpan@iei.com.tw":  "kevinpan@ieiworld.com",
    "ieiandyjrlin@iei.com.tw": "andyjrlin@ieiworld.com",
    "ieiskylan@iei.com.tw":    "skylan@ieiworld.com",
    "ieismartliao@iei.com.tw": "smartliao@ieiworld.com",
    "ieikimichang@iei.com.tw": "kimichang@ieiworld.com",
    "ieialanhsueh@iei.com.tw": "alanhsueh@ieiworld.com",
    "ieipeelchang@iei.com.tw": "peelchang@ieiworld.com",
    "ieilonghsu@iei.com.tw":   "longhsu@ieiworld.com",
}

DEPT_SHANGHAI = "上海"
DEPT_USA = "美國"
DEPT_BRITEMED = "百視美"


def parse_employee_excel(xlsx_bytes: bytes) -> dict:
    """
    讀 employee Excel，用表頭名稱定位欄位（不寫死欄號，容忍欄位順序/數量變動）。
    回傳 {email(lower): 部門名稱}。
    """
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes), data_only=True, read_only=True)
    ws = wb.active
    rows = ws.iter_rows(values_only=True)
    header = list(next(rows))

    def col_index(name):
        if name not in header:
            raise ValueError(f"Excel 缺少欄位「{name}」，實際表頭：{header}")
        return header.index(name)

    ci_email = col_index("email")
    ci_dept = col_index("部門名稱")

    mapping = {}
    for r in rows:
        if r is None or all(v is None for v in r):
            continue
        email = (r[ci_email] or "").strip().lower()
        dept = r[ci_dept]
        if email and dept:
            mapping[email] = str(dept).strip()
    return mapping


def resolve_department(email: str, group_id: int, excel_map: dict):
    """
    依規則(A)決定某人的部門。回傳部門字串，或 None（表示不動）。
    優先序：
      1. ASH 組（group_id == 1）→ 上海（整組，不論 email 網域，涵蓋 iei_it）
      2. @britemed.com.tw → 百視美
      3. @usa.ieiworld.com → 美國
      4. 特殊 8 人（ieiXXX@iei.com.tw）→ 轉 ieiworld 查 Excel
      5. 其餘 @ieiworld.com → 直接查 Excel
      6. 其他 → 不動
    """
    # 1. ASH 組整組上海（用 group 判，最準，iei_it 也涵蓋）
    if group_id == 1:
        return DEPT_SHANGHAI

    e = (email or "").strip().lower()
    if not e:
        return None
    local, _, domain = e.partition("@")

    # 2. britemed（百視美）
    if domain == "britemed.com.tw":
        return DEPT_BRITEMED

    # 3. usa → 美國
    if domain == "usa.ieiworld.com":
        return DEPT_USA

    # 4. 特殊 8 人 → 轉換後查 Excel
    if e in SPECIAL_MAP:
        return excel_map.get(SPECIAL_MAP[e])

    # 5. 其餘 ieiworld.com → 查 Excel
    if domain == "ieiworld.com":
        return excel_map.get(e)

    return None   # 其他網域 → 不動


def sync_departments(xlsx_bytes: bytes) -> dict:
    """
    主流程：讀 Excel → 對 db 內所有 users 套規則 → 更新 department。
    回傳統計：{updated, skipped, by_source:{excel, 上海, 美國}, excel_rows}
    """
    excel_map = parse_employee_excel(xlsx_bytes)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    users = cur.execute("SELECT uuid, email, group_id FROM users").fetchall()

    updated = 0
    skipped = 0
    src_excel = src_sh = src_usa = src_bm = 0

    for uuid, email, group_id in users:
        dept = resolve_department(email, group_id, excel_map)
        if dept is None:
            skipped += 1
            continue
        cur.execute("UPDATE users SET department = ? WHERE uuid = ?", (dept, uuid))
        updated += 1
        if dept == DEPT_SHANGHAI:
            src_sh += 1
        elif dept == DEPT_USA:
            src_usa += 1
        elif dept == DEPT_BRITEMED:
            src_bm += 1
        else:
            src_excel += 1

    conn.commit()
    conn.close()
    return {
        "updated": updated,
        "skipped": skipped,
        "excel_rows": len(excel_map),
        "by_source": {"excel": src_excel, "上海": src_sh, "美國": src_usa, "百視美": src_bm},
    }
