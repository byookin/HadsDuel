from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_socketio import SocketIO, join_room, leave_room, send, emit
from flask_bcrypt import Bcrypt
from forms import RegistrationForm, LoginForm
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

@app.route('/leaderboard')
@login_required
def leaderboard():
    users = User.query.order_by(User.score.desc()).all()
    return render_template("leaderboard.html", users=users)

@app.route('/create-room')
@login_required
def create_room():
    room_id = generate_room_id()
    rooms[room_id] = {
        "players": [current_user.username], 
        "status": "waiting",
        "target_number": random.randint(1, 100),
        "attempts": {}
    }
    return render_template("room.html", room_id=room_id, players=rooms[room_id]["players"])

@app.route('/join-room', methods=['GET', 'POST'])
@login_required
def join_room_view():
    if request.method == "POST":
        room_id = request.form.get("room_id")
        if room_id in rooms and len(rooms[room_id]["players"]) < 2:
            rooms[room_id]["players"].append(current_user.username)
            return redirect(url_for("room", room_id=room_id))
        flash("Invalid room ID or room is full.", "danger")
    return render_template("join_room.html")

@socketio.on("join_room")
def handle_join_room(data):
    room_id = data["room"]
    username = data["username"]

    if room_id in rooms:
        if username not in rooms[room_id]["players"]:
            rooms[room_id]["players"].append(username)
        join_room(room_id)
        
        print(f"📢 {username} joined room {room_id}")
        print(f"👥 Current players: {rooms[room_id]['players']}")
        
        emit("update_players", {"players": rooms[room_id]["players"]}, room=room_id)

@socketio.on("send_message")
def handle_send_message(data):
    room_id = data["room"]
    username = data["username"]
    message = data["message"]

    if room_id in rooms:
        print(f"📩 Message from {username}: {message}")
        emit("receive_message", {"username": username, "message": message}, room=room_id)

@app.route('/room/<room_id>')
@login_required
def room(room_id):
    if room_id in rooms:
        return render_template("room.html", room_id=room_id, players=rooms[room_id]["players"])
    return "Room not found", 404

@socketio.on("guess_number")
def handle_guess_number(data):
    room_id = data["room"]
    username = data["username"]
    guess = int(data["guess"])

    if room_id not in rooms:
        return

    target = rooms[room_id]["target_number"]

    if guess == target:
        user = User.query.filter_by(username=username).first()
        if user:
            user.score += 10
            db.session.commit()

        emit("game_winner", {"winner": username}, room=room_id, broadcast=True)
        del rooms[room_id]
    elif guess < target:
        emit("guess_feedback", {"username": username, "feedback": "بزرگ‌تر حدس بزن!"}, room=room_id, broadcast=True)
    else:
        emit("guess_feedback", {"username": username, "feedback": "کوچک‌تر حدس بزن!"}, room=room_id, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True)
