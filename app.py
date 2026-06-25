from flask import Flask, request, redirect, session, render_template_string
import os
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash
import cloudinary
import cloudinary.uploader

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- CLOUDINARY ----------------

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

# ---------------- DATABASE ----------------

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db():
    if not DATABASE_URL:
        raise Exception("DATABASE_URL missing")
    return psycopg2.connect(DATABASE_URL, sslmode="require")

# ---------------- INIT DB SAFE ----------------

def init_db():
    try:
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

        # главный админ
        cur.execute("SELECT * FROM users WHERE username=%s", ("admin",))
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
                ("admin", generate_password_hash("admin123"), "admin")
            )

        conn.commit()
        conn.close()
    except Exception as e:
        print("DB INIT ERROR:", e)

with app.app_context():
    init_db()

# ---------------- UI TEMPLATE ----------------

BASE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>My Site</title>
    <style>
        body { font-family: Arial; background:#0f0f0f; color:white; text-align:center; }
        a { color:#4da3ff; margin:10px; text-decoration:none; font-size:18px; }
        .box { margin-top:80px; }
        input, button {
            padding:10px;
            margin:5px;
            border-radius:8px;
            border:none;
        }
        button { background:#4da3ff; color:white; cursor:pointer; }
        table { margin:auto; border-collapse:collapse; }
        td { border:1px solid white; padding:10px; }
    </style>
</head>
<body>
<div class="box">
    {{content}}
</div>
</body>
</html>
"""

# ---------------- HOME ----------------

@app.route("/")
def home():
    if "user" in session:
        content = f"""
        <h1>Привет {session['user']} 🚀</h1>
        <a href="/upload">📤 Upload</a>
        <a href="/admin">🛠 Admin</a>
        <a href="/logout">🚪 Logout</a>
        """
    else:
        content = """
        <h1>Сайт работает 🚀</h1>
        <a href="/login">Login</a>
        <a href="/register">Register</a>
        """
    return render_template_string(BASE_HTML, content=content)

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
            return "User exists"

        conn.close()
        return redirect("/login")

    return render_template_string(BASE_HTML, content="""
    <h2>Register</h2>
    <form method="post">
        <input name="username" placeholder="username"><br>
        <input name="password" type="password" placeholder="password"><br>
        <button>Register</button>
    </form>
    """)

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

        return "Wrong login"

    return render_template_string(BASE_HTML, content="""
    <h2>Login</h2>
    <form method="post">
        <input name="username" placeholder="username"><br>
        <input name="password" type="password" placeholder="password"><br>
        <button>Login</button>
    </form>
    """)

# ---------------- UPLOAD ----------------

@app.route("/upload", methods=["GET", "POST"])
def upload():
    if "user" not in session:
        return redirect("/login")

    if request.method == "POST":
        file = request.files["file"]

        result = cloudinary.uploader.upload_large(
            file,
            resource_type="video"
        )

        url = result["secure_url"]

        return render_template_string(BASE_HTML, content=f"""
        <h2>Uploaded ✅</h2>
        <a href="{url}">Watch video</a>
        """)

    return render_template_string(BASE_HTML, content="""
    <h2>Upload video</h2>
    <form method="post" enctype="multipart/form-data">
        <input type="file" name="file"><br>
        <button>Upload</button>
    </form>
    """)

# ---------------- ADMIN ----------------

@app.route("/admin")
def admin():
    if session.get("role") != "admin":
        return "No access"

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT id, username, role FROM users")
    users = cur.fetchall()
    conn.close()

    html = "<h2>Admin panel</h2><table>"

    for u in users:
        uid, username, role = u

        if username == "admin":
            action = "🔒 MAIN ADMIN"
        else:
            action = f"<a href='/delete/{uid}'>Delete</a>"

        html += f"<tr><td>{uid}</td><td>{username}</td><td>{role}</td><td>{action}</td></tr>"

    html += "</table>"
    return render_template_string(BASE_HTML, content=html)

# ---------------- DELETE ----------------

@app.route("/delete/<int:user_id>")
def delete(user_id):
    if session.get("role") != "admin":
        return "No access"

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT username FROM users WHERE id=%s", (user_id,))
    user = cur.fetchone()

    if user and user[0] == "admin":
        return "Cannot delete main admin"

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
