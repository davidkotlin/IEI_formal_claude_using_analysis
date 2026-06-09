import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

class Config:
    # SQLite 開發用，正式換 PostgreSQL 只改這一行
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{BASE_DIR}/db/monitor.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
