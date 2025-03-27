socket.on("connect", () => {
    console.log("Connected to server");
    socket.emit("join_room", {"room": roomId, "username": username});
});

let currentTimer = null;

function updateButtons() {
    console.log("Current Turn:", currentTurn, "Username:", username);
    document.querySelectorAll(".number").forEach(button => {
        if (button.classList.contains("disabled")) return;
        button.disabled = (currentTurn !== username);
        button.style.cursor = (currentTurn === username) ? "pointer" : "not-allowed";
    });
}

updateButtons();

socket.on("game_started", (data) => {
    console.log("Game Started, Current Turn:", data.turn, "Room:", data.room);
    currentTurn = data.turn;
    updateButtons();
    socket.emit("start_timer", {"turn": currentTurn, "room": roomId});
});

socket.on("update_turn", (data) => {
    console.log("Turn Updated, Current Turn:", data.turn);
    currentTurn = data.turn;
    document.querySelectorAll(".username").forEach(el => {
        el.classList.remove("blink");
        if (el.textContent === currentTurn) el.classList.add("blink");
    });
    updateButtons();
});

socket.on("start_timer", (data) => {
    console.log("Starting Timer for:", data.turn, "Room:", data.room);
    if (currentTimer) {
        clearInterval(currentTimer);
    }
    let timeLeft = 15;
    const timerEl = document.getElementById(data.turn === players[0] ? "timer1" : "timer2");
    const otherTimerEl = document.getElementById(data.turn === players[0] ? "timer2" : "timer1");
    otherTimerEl.innerHTML = "";
    timerEl.innerHTML = `(${timeLeft}s)`;
    currentTimer = setInterval(() => {
        timeLeft--;
        timerEl.innerHTML = `(${timeLeft}s)`;
        if (timeLeft < 0) {
            clearInterval(currentTimer);
            currentTimer = null;
            timerEl.innerHTML = "";
            socket.emit("guess_number", {"room": roomId, "username": data.turn, "guess": -1});
        }
    }, 1000);
});

document.querySelectorAll(".number").forEach(button => {
    button.addEventListener("click", () => {
        if (currentTurn === username && !button.disabled) {
            if (currentTimer) {
                clearInterval(currentTimer);
                currentTimer = null;
                const timerEl = document.getElementById(currentTurn === players[0] ? "timer1" : "timer2");
                timerEl.innerHTML = "";
            }
            const guess = button.getAttribute("data-number");
            socket.emit("guess_number", {"room": roomId, "username": username, "guess": guess});
        }
    });
});

socket.on("guess_feedback", (data) => {
    console.log("Guess Feedback:", data);
    const button = document.querySelector(`button[data-number="${data.guess}"]`);
    // فقط کلاس مربوط به فیدبک رو اضافه کن
    if (data.feedback === "larger") {
        button.classList.add("larger");
    } else if (data.feedback === "smaller") {
        button.classList.add("smaller");
    }
    // غیرفعال کردن دکمه بدون تاثیر روی رنگ
    button.disabled = true;
    button.classList.add("disabled");
});

socket.on("game_winner", (data) => {
    console.log("Game Winner:", data);
    if (currentTimer) {
        clearInterval(currentTimer);
        currentTimer = null;
        const timerEl = document.getElementById(currentTurn === players[0] ? "timer1" : "timer2");
        timerEl.innerHTML = "";
    }
    const button = document.querySelector(`button[data-number="${data.guess}"]`);
    button.classList.remove("larger", "smaller"); // پاک کردن کلاس‌های قبلی
    button.classList.add("correct");
    button.disabled = true;
    button.classList.add("disabled");
    setTimeout(() => {
        window.location.href = `/result/${roomId}/${data.winner}`;
    }, 2000);
});

socket.on("redirect", (data) => {
    console.log("Redirecting to:", data.url);
    window.location.href = data.url;
});

function sendMessage() {
    const message = document.getElementById("chat-input").value;
    if (message.trim() !== "") {
        console.log("Sending Message:", message);
        socket.emit("send_message", {"room": roomId, "username": username, "message": message});
        document.getElementById("chat-input").value = "";
    }
}

socket.on("receive_message", (data) => {
    console.log("Received Message:", data);
    const chatBox = document.getElementById("chat-box");
    const p = document.createElement("p");
    p.innerHTML = `<strong>${data.username}:</strong> ${data.message}`;
    chatBox.appendChild(p);
    chatBox.scrollTop = chatBox.scrollHeight;
});

socket.on("update_chat", (data) => {
    console.log("Updating Chat:", data);
    const chatBox = document.getElementById("chat-box");
    chatBox.innerHTML = "";
    data.chat_history.forEach(msg => {
        const p = document.createElement("p");
        p.innerHTML = `<strong>${msg.username}:</strong> ${msg.message}`;
        chatBox.appendChild(p);
    });
    chatBox.scrollTop = chatBox.scrollHeight;
});