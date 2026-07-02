# models/openai_user.py
from . import db

class OpenAIUser(db.Model):
    __bind_key__  = "openai"
    __tablename__ = "users"
    email   = db.Column(db.String, primary_key=True)
    name    = db.Column(db.String)
    user_id = db.Column(db.String)
    active  = db.Column(db.Integer, default=1)