import sys
from pathlib import Path

# Python 3.11+ 用内建 tomllib；3.10 以下用 tomli（API 相同）
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

BASE_DIR = Path(__file__).parent.parent

# 读取 config.toml（注意 TOML 一定要用 "rb" 二进位模式开档）
with open(BASE_DIR / "config.toml", "rb") as f:
    _cfg = tomllib.load(f)


class Config:
    # ↓↓↓ 这两个是「实际会自动生效」的（Flask-SQLAlchemy 会自动读取）↓↓↓
    _db = _cfg["database"]
    # 路徑集中在此定義（單一來源，搬檔案不受影響）
    DB_DIR = BASE_DIR / "db"
    CLAUDE_DB_PATH = DB_DIR / _db["name"]        # monitor.db（原生 sqlite3 用：純路徑）
    OPENAI_DB_PATH = DB_DIR / "openai.db"        # openai.db（原生 sqlite3 用：純路徑）
    
    # Flask-SQLAlchemy 讀取用（URI 字串）
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{CLAUDE_DB_PATH}"
    SQLALCHEMY_TRACK_MODIFICATIONS = _db["track_modifications"]
    # openai使用情況資料庫
    SQLALCHEMY_BINDS = {
        "openai": f"sqlite:///{OPENAI_DB_PATH}",              # 附加庫
    }

    # ↓↓↓ 以下是「先读出来备用」，目前还没接到程式里 ↓↓↓
    APP_NAME = _cfg["app_name"]
    DEBUG = _cfg["debug"]
    PORT = _cfg["port"]
    INCOMING_DIR = BASE_DIR / _cfg["importer"]["incoming_dir_1"]
    DELETE_AFTER_IMPORT = _cfg["importer"]["delete_after_import"]
    CORS_ORIGINS = _cfg["cors"]["origins"]