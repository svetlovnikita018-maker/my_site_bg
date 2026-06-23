from flask import Flask, request, redirect, session, render_template_string
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

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
        password TEXT,
        role TEXT DEFAULT 'user'
    )
    """)

    # 👉 создаём админа
    c.execute("SELECT * FROM users WHERE username=?", ("admin",))
    if not c.fetchone():
        c.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            ("admin", generate_password_hash("admin123"), "admin")
        )

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

.card {
    background: rgba(255,255,255,0.1);
    padding: 25px;
    width: 320px;
    margin: 50px auto;
    border-radius: 15px;
}

input {
    width: 90%;
    padding: 10px;
    margin: 8px;
    border-radius: 10px;
    border: none;
}

button {
    width: 95%;
    padding: 10px;
    border-radius: 10px;
    border: none;
    background: #3b82f6;
    color: white;
    cursor: pointer;
}

a { color: #60a5fa; text-decoration: none; }
</style>
"""

# ---------------- HOME ----------------

@app.route("/")
def home():
    user = session.get("user")

    return STYLE + f"""
    <div class="card">
        <h1>🚀 Сайт</h1>

        {"<p>Привет, " + user + "</p>" if user else "<p>Ты не вошёл</p>"}

        <a href="/login">Login</a><br><br>
        <a href="/register">Register</a><br><br>
        <a href="/admin">Admin</a><br><br>
        <a href="/logout">Logout</a>
    </div>
    """

# ---------------- REGISTER ----------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        try:
            c.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                (username, password, "user")
            )
            conn.commit()
        except:
            return STYLE + "<div class='card'>❌ Пользователь уже существует</div>"

        conn.close()
        return redirect("/login")

    return STYLE + """
    <div class="card">
        <h2>Регистрация</h2>
        <form method="post">
            <input name="username" placeholder="username">
            <input name="password" type="password" placeholder="password">
            <button>Создать</button>
        </form>
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

        c.execute("SELECT username, password, role FROM users WHERE username=?", (username,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user[1], password):
            session["user"] = user[0]
            session["role"] = user[2]
            return redirect("/")
        else:
            return STYLE + "<div class='card'>❌ Неверный логин</div>"

    return STYLE + """
    <div class="card">
        <h2>Вход</h2>
        <form method="post">
            <input name="username">
            <input name="password" type="password">
            <button>Войти</button>
        </form>
    </div>
    """

# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- ADMIN PANEL ----------------

@app.route("/admin")
def admin():
    if session.get("role") != "admin":
        return "⛔ Доступ запрещён"

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, username, role FROM users")
    users = c.fetchall()
    conn.close()

    html_users = ""
    for u in users:
        html_users += f"""
        <tr>
            <td>{u[0]}</td>
            <td>{u[1]}</td>
            <td>{u[2]}</td>
            <td><a href="/delete/{u[0]}">Удалить</a></td>
        </tr>
        """

    return STYLE + f"""
    <div class="card" style="width:600px">
        <h2>👑 Admin Panel</h2>
        <table border="1" width="100%">
            {html_users}
        </table>
    </div>
    """

# ---------------- DELETE USER ----------------

@app.route("/delete/<int:user_id>")
def delete_user(user_id):
    if session.get("role") != "admin":
        return "⛔ Нет доступа"

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()

    return redirect("/admin")

# ---------------- RUN ----------------

if __name__ == "__main__":
    app.run()
