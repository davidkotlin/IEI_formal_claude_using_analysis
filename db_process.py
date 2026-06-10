import json
import sqlite3
import os
from datetime import datetime, timedelta
from pathlib import Path

DB_DIR = Path(__file__).parent / "db"
DB_PATH = DB_DIR / "monitor.db"


def get_connection():
    DB_DIR.mkdir(exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    """建立資料表（若不存在）"""
    conn = get_connection()
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            uuid      TEXT PRIMARY KEY,
            full_name TEXT,
            email     TEXT
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
    """)

    conn.commit()
    conn.close()


def import_users(users_data: list) -> dict:
    """
    寫入 users，已存在的跳過。
    回傳 {uuid: full_name} 的 mapping。
    """
    conn = get_connection()
    cur = conn.cursor()

    inserted = 0
    skipped = 0
    mapping = {}

    for user in users_data:
        uuid = user.get("uuid")
        if not uuid:
            continue
        full_name = user.get("full_name", "")
        email = user.get("email_address", "")
        mapping[uuid] = full_name

        cur.execute(
            "INSERT OR IGNORE INTO users (uuid, full_name, email) VALUES (?, ?, ?)",
            (uuid, full_name, email)
        )
        if cur.rowcount == 1:
            inserted += 1
        else:
            skipped += 1

    conn.commit()
    conn.close()
    return mapping, inserted, skipped


def import_conversations(conv_data: list, user_mapping: dict) -> tuple:
    """
    寫入 conversations 與 messages，已存在的跳過，不在 user_mapping 的跳過。
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

        # 只保留週一至週五（以對話開始日期判斷）
        if t_start_tw.weekday() > 4:
            skipped_weekend += 1
            continue

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
                duration_min, total_messages, tool_use_count, weekday, hour, date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
                       (uuid, conversation_uuid, sender, created_at_tw, date, hour, tool_use_count)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        msg_uuid,
                        uuid,
                        sender,
                        t_msg_tw.strftime("%Y-%m-%d %H:%M:%S"),
                        t_msg_tw.strftime("%Y-%m-%d"),
                        t_msg_tw.hour,
                        msg_tool_count,
                    )
                )
        else:
            skipped_dup += 1

    conn.commit()
    conn.close()
    return inserted, skipped_dup, skipped_unknown, skipped_weekend, skipped_empty


def db_exists() -> bool:
    return DB_PATH.exists()


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


def import_from_bytes(users_bytes: bytes, conv_bytes: bytes) -> dict:
    """
    接收上傳的 bytes，解析 JSON 並寫入 db。
    回傳各項統計數字。
    """
    init_db()

    users_data = json.loads(users_bytes)
    conv_data = json.loads(conv_bytes)

    user_mapping, u_inserted, u_skipped = import_users(users_data)

    c_inserted, c_dup, c_unknown, c_weekend, c_empty = import_conversations(
        conv_data, user_mapping
    )

    return {
        "users_inserted": u_inserted,
        "users_skipped": u_skipped,
        "conv_inserted": c_inserted,
        "conv_skipped_dup": c_dup,
        "conv_skipped_unknown": c_unknown,
        "conv_skipped_weekend": c_weekend,
        "conv_skipped_empty": c_empty,
    }
