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
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{BASE_DIR}/db/{_db['name']}"
    SQLALCHEMY_TRACK_MODIFICATIONS = _db["track_modifications"]
    
    # openai使用情況資料庫
    SQLALCHEMY_BINDS = {
        "openai": f"sqlite:///{BASE_DIR}/db/openai.db",              # 附加庫
    }

    # ↓↓↓ 以下是「先读出来备用」，目前还没接到程式里 ↓↓↓
    APP_NAME = _cfg["app_name"]
    DEBUG = _cfg["debug"]
    PORT = _cfg["port"]
    INCOMING_DIR = BASE_DIR / _cfg["importer"]["incoming_dir"]
    DELETE_AFTER_IMPORT = _cfg["importer"]["delete_after_import"]
    CORS_ORIGINS = _cfg["cors"]["origins"]