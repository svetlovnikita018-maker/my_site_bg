from flask import Flask, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = "secret123"

DB_NAME = "database.db"

# ---------------- DATABASE ----------------

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    conn.commit()
    conn.close()

# 👉 ВАЖНО: создаём БД правильно для Render
with app.app_context():
    init_db()

# ---------------- ROUTES ----------------

@app.route("/")
def home():
    return "Сайт работает 🚀"

# ---------------- REGISTER ----------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        try:
            c.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, password)
            )
            conn.commit()
        except:
            return "❌ Пользователь уже существует"

        conn.close()
        return redirect("/login")

    return """
    <h2>Register</h2>
    <form method="post">
        <input name="username" placeholder="username">
        <input name="password" placeholder="password">
        <button type="submit">Register</button>
    </form>
    """

# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        c.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        )

        user = c.fetchone()
        conn.close()

        if user:
            session["user"] = username
            return "✅ Вход выполнен"
        else:
            return "❌ Неверный логин или пароль"

    return """
    <h2>Login</h2>
    <form method="post">
        <input name="username" placeholder="username">
        <input name="password" placeholder="password">
        <button type="submit">Login</button>
    </form>
    """

# ---------------- RUN (локально) ----------------

if __name__ == "__main__":
    app.run()
