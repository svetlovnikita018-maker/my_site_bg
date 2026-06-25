from flask import Flask, request, redirect, session
import psycopg2
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- DATABASE ----------------

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db():
    if not DATABASE_URL:
        raise Exception("DATABASE_URL not set in environment variables")
    return psycopg2.connect(DATABASE_URL, sslmode="require")

# ---------------- INIT DB ----------------

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

    # главный админ (защищённый)
    cur.execute("SELECT * FROM users WHERE username=%s", ("admin",))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
            ("admin", generate_password_hash("admin123"), "admin")
        )

    conn.commit()
    conn.close()

# ---------------- SAFE START ----------------

with app.app_context():
    init_db()

# ---------------- ROUTES ----------------

@app.route("/")
def home():
    if "user" in session:
        return f"""
        <h1>Привет {session['user']}</h1>
        <a href="/logout">Logout</a><br>
        <a href="/admin">Admin panel</a>
        """
    return "<h1>Сайт работает 🚀</h1><a href='/login'>Login</a> | <a href='/register'>Register</a>"

# ---------------- REGISTER ----------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])

        conn = get_db()
        cur = conn.cursor()

        try:
            cur.execute(
                "INSERT INTO users (username, password) VALUES (%s, %s)",
                (username, password)
            )
            conn.commit()
        except:
            return "❌ User already exists"

        conn.close()
        return redirect("/login")

    return """
    <form method="post">
        <input name="username" placeholder="username">
        <input name="password" type="password" placeholder="password">
        <button>Register</button>
    </form>
    """

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
            return redirect("/")
        return "❌ Wrong login"

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
        return "⛔ No access"

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT id, username, role FROM users")
    users = cur.fetchall()
    conn.close()

    html = "<h1>Admin panel</h1><table border='1'>"

    for u in users:
        user_id, username, role = u

        # 🔒 защита главного админа
        if username == "admin":
            actions = "🔒 MAIN ADMIN"
        else:
            actions = f"""
            <a href="/delete/{user_id}">Delete</a> |
            <a href="/make_admin/{user_id}">Make admin</a>
            """

        html += f"""
        <tr>
            <td>{user_id}</td>
            <td>{username}</td>
            <td>{role}</td>
            <td>{actions}</td>
        </tr>
        """

    html += "</table>"
    return html

# ---------------- MAKE ADMIN ----------------

@app.route("/make_admin/<int:user_id>")
def make_admin(user_id):
    if session.get("role") != "admin":
        return "⛔ No access"

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
        return "⛔ No access"

    conn = get_db()
    cur = conn.cursor()

    # 🔒 запрет удаления главного админа
    cur.execute("SELECT username FROM users WHERE id=%s", (user_id,))
    user = cur.fetchone()

    if user and user[0] == "admin":
        return "⛔ Cannot delete main admin"

    cur.execute("DELETE FROM users WHERE id=%s", (user_id,))
    conn.commit()
    conn.close()

    return redirect("/admin")

# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- RUN (Render uses gunicorn, this is fallback) ----------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
