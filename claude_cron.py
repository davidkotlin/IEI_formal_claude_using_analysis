"""
cron_import.py
每週由 cron 定期執行，自動掃描三組各自的 incoming 資料夾並匯入 db。

三組資料夾（放對資料夾 = 打對 group，再加基準名單 90% 防呆雙保險）：
    data/claude_incoming_1/  -> group 1 (ASH)
    data/claude_incoming_2/  -> group 2 (David)
    data/claude_incoming_3/  -> group 3 (Alex)

crontab 範例（每週一早上 8 點執行）：
0 8 * * 1 /usr/bin/python3 /path/to/project/cron_import.py >> /var/log/claude_monitor.log 2>&1
"""

import logging
from pathlib import Path
from backend.importers.claude_process import init_db, import_from_bytes

# --- 設定 ---
DATA_DIR = Path(__file__).parent / "data"
GROUP_DIRS = {
    1: DATA_DIR / "claude_incoming_1",   # ASH
    2: DATA_DIR / "claude_incoming_2",   # David
    3: DATA_DIR / "claude_incoming_3",   # Alex
}
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger(__name__)


def find_json_pair(directory: Path):
    """
    在資料夾內尋找 users.json 與 conversations.json（支援根目錄與一層子資料夾）。
    回傳 list of (users_path, conv_path) tuple。
    """
    pairs = []

    users = directory / "users.json"
    conv = directory / "conversations.json"
    if users.exists() and conv.exists():
        pairs.append((users, conv))

    for sub in sorted(directory.iterdir()):
        if sub.is_dir():
            u = sub / "users.json"
            c = sub / "conversations.json"
            if u.exists() and c.exists():
                pairs.append((u, c))

    return pairs


def _process_group(group: int, incoming_dir: Path):
    """處理單一組的 incoming 資料夾。"""
    if not incoming_dir.exists():
        logger.warning(f"group{group} 資料夾不存在，跳過：{incoming_dir}")
        return

    pairs = find_json_pair(incoming_dir)
    if not pairs:
        logger.info(f"group{group}：未找到配對，跳過。")
        return

    for users_path, conv_path in pairs:
        logger.info(f"處理 group{group}：{users_path.parent}")
        try:
            users_bytes = users_path.read_bytes()
            conv_bytes = conv_path.read_bytes()

            result = import_from_bytes(users_bytes, conv_bytes, group)

            # 防呆拒絕（疑似匯錯組）→ 保留檔案、不刪，記錄錯誤讓人檢查
            if not result.get("ok", True):
                logger.error(
                    f"group{group} 匯入被拒絕（符合率 {result.get('match_rate')}）："
                    f"{result.get('message')}。保留檔案不刪，請檢查是否放錯資料夾。"
                )
                continue

            logger.info(
                f"group{group} 完成 - 新增對話 {result['conv_inserted']} 筆，"
                f"略過重複 {result['conv_skipped_dup']} 筆、"
                f"未知帳號 {result['conv_skipped_unknown']} 筆、"
                f"週末 {result['conv_skipped_weekend']} 筆、"
                f"空對話 {result['conv_skipped_empty']} 筆、"
                f"排除名單屏蔽 {result['users_excluded']} 人。"
            )

            users_path.unlink()
            conv_path.unlink()
            logger.info(f"已刪除：{users_path.name}, {conv_path.name}")

            if users_path.parent != incoming_dir:
                if not list(users_path.parent.iterdir()):
                    users_path.parent.rmdir()
                    logger.info(f"已刪除空資料夾：{users_path.parent.name}")

        except Exception as e:
            logger.error(f"group{group} 處理失敗：{e}")


def run():
    logger.info("=== cron_import 開始執行 ===")
    init_db()

    for group, incoming_dir in GROUP_DIRS.items():
        _process_group(group, incoming_dir)

    logger.info("=== cron_import 執行完畢 ===")


if __name__ == "__main__":
    run()
