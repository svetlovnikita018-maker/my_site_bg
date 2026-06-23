from flask import Flask, request, redirect, session, render_template_string
import psycopg2
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "secret123"

DATABASE_URL = os.getenv("DATABASE_URL")

# ---------------- DB ----------------

def get_db():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT DEFAULT 'user'
    )
    """)

    # 👉 главный админ
    cur.execute("SELECT * FROM users WHERE username=%s", ("admin",))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
            ("admin", generate_password_hash("admin123"), "admin")
        )

    conn.commit()
    conn.close()

with app.app_context():
    init_db()

# ---------------- HOME ----------------

@app.route("/")
def home():
    return "<h1>Сайт работает 🚀</h1>"

# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT username, password, role FROM users WHERE username=%s", (username,))
        user = cur.fetchone()
        conn.close()

        if user and check_password_hash(user[1], password):
            session["user"] = user[0]
            session["role"] = user[2]
            return redirect("/admin")
        return "❌ Неверный логин"

    return """
    <form method="post">
        <input name="username">
        <input name="password" type="password">
        <button>Login</button>
    </form>
    """

# ---------------- ADMIN PANEL ----------------

@app.route("/admin")
def admin():
    if session.get("role") != "admin":
        return "⛔ Нет доступа"

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT id, username, role FROM users")
    users = cur.fetchall()
    conn.close()

    html = "<h2>Admin panel</h2><table border='1'>"

    for u in users:

        # 👉 защита главного админа
        if u[1] == "admin":
            action = "🔒 главный админ"
        else:
            action = f"<a href='/delete/{u[0]}'>Удалить</a> | <a href='/make_admin/{u[0]}'>Сделать админом</a>"

        html += f"""
        <tr>
            <td>{u[0]}</td>
            <td>{u[1]}</td>
            <td>{u[2]}</td>
            <td>{action}</td>
        </tr>
        """

    html += "</table>"
    return html

# ---------------- MAKE ADMIN ----------------

@app.route("/make_admin/<int:user_id>")
def make_admin(user_id):
    if session.get("role") != "admin":
        return "⛔ Нет доступа"

    conn = get_db()
    cur = conn.cursor()

    cur.execute("UPDATE users SET role='admin' WHERE id=%s", (user_id,))
    conn.commit()
    conn.close()

    return redirect("/admin")

# ---------------- DELETE USER ----------------

@app.route("/delete/<int:user_id>")
def delete_user(user_id):
    if session.get("role") != "admin":
        return "⛔ Нет доступа"

    conn = get_db()
    cur = conn.cursor()

    # 👉 проверка: нельзя удалить главного админа
    cur.execute("SELECT username FROM users WHERE id=%s", (user_id,))
    user = cur.fetchone()

    if user and user[0] == "admin":
        return "⛔ Нельзя удалить главного админа"

    cur.execute("DELETE FROM users WHERE id=%s", (user_id,))
    conn.commit()
    conn.close()

    return redirect("/admin")

# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- RUN ----------------

if __name__ == "__main__":
    app.run()
