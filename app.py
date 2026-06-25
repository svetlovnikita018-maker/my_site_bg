import os
import sqlite3
import datetime
import time
import re
from flask import Flask, request, render_template_string, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_sessions'

# Лимит на размер файла
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024

UPLOAD_FOLDER = 'static/videos'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv'}

DB_NAME = 'app_database.db'

# --- Вспомогательная функция для безопасных имен с поддержкой кириллицы ---
def make_safe_filename(filename):
    base = os.path.basename(filename.replace('\\', '/'))
    clean = re.sub(r'[^a-zA-Z0-9а-яА-ЯёЁ\s_\-]', '', base)
    return clean.strip()

# --- Ультра-детализированный HTML/CSS Шаблон ---

BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VAULT // DIGITAL MEDIA CORE</title>
    <style>
        :root {
            --bg: #050505;
            --surface: #0d0d11;
            --border: rgba(255, 255, 255, 0.04);
            --border-bright: rgba(255, 255, 255, 0.15);
            --text: #ffffff;
            --text-muted: #66666e;
            --accent: #d4af37; 
            --font-mono: 'Courier New', Courier, monospace;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        body { 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; 
            background-color: var(--bg); 
            color: var(--text); 
            padding: 60px 40px;
            -webkit-font-smoothing: antialiased;
            overflow-x: hidden;
        }

        .container { max-width: 1400px; margin: 0 auto; }

        /* Верхний инфоблок */
        .header-meta {
            display: flex;
            justify-content: space-between;
            font-family: var(--font-mono);
            font-size: 0.75rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.15em;
            padding-bottom: 15px;
            border-bottom: 1px solid var(--border);
        }
        .status-pulse {
            display: inline-block;
            width: 6px;
            height: 6px;
            background: #34c759;
            border-radius: 50%;
            margin-right: 6px;
        }

        /* Навигационная панель */
        .nav { 
            display: flex; 
            justify-content: space-between; 
            align-items: baseline; 
            padding: 30px 0; 
            border-bottom: 1px solid var(--border); 
            margin-bottom: 80px; 
        }
        .logo { 
            font-size: 1.4rem; 
            font-weight: 900; 
            text-transform: uppercase; 
            letter-spacing: -0.03em; 
        }
        .logo span { color: var(--text-muted); font-weight: 300; font-family: var(--font-mono); font-size: 0.9rem; margin-left: 10px;}
        
        .nav-links a { 
            text-decoration: none; 
            color: var(--text); 
            font-size: 0.8rem; 
            font-weight: 600; 
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-left: 40px;
            transition: color 0.3s; 
            font-family: var(--font-mono);
        }
        .nav-links a:hover { color: var(--text-muted); }

        /* Главный заголовок страницы */
        .page-title-area {
            margin-bottom: 60px;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
        }
        h2 { 
            font-size: 4rem; 
            font-weight: 300; 
            letter-spacing: -0.04em; 
            line-height: 1.1;
            text-transform: uppercase;
        }
        h2 b { font-weight: 800; }

        /* Сетка видеороликов */
        .video-grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fill, minmax(400px, 1fr)); 
            gap: 1px; 
            background: var(--border); 
            border: 1px solid var(--border);
        }
        
        .video-card { 
            background: var(--bg); 
            padding: 30px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            transition: background 0.4s ease;
        }
        .video-card:hover { background: var(--surface); }

        .card-header {
            display: flex;
            justify-content: space-between;
            font-family: var(--font-mono);
            font-size: 0.8rem;
            color: var(--text-muted);
            margin-bottom: 20px;
        }

        .video-wrapper { 
            position: relative; 
            width: 100%; 
            aspect-ratio: 16/9; 
            background: #000; 
            overflow: hidden;
            border-radius: 2px;
            margin-bottom: 25px;
        }
        video { 
            width: 100%; 
            height: 100%; 
            object-fit: cover; 
            display: block; 
            transition: transform 0.6s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .video-card:hover video { transform: scale(1.03); }
        
        .video-meta-tags {
            display: flex;
            gap: 10px;
            font-family: var(--font-mono);
            font-size: 0.7rem;
            color: var(--text-muted);
            margin-bottom: 12px;
            text-transform: uppercase;
        }
        .tag { padding: 2px 6px; border: 1px solid var(--border); border-radius: 3px; }

        .video-title { 
            font-size: 1.3rem; 
            font-weight: 600; 
            letter-spacing: -0.02em;
            margin-bottom: 25px;
            white-space: nowrap; 
            overflow: hidden; 
            text-overflow: ellipsis; 
        }

        /* Кнопки управления */
        .actions-group {
            display: flex;
            gap: 10px;
            border-top: 1px solid var(--border);
            padding-top: 20px;
        }

        .btn {
            font-family: var(--font-mono);
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            padding: 10px 20px;
            border: 1px solid var(--border-bright);
            background: transparent;
            color: var(--text);
            cursor: pointer;
            text-decoration: none;
            transition: all 0.3s ease;
            display: inline-flex;
            align-items: center;
            justify-content: center;
        }
        .btn:hover {
            background: var(--text);
            color: var(--bg);
            border-color: var(--text);
        }
        .btn-sm { padding: 6px 12px; font-size: 0.7rem; }
        .btn-danger:hover { background: #ff453a; color: #fff; border-color: #ff453a; }

        /* Таблица пользователей */
        .users-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            font-family: var(--font-mono);
            font-size: 0.9rem;
        }
        .users-table th {
            text-align: left;
            padding: 15px 20px;
            color: var(--text-muted);
            border-bottom: 1px solid var(--border-bright);
            text-transform: uppercase;
            font-size: 0.75rem;
            letter-spacing: 0.1em;
        }
        .users-table td {
            padding: 20px;
            border-bottom: 1px solid var(--border);
            color: var(--text);
        }
        .users-table tr:hover td {
            background: var(--surface);
        }
        .role-badge {
            display: inline-block;
            padding: 2px 8px;
            font-size: 0.75rem;
            border-radius: 3px;
            border: 1px solid var(--border-bright);
        }
        .role-badge.admin {
            color: var(--accent);
            border-color: var(--accent);
        }
        .user-actions form {
            display: inline-block;
            margin-right: 5px;
        }

        /* Изысканные формы */
        .form-layout {
            max-width: 500px;
            margin: 100px auto;
            border: 1px solid var(--border-bright);
            padding: 50px 40px;
            background: var(--surface);
        }
        .form-layout h3 {
            font-size: 1.8rem;
            font-weight: 300;
            margin-bottom: 35px;
            text-transform: uppercase;
            letter-spacing: -0.02em;
        }
        .field { margin-bottom: 30px; }
        .field label {
            display: block;
            font-family: var(--font-mono);
            font-size: 0.7rem;
            color: var(--text-muted);
            text-transform: uppercase;
            margin-bottom: 10px;
            letter-spacing: 0.1em;
        }
        input[type="text"], input[type="password"], input[type="file"] {
            width: 100%;
            padding: 15px;
            background: var(--bg);
            border: 1px solid var(--border);
            color: var(--text);
            font-size: 1rem;
            transition: border-color 0.3s;
        }
        input:focus { outline: none; border-color: var(--text); }
        
        .form-nav-back {
            display: block;
            margin-top: 25px;
            font-family: var(--font-mono);
            font-size: 0.75rem;
            color: var(--text-muted);
            text-decoration: none;
            text-align: center;
        }
        .form-nav-back:hover { color: var(--text); }

        /* Системные уведомления */
        .flash-msg {
            font-family: var(--font-mono);
            font-size: 0.8rem;
            background: var(--surface);
            border: 1px solid var(--border-bright);
            padding: 15px 20px;
            margin-bottom: 20px;
            text-transform: uppercase;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header-meta">
            <div><span class="status-pulse"></span>SYSTEM STATUS: OPERATIONAL</div>
            <div>CORE V.3.1 // USER MANAGEMENT LOADED</div>
        </div>

        {% if session.get('username') %}
        <div class="nav">
            <div class="logo">VAULT <span>// SYSTEM</span></div>
            <div class="nav-links">
                <a href="{{ url_for('index') }}">Видео</a>
                {% if session.get('role') == 'admin' %}
                <a href="{{ url_for('admin_users') }}">[ Пользователи ]</a>
                <a href="{{ url_for('admin') }}" style="color: var(--accent);">[ + Загрузить материал ]</a>
                {% endif %}
                <a href="{{ url_for('logout') }}">Выход ({{ session['username'] }})</a>
            </div>
        </div>
        {% endif %}
        
        {% with messages = get_flashed_messages() %}
          {% if messages %}
            {% for message in messages %}
              <div class="flash-msg">// SYSTEM NOTICE: {{ message }}</div>
            {% endfor %}
          {% endif %}
        {% endwith %}
        
        {{ content|safe }}
    </div>
</body>
</html>
"""

# --- База Данных ---

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL,
                        role TEXT NOT NULL DEFAULT 'user'
                    )''')
    
    admin = conn.execute('SELECT * FROM users WHERE username = ?', ('admin',)).fetchone()
    if admin is None:
        hashed_pw = generate_password_hash('admin123')
        conn.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
                     ('admin', hashed_pw, 'admin'))
    conn.commit()
    conn.close()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Маршруты ---

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    try:
        video_files = os.listdir(app.config['UPLOAD_FOLDER'])
        video_files = [v for v in video_files if allowed_file(v)]
    except Exception:
        video_files = []
    
    is_admin = session.get('role') == 'admin'
    
    video_html = "<div class='page-title-area'><h2>Медиа <b>Видео</b></h2></div>"
    video_html += "<div class='video-grid'>"
    
    if not video_files:
        video_html += "<p style='color: var(--text-muted); font-family: var(--font-mono); padding: 40px; grid-column: 1/-1;'>// Список пуст. Ожидание импорта данных.</p>"
    
    for idx, video in enumerate(video_files, 1):
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], video)
        
        file_size_mb = 0
        file_date = "UNKNOWN"
        if os.path.exists(file_path):
            file_size_mb = round(os.path.getsize(file_path) / (1024 * 1024), 2)
            timestamp = os.path.getmtime(file_path)
            file_date = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
            
        ext = video.rsplit('.', 1)[1].upper() if '.' in video else 'RAW'
        display_title = video.rsplit('.', 1)[0] if '.' in video else video
        
        admin_actions = ""
        if is_admin:
            admin_actions = f"""
            <div class="actions-group">
                <a href="{url_for('rename_video', filename=video)}" class="btn btn-sm">Переименовать</a>
                <form action="{url_for('delete_video', filename=video)}" method="POST" style="margin:0;" onsubmit="return confirm('Удалить этот файл безвозвратно?');">
                    <button type="submit" class="btn btn-sm btn-danger">Удалить</button>
                </form>
            </div>
            """
            
        video_html += f"""
        <div class='video-card'>
            <div>
                <div class='card-header'>
                    <span>[{idx:02d}]</span>
                    <span>{file_date}</span>
                </div>
                <div class='video-wrapper'>
                    <video controls>
                        <source src="{url_for('static', filename='videos/' + video)}" type="video/mp4">
                    </video>
                </div>
                <div class='video-meta-tags'>
                    <span class='tag'>{ext}</span>
                    <span class='tag'>{file_size_mb} MB</span>
                </div>
                <div class='video-title' title='{display_title}'>{display_title}</div>
            </div>
            {admin_actions}
        </div>"""
        
    video_html += "</div>"
    return render_template_string(BASE_TEMPLATE, content=video_html)

# --- Управление пользователями (Админ) ---

@app.route('/admin/users')
def admin_users():
    if session.get('role') != 'admin':
        return "Доступ запрещен", 403
        
    conn = get_db()
    users = conn.execute('SELECT id, username, role FROM users ORDER BY id ASC').fetchall()
    conn.close()
    
    table_rows = ""
    for user in users:
        role_class = "admin" if user['role'] == 'admin' else "user"
        
        # Кнопки управления появляются, только если это не сам текущий админ
        actions_html = ""
        if user['username'] != session.get('username'):
            make_admin_btn = ""
            if user['role'] != 'admin':
                make_admin_btn = f"""
                <form action="{url_for('make_user_admin', user_id=user['id'])}" method="POST">
                    <button type="submit" class="btn btn-sm">В админы</button>
                </form>
                """
            
            delete_btn = f"""
            <form action="{url_for('delete_user_account', user_id=user['id'])}" method="POST" onsubmit="return confirm('Вы уверены, что хотите удалить пользователя {user['username']}?');">
                <button type="submit" class="btn btn-sm btn-danger">Удалить</button>
            </form>
            """
            actions_html = f"<div class='user-actions'>{make_admin_btn}{delete_btn}</div>"
        else:
            actions_html = "<span style='color: var(--text-muted); font-size: 0.75rem;'>[ ТЕКУЩИЙ ПРОФИЛЬ ]</span>"

        table_rows += f"""
        <tr>
            <td>{user['id']:04d}</td>
            <td><b>{user['username']}</b></td>
            <td><span class="role-badge {role_class}">{user['role'].upper()}</span></td>
            <td>{actions_html}</td>
        </tr>
        """
        
    content = f"""
    <div class="page-title-area">
        <h2>Реестр <b>Пользователей</b></h2>
        <span style="font-family: var(--font-mono); color: var(--text-muted); font-size:0.85rem;">Всего записей: {len(users)}</span>
    </div>
    <div style="border: 1px solid var(--border); background: var(--bg);">
        <table class="users-table">
            <thead>
                <tr>
                    <th>ID профиля</th>
                    <th>Имя пользователя (Логин)</th>
                    <th>Уровень доступа (Роль)</th>
                    <th>Действия</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
    </div>
    """
    return render_template_string(BASE_TEMPLATE, content=content)

@app.route('/admin/make_admin/<int:user_id>', methods=['POST'])
def make_user_admin(user_id):
    if session.get('role') != 'admin':
        return "Доступ запрещен", 403
        
    conn = get_db()
    conn.execute('UPDATE users SET role = "admin" WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    
    flash('Права администратора успешно предоставлены.')
    return redirect(url_for('admin_users'))

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
def delete_user_account(user_id):
    if session.get('role') != 'admin':
        return "Доступ запрещен", 403

    conn = get_db()

    user_to_delete = conn.execute(
        'SELECT username, role FROM users WHERE id = ?',
        (user_id,)
    ).fetchone()

    if not user_to_delete:
        flash('Пользователь не найден.')
        conn.close()
        return redirect(url_for('admin_users'))

    # Нельзя удалить самого себя
    if user_to_delete['username'] == session.get('username'):
        flash('Ошибка: Вы не можете удалить собственный профиль.')

    # Нельзя удалить главного администратора
    elif user_to_delete['username'] == 'admin':
        flash('Ошибка: Главный администратор защищён от удаления.')

    else:
        conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
        flash(f'Пользователь {user_to_delete["username"]} был удален из системы.')

    conn.close()
    return redirect(url_for('admin_users'))
# --- Основной функционал приложения ---

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if session.get('role') != 'admin':
        return "Доступ запрещен", 403
        
    if request.method == 'POST':
        if 'video' not in request.files:
            flash('Критическая ошибка: Запрос пуст.')
            return redirect(request.url)
            
        file = request.files['video']
        if file.filename == '':
            flash('Ошибка: Файл не выбран.')
            return redirect(request.url)
            
        if file and allowed_file(file.filename):
            orig_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'mp4'
            raw_base_name = file.filename.rsplit('.', 1)[0] if '.' in file.filename else 'video'
            
            clean_base = make_safe_filename(raw_base_name)
            
            if not clean_base or clean_base == '':
                clean_base = f"imported_media_{int(time.time())}"
                
            filename = f"{clean_base}.{orig_ext}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            try:
                file.save(file_path)
                flash(f'Объект "{filename}" успешно импортирован в хранилище.')
                return redirect(url_for('index'))
            except Exception as e:
                flash(f'Ошибка файловой системы при сохранении: {e}')
                return redirect(request.url)
        else:
            flash('Ошибка: Недопустимый формат файла. Разрешены только: MP4, AVI, MOV, MKV.')
            return redirect(request.url)
            
    content = """
    <div class="form-layout">
        <h3>UPLOAD TO VAULT</h3>
        <p style="color: var(--text-muted); font-size: 0.85rem; margin-bottom: 25px; font-family: var(--font-mono);">
            Максимальный размер пакета: 500 MB.<br>Поддерживаются любые языки в названиях.
        </p>
        <form method="POST" enctype="multipart/form-data">
            <div class="field">
                <label>Выбрать файл</label>
                <input type="file" name="video" accept="video/*" required>
            </div>
            <button type="submit" class="btn" style="width: 100%;">Начать импорт</button>
        </form>
        <a href="/" class="form-nav-back">← На главную</a>
    </div>
    """
    return render_template_string(BASE_TEMPLATE, content=content)

@app.route('/rename/<filename>', methods=['GET', 'POST'])
def rename_video(filename):
    if session.get('role') != 'admin':
        return "Доступ запрещен", 403
        
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(file_path):
        flash('Файл не найден.')
        return redirect(url_for('index'))
        
    name_part, ext_part = filename.rsplit('.', 1) if '.' in filename else (filename, '')
    
    if request.method == 'POST':
        new_name_raw = request.form['new_name'].strip()
        if not new_name_raw:
            flash('Имя не может быть пустым.')
            return redirect(request.url)
            
        clean_name = make_safe_filename(new_name_raw)
        
        if not clean_name:
            clean_name = f"renamed_media_{int(time.time())}"
            
        new_filename = f"{clean_name}.{ext_part}" if ext_part else clean_name
        new_file_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
        
        try:
            os.rename(file_path, new_file_path)
            flash(f'Файл переименован в "{clean_name}"')
            return redirect(url_for('index'))
        except Exception as e:
            flash(f'Ошибка переименования: {e}')
            return redirect(request.url)
            
    content = f"""
    <div class="form-layout">
        <h3>Переименовать медиа</h3>
        <p style="color: var(--text-muted); font-size: 0.85rem; margin-bottom: 25px; font-family: var(--font-mono);">
            ТЕКУЩЕЕ ИМЯ: {name_part}<br>формат: .{ext_part}
        </p>
        <form method="POST">
            <div class="field">
                <label>Новое название (без расширения)</label>
                <input type="text" name="new_name" value="{name_part}" required autofocus>
            </div>
            <button type="submit" class="btn" style="width: 100%;">Сохранить</button>
        </form>
        <a href="/" class="form-nav-back">← Отмена</a>
    </div>
    """
    return render_template_string(BASE_TEMPLATE, content=content)

@app.route('/delete/<filename>', methods=['POST'])
def delete_video(filename):
    if session.get('role') != 'admin':
        return "Доступ запрещен", 403
        
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            flash(f'Файл "{filename}" стерт из хранилища.')
        except Exception as e:
            flash(f'Ошибка удаления: {e}')
    else:
        flash('Файл не найден.')
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db()
        try:
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                         (username, generate_password_hash(password)))
            conn.commit()
            flash('Регистрация завершена. Выполните вход.')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Этот идентификатор уже занят.')
        finally:
            conn.close()
            
    content = """
    <div class="form-layout">
        <h3>REGISTRATION</h3>
        <form method="POST">
            <div class="field">
                <label>Идентификатор (Логин)</label>
                <input type="text" name="username" placeholder="e.g. user_01" required>
            </div>
            <div class="field">
                <label>Крипто-пароль</label>
                <input type="password" name="password" placeholder="••••••••" required>
            </div>
            <button type="submit" class="btn" style="width: 100%;">Создать профиль</button>
        </form>
        <a href="/login" class="form-nav-back">Уже есть доступ? Войти</a>
    </div>
    """
    return render_template_string(BASE_TEMPLATE, content=content)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('index'))
        else:
            flash('Отказ в доступе. Неверная комбинация.')
            
    content = """
    <div class="form-layout">
        <h3>SIGN IN</h3>
        <form method="POST">
            <div class="field">
                <label>Логин доступа</label>
                <input type="text" name="username" required>
            </div>
            <div class="field">
                <label>Пароль</label>
                <input type="password" name="password" required>
            </div>
            <button type="submit" class="btn" style="width: 100%;">Авторизоваться</button>
        </form>
        <a href="/register" class="form-nav-back">Запросить доступ (Регистрация)</a>
    </div>
    """
    return render_template_string(BASE_TEMPLATE, content=content)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    init_db()
    # Как вы и предпочитаете, приложение запускается и тестируется в локальной среде на ПК
    app.run(debug=True, port=5000)
