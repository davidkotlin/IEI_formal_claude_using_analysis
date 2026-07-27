"""
openai_departments.py（邏輯層，backend/importers/）
OpenAI 名單的部門匯入：讀「同一份」employee Excel，依 OpenAI 規則填 users.department。

與 Claude 的 departments.py 平行，差異：
- OpenAI 沒有 group_id，ASH 改用 email 判（@iei.com.tw 且 ash/qsh/ish 開頭）。
- 只有兩條規則，不含 特殊8 / britemed / usa。
- 寫入 openai.db（透過 openai_process.get_connection，非 monitor.db）。
- Excel 解析直接重用 Claude departments.py 的 parse_employee_excel（唯一來源，不複製一份）。

規則優先序：
  1. @iei.com.tw 且 local 以 ash/qsh/ish 開頭 → 上海
  2. @ieiworld.com → 查 Excel（查無→不動）
  3. 其他 → 不動（保留原值）
"""

from .departments import parse_employee_excel
from .openai_process import get_connection, init_db

DEPT_SHANGHAI = "上海"
ASH_PREFIXES = ("ash", "qsh", "ish")


def resolve_department(email: str, excel_map: dict):
    """
    依 OpenAI 規則決定某 email 的部門。回傳部門字串，或 None（表示不動）。
    excel_map 的 key 為 lower 過的 email（parse_employee_excel 的輸出）。
    """
    e = (email or "").strip().lower()
    if not e:
        return None
    local, _, domain = e.partition("@")

    # 1. ASH：iei.com.tw 且 ash/qsh/ish 開頭 → 上海
    if domain == "iei.com.tw" and local.startswith(ASH_PREFIXES):
        return DEPT_SHANGHAI

    # 2. ieiworld.com → 查 Excel（查無→回 None→不動）
    if domain == "ieiworld.com":
        return excel_map.get(e)

    # 3. 其他網域 → 不動
    return None


def sync_departments(xlsx_bytes: bytes) -> dict:
    """
    主流程：讀 Excel → 對 openai.db 內所有 users 套規則 → 更新 department。
    回傳統計：{updated, skipped, excel_rows, by_source:{excel, 上海}}
      - updated：實際被規則填值的人數
      - skipped：規則回 None（不動）的人數，含 ieiworld 但 Excel 查無者
      - excel_rows：Excel 解析到的有效列數
    """
    excel_map = parse_employee_excel(xlsx_bytes)

    init_db()  # 保底：確保 department 欄存在（新/舊 db 皆安全、冪等）
    conn = get_connection()
    cur = conn.cursor()
    users = cur.execute("SELECT email FROM users").fetchall()

    updated = 0
    skipped = 0
    src_excel = src_sh = 0

    for (email,) in users:
        dept = resolve_department(email, excel_map)
        if dept is None:
            skipped += 1
            continue
        cur.execute("UPDATE users SET department = ? WHERE email = ?", (dept, email))
        updated += 1
        if dept == DEPT_SHANGHAI:
            src_sh += 1
        else:
            src_excel += 1

    conn.commit()
    conn.close()
    return {
        "updated": updated,
        "skipped": skipped,
        "excel_rows": len(excel_map),
        "by_source": {"excel": src_excel, "上海": src_sh},
    }
