from flask import Flask
from models import db
import config

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = config.DATABASE_URL
db.init_app(app)

with app.app_context():
    db.create_all()  # ایجاد جداول در دیتابیس

print("Database created successfully!")
