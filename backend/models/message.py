from . import db


class Message(db.Model):
    __tablename__ = "messages"

    uuid              = db.Column(db.Text, primary_key=True)
    conversation_uuid = db.Column(db.Text, db.ForeignKey("conversations.uuid"))
    sender            = db.Column(db.Text)
    created_at_tw     = db.Column(db.Text)
    date              = db.Column(db.Text)
    hour              = db.Column(db.Integer)
    tool_use_count    = db.Column(db.Integer, default=0)
    group_id          = db.Column(db.Integer, index=True)   # 跟著 conversation 的組別

    conversation = db.relationship("Conversation", backref="messages")
