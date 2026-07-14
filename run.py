from backend.app import create_app
from backend.models import db
from sqlalchemy import inspect

app = create_app()

with app.app_context():
    inspector = inspect(db.engine)
    if not inspector.has_table("users"):
        db.create_all()

if __name__ == "__main__":
    # host="0.0.0.0"：監聽所有網卡，讓區網內的手機能連進來（不只本機 127.0.0.1）
    # 手機連 http://<電腦區網IP>:5000/api，IP 見前端 src/config.ts
    app.run(debug=True, host="0.0.0.0", port=5000)