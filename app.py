from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_socketio import SocketIO, join_room, leave_room
import random
import string
import config

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = config.DATABASE_URL
app.config["SECRET_KEY"] = "supersecretkey"

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# مدل کاربر
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    country = db.Column(db.String(50), nullable=False)
    score = db.Column(db.Integer, default=0)

# تابع تولید ID برای روم
def generate_room_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

rooms = {}  # ذخیره اطلاعات روم‌ها

@app.route('/')
def home():
    if current_user.is_authenticated:
        return render_template("home.html")
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        name = request.form.get("name")
        age = request.form.get("age")
        country = request.form.get("country")

        user = User(username=username, password=password, name=name, age=int(age), country=country)
        db.session.add(user)
        db.session.commit()
        flash("Registration successful! You can now log in.", "success")
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            login_user(user)
            flash("Login successful!", "success")
            return redirect(url_for('home'))
        else:
            flash("Invalid username or password.", "danger")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

@app.route('/create-room')
@login_required
def create_room():
    room_id = generate_room_id()
    rooms[room_id] = {"players": [current_user.username], "status": "waiting"}
    return render_template("room.html", room_id=room_id, players=rooms[room_id]["players"])

@app.route('/join-room', methods=['GET', 'POST'])
@login_required
def join_room_page():
    if request.method == "POST":
        room_id = request.form.get("room_id")
        if room_id in rooms and len(rooms[room_id]["players"]) < 2:
            rooms[room_id]["players"].append(current_user.username)
            return redirect(url_for("room", room_id=room_id))
        flash("Invalid room ID or room is full.", "danger")
    return render_template("join_room.html")

@app.route('/room/<room_id>')
@login_required
def room(room_id):
    if room_id in rooms:
        return render_template("room.html", room_id=room_id, players=rooms[room_id]["players"])
    return "Room not found", 404

if __name__ == '__main__':
    socketio.run(app, debug=True)
