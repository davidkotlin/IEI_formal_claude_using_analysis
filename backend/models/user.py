from . import db

class User(db.Model):
    __tablename__ = "users"

    uuid      = db.Column(db.Text, primary_key=True)
    full_name = db.Column(db.Text)
    email     = db.Column(db.Text)

    conversations = db.relationship("Conversation", backref="user", lazy=True)
