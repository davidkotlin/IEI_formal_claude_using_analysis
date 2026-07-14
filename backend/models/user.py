from . import db

class User(db.Model):
    __tablename__ = "users"

    uuid      = db.Column(db.Text, primary_key=True)
    full_name = db.Column(db.Text)
    email     = db.Column(db.Text)
    group_id  = db.Column(db.Integer, index=True)   # 1/2/3 —— 這組的基準名單成員
    department = db.Column(db.Text)                  # 部門（由 employee Excel 匯入或手動填）

    conversations = db.relationship("Conversation", backref="user", lazy=True)
