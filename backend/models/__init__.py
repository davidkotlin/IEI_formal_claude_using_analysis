from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
# claude using db
from .user import User
from .conversation import Conversation
from .message import Message
#openai using db
from .openai_user import OpenAIUser
from .codex_daily import CodexDaily
from .web_daily import WebDaily