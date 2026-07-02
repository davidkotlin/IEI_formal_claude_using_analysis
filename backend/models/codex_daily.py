# models/codex_daily.py
from . import db

class CodexDaily(db.Model):
    __bind_key__  = "openai"
    __tablename__ = "codex_daily"
    email          = db.Column(db.String, primary_key=True)   # 複合主鍵
    date           = db.Column(db.String, primary_key=True)   # (email, date)
    uncached_input = db.Column(db.Integer, default=0)
    cached_input   = db.Column(db.Integer, default=0)
    output         = db.Column(db.Integer, default=0)
    n_sessions     = db.Column(db.Integer, default=0)
    n_messages     = db.Column(db.Integer, default=0)