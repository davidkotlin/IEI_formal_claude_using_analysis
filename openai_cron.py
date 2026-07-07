"""
openai_cron.py（cron 入口，位於專案根）
由 crontab 定期執行，掃描 data/openai_incoming 並匯入 openai.db。
解析/匯入邏輯都在 backend/importers/openai_import.py，本檔只負責「掃描 + 分派 + 記錄」。

crontab 範例：
0 8 * * 1 /path/to/venv/bin/python /path/to/openai_cron.py >> /var/log/openai_import.log 2>&1
"""

import logging
from pathlib import Path

from backend.importers.openai_process import init_db
from backend.importers.openai_import import (
    import_roster_xlsx,
    import_codex_from_path,
    import_web_from_path,
    extract_date_from_filename,
)

# --- 設定 ---
INCOMING_DIR = Path(__file__).parent / "data" / "openai_incoming"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger(__name__)


def _classify(path: Path) -> str:
    name = path.name.lower()
    if name.endswith((".xlsx", ".xls")) and "user" in name:
        return "roster"
    if name.endswith(".csv") and "codex" in name:
        return "codex"
    if name.endswith(".csv"):
        return "web"
    return "unknown"


def run():
    logger.info("=== openai_cron 開始執行 ===")

    if not INCOMING_DIR.exists():
        logger.error(f"openai_ncoming 資料夾不存在：{INCOMING_DIR}，請先建立並放入匯出檔。")
        return

    init_db()

    files = [p for p in sorted(INCOMING_DIR.rglob("*")) if p.is_file()]
    order = {"roster": 0, "codex": 1, "web": 2, "unknown": 9}   # 名單先進
    files.sort(key=lambda p: order[_classify(p)])

    processed = 0
    for path in files:
        kind = _classify(path)
        if kind == "unknown":
            logger.info(f"略過無法辨識的檔案：{path.name}")
            continue

        logger.info(f"處理 [{kind}]：{path.name}")
        try:
            if kind == "roster":
                result = import_roster_xlsx(path)
                logger.info(
                    f"名單完成 - 新增 {result['roster_inserted']}、"
                    f"更新 {result['roster_updated']}、略過 {result['roster_skipped']}。"
                )
                processed += 1   # 名單是母體來源，不刪除
                continue

            if kind == "codex":
                result = import_codex_from_path(path)
                logger.info(
                    f"Codex 完成 - 新增 {result['codex_inserted']} 筆、"
                    f"重複 {result['codex_skipped_dup']}、unknown {result['codex_skipped_unknown']}。"
                )
            else:  # web
                date = extract_date_from_filename(path)
                if not date:
                    logger.error(f"網頁版檔名無日期，略過：{path.name}")
                    continue
                result = import_web_from_path(path)
                logger.info(
                    f"網頁版 完成 ({date}) - 新增 {result['web_inserted']} 筆、"
                    f"重複 {result['web_skipped_dup']}、unknown {result['web_skipped_unknown']}。"
                )

            path.unlink()   # 用量檔匯入成功後刪除（資料已進 db）
            logger.info(f"已刪除：{path.name}")
            processed += 1

        except Exception as e:
            logger.error(f"處理失敗 {path.name}：{e}")

    logger.info(f"=== openai_cron 執行完畢，共處理 {processed} 個檔案 ===")


if __name__ == "__main__":
    run()
