from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_socketio import SocketIO, join_room, leave_room, send, emit
from flask_bcrypt import Bcrypt
from forms import RegistrationForm, LoginForm  # ایمپورت فرم لاگین و ثبت‌نام
import random
import string
import config

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = config.DATABASE_URL
app.config["SECRET_KEY"] = "supersecretkey"

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
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

    def set_password(self, password):
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password, password)

# ذخیره اطلاعات روم‌ها
rooms = {}

def generate_room_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

@app.route('/')
def home():
    if current_user.is_authenticated:
        return render_template("home.html")
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        name = form.name.data
        age = form.age.data
        country = form.country.data

        user = User.query.filter_by(username=username).first()
        if user:
            flash("Username already exists. Choose another.", "danger")
            return redirect(url_for("register"))

        new_user = User(
            username=username,
            name=name,
            age=int(age),
            country=country
        )
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful! You can now log in.", "success")  # پیام موفقیت ثبت‌نام
        return redirect(url_for('login'))

    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            flash("Login successful!", "success")
            return redirect(url_for('home'))
        else:
            flash("Invalid username or password.", "danger")

    return render_template('login.html', form=form)

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

@socketio.on("join_room")
def handle_join_room(data):
    room_id = data["room"]
    username = data["username"]
    if room_id in rooms:
        join_room(room_id)
        emit("update_players", {"players": rooms[room_id]["players"]}, room=room_id)

@socketio.on("send_message")
def handle_send_message(data):
    room_id = data["room"]
    username = data["username"]
    message = data["message"]

    if room_id in rooms:
        emit("receive_message", {"username": username, "message": message}, room=room_id)

@socketio.on("start_game")
def handle_start_game(data):
    room_id = data["room"]
    if room_id in rooms:
        emit("game_started", room=room_id)

@app.route('/game/<room_id>')
@login_required
def game(room_id):
    if room_id in rooms:
        return render_template("game.html", room_id=room_id, players=rooms[room_id]["players"])
    return "Room not found", 404

@app.route('/leaderboard')
@login_required
def leaderboard():
    users = User.query.order_by(User.score.desc()).all()
    return render_template("leaderboard.html", users=users)

@app.route('/profile')
@login_required
def profile():
    return render_template("profile.html", user=current_user)


if __name__ == '__main__':
    socketio.run(app, debug=True)
