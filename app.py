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

# ---------------- DATABASE (POSTGRES) ----------------

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db():
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

    # admin
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
    return "<h1>Сайт работает 🚀 (PRO VERSION)</h1>"

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

    return """
    <form method="post">
        <input name="username">
        <input name="password" type="password">
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
        return "Wrong login"

    return """
    <form method="post">
        <input name="username">
        <input name="password" type="password">
        <button>Login</button>
    </form>
    """

# ---------------- VIDEO UPLOAD (CLOUDINARY) ----------------

@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        file = request.files["file"]

        result = cloudinary.uploader.upload_large(file, resource_type="video")

        return f"Uploaded: {result['secure_url']}"

    return """
    <form method="post" enctype="multipart/form-data">
        <input type="file" name="file">
        <button>Upload video</button>
    </form>
    """

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

    html = "<h2>Admin panel</h2>"
    for u in users:
        html += f"{u}<br>"

    return html

# ---------------- RUN ----------------

if __name__ == "__main__":
    app.run()
