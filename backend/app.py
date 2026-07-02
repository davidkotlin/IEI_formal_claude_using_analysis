from flask import Flask
from flask_cors import CORS
from .config import Config
from .models import db
#claude routes
from .routes.users import users_bp
from .routes.stats import stats_bp
from .routes.imports import imports_bp
#openai routes
# 最上面 import 區，跟著現有的往下加
from .routes.openai_stats import openai_stats_bp
from .routes.openai_users import openai_users_bp
from .routes.openai_imports import openai_imports_bp
def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # 開發時允許前端 localhost:5173 跨域存取
    CORS(app, resources={r"/api/*": {"origins": "http://localhost:5173"}})

    db.init_app(app)
    #claude
    app.register_blueprint(users_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(imports_bp)
    #openai
    app.register_blueprint(openai_stats_bp)
    app.register_blueprint(openai_users_bp)
    app.register_blueprint(openai_imports_bp)

    return app
