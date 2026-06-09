from . import db

class Conversation(db.Model):
    __tablename__ = "conversations"

    uuid           = db.Column(db.Text, primary_key=True)
    user_uuid      = db.Column(db.Text, db.ForeignKey("users.uuid"))
    name           = db.Column(db.Text)
    created_at_tw  = db.Column(db.Text)
    updated_at_tw  = db.Column(db.Text)
    duration_min   = db.Column(db.Float)
    total_messages = db.Column(db.Integer)
    tool_use_count = db.Column(db.Integer)
    weekday        = db.Column(db.Integer)
    hour           = db.Column(db.Integer)
    date           = db.Column(db.Text)
