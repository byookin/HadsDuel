import os

# تنظیم آدرس دیتابیس
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///hadsduel.db")
