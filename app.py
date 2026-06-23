from flask import Flask, request, redirect, session, render_template_string
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

with app.app_context():
    init_db()

# ---------------- STYLE ----------------

STYLE = """
<style>
body {
    margin: 0;
    font-family: Arial;
    background: linear-gradient(120deg, #0f172a, #1e293b);
    color: white;
    text-align: center;
}

.container {
    margin-top: 80px;
}

.card {
    background: rgba(255,255,255,0.1);
    padding: 30px;
    width: 300px;
    margin: auto;
    border-radius: 15px;
    box-shadow: 0 0 20px rgba(0,0,0,0.5);
}

input {
    width: 90%;
    padding: 10px;
    margin: 10px 0;
    border-radius: 10px;
    border: none;
}

button {
    padding: 10px 20px;
    border: none;
    border-radius: 10px;
    background: #3b82f6;
    color: white;
    cursor: pointer;
    width: 100%;
}

button:hover {
    background: #2563eb;
}

a {
    color: #60a5fa;
    text-decoration: none;
}
</style>
"""

# ---------------- HOME ----------------

@app.route("/")
def home():
    return STYLE + """
    <div class="container">
        <h1>🚀 Мой сайт</h1>
        <div class="card">
            <p>Добро пожаловать!</p>
            <a href="/login">Войти</a><br><br>
            <a href="/register">Регистрация</a>
        </div>
    </div>
    """

# ---------------- REGISTER ----------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        try:
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                      (username, password))
            conn.commit()
        except:
            return STYLE + "<h2>❌ Пользователь уже существует</h2>"

        conn.close()
        return redirect("/login")

    return STYLE + """
    <div class="container">
        <div class="card">
            <h2>Регистрация</h2>
            <form method="post">
                <input name="username" placeholder="username"><br>
                <input name="password" placeholder="password" type="password"><br>
                <button type="submit">Создать аккаунт</button>
            </form>
            <br>
            <a href="/">← назад</a>
        </div>
    </div>
    """

# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        c.execute("SELECT * FROM users WHERE username=? AND password=?",
                  (username, password))

        user = c.fetchone()
        conn.close()

        if user:
            session["user"] = username
            return STYLE + f"""
            <div class="container">
                <div class="card">
                    <h2>✅ Добро пожаловать {username}</h2>
                    <a href="/">На главную</a>
                </div>
            </div>
            """
        else:
            return STYLE + "<h2>❌ Неверный логин или пароль</h2>"

    return STYLE + """
    <div class="container">
        <div class="card">
            <h2>Вход</h2>
            <form method="post">
                <input name="username" placeholder="username"><br>
                <input name="password" placeholder="password" type="password"><br>
                <button type="submit">Войти</button>
            </form>
            <br>
            <a href="/">← назад</a>
        </div>
    </div>
    """

# ---------------- RUN ----------------

if __name__ == "__main__":
    app.run()
