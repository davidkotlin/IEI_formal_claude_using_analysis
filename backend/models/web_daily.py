# models/web_daily.py
from . import db

class WebDaily(db.Model):
    __bind_key__  = "openai"
    __tablename__ = "web_daily"
    email  = db.Column(db.String, primary_key=True)   # 複合主鍵
    date   = db.Column(db.String, primary_key=True)   # (email, date)
    tokens = db.Column(db.Integer, default=0)