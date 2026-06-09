from backend.app import create_app
from backend.models import db
from sqlalchemy import inspect

app = create_app()

with app.app_context():
    inspector = inspect(db.engine)
    if not inspector.has_table("users"):
        db.create_all()

if __name__ == "__main__":
    app.run(debug=True, port=5000)