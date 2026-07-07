"""
cron_import.py
每週由 cron 定期執行，自動掃描 claude_incoming 資料夾並匯入 db。

crontab 範例（每週一早上 8 點執行）：
0 8 * * 1 /usr/bin/python3 /path/to/project/cron_import.py >> /var/log/claude_monitor.log 2>&1
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from backend.importers.claude_process import init_db, import_from_bytes

# --- 設定 ---
INCOMING_DIR = Path(__file__).parent / "data" / "claude_incoming"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger(__name__)


def find_json_pair(directory: Path):
    """
    在資料夾內尋找 users.json 與 conversations.json。
    支援子資料夾（例如每次匯出放在獨立資料夾）。
    回傳 list of (users_path, conv_path) tuple。
    """
    pairs = []

    # 先找根目錄
    users = directory / "users.json"
    conv = directory / "conversations.json"
    if users.exists() and conv.exists():
        pairs.append((users, conv))

    # 再找一層子資料夾
    for sub in sorted(directory.iterdir()):
        if sub.is_dir():
            u = sub / "users.json"
            c = sub / "conversations.json"
            if u.exists() and c.exists():
                pairs.append((u, c))

    return pairs


def run():
    logger.info("=== cron_import 開始執行 ===")

    if not INCOMING_DIR.exists():
        logger.error(f"claude_incoming 資料夾不存在：{INCOMING_DIR}，請先建立並掛載 NAS。")
        return

    # 確保 db 存在
    init_db()

    pairs = find_json_pair(INCOMING_DIR)
    if not pairs:
        logger.info("未找到任何 users.json + conversations.json 配對，結束。")
        return

    for users_path, conv_path in pairs:
        logger.info(f"處理：{users_path.parent}")
        try:
            users_bytes = users_path.read_bytes()
            conv_bytes = conv_path.read_bytes()

            result = import_from_bytes(users_bytes, conv_bytes)

            logger.info(
                f"完成 - 新增對話 {result['conv_inserted']} 筆，"
                f"略過重複 {result['conv_skipped_dup']} 筆、"
                f"未知帳號 {result['conv_skipped_unknown']} 筆、"
                f"週末 {result['conv_skipped_weekend']} 筆、"
                f"空對話 {result['conv_skipped_empty']} 筆。"
            )

            # 匯入成功後刪除 JSON
            users_path.unlink()
            conv_path.unlink()
            logger.info(f"已刪除：{users_path.name}, {conv_path.name}")

            # 若是子資料夾且已空則刪除資料夾
            if users_path.parent != INCOMING_DIR:
                remaining = list(users_path.parent.iterdir())
                if not remaining:
                    users_path.parent.rmdir()
                    logger.info(f"已刪除空資料夾：{users_path.parent.name}")

        except Exception as e:
            logger.error(f"處理失敗：{e}")

    logger.info("=== cron_import 執行完畢 ===")


if __name__ == "__main__":
    run()
