from flask import Flask
from flask_cors import CORS
from .config import Config
from .models import db
from .routes.users import users_bp
from .routes.stats import stats_bp
from .routes.imports import imports_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # 開發時允許前端 localhost:5173 跨域存取
    CORS(app, resources={r"/api/*": {"origins": "http://localhost:5173"}})

    db.init_app(app)

    app.register_blueprint(users_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(imports_bp)

    return app
