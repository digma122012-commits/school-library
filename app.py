import os
import json
import hashlib
from flask import Flask, render_template_string, request, redirect, url_for, send_from_directory, flash, session

# === Настройки ===
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'ppt', 'pptx', 'txt', 'zip', 'jpg', 'png', 'jpeg'}
TEACHER_FILE = 'teacher.json'
PENDING_FILE = 'pending_teachers.json'
DB_FILE = 'lessons.json'

# 🔑 Пароль администратора (задаётся в Render как переменная окружения)
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'school_library_secret_2024')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def load_teacher():
    if not os.path.exists(TEACHER_FILE):
        return None
    try:
        with open(TEACHER_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None


def save_teacher(username, password_hash):
    with open(TEACHER_FILE, 'w', encoding='utf-8') as f:
        json.dump({"username": username, "password_hash": password_hash}, f)


def load_pending():
    if not os.path.exists(PENDING_FILE):
        return []
    try:
        with open(PENDING_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []


def save_pending(pending_list):
    with open(PENDING_FILE, 'w', encoding='utf-8') as f:
        json.dump(pending_list, f, ensure_ascii=False, indent=2)


def load_lessons():
    if not os.path.exists(DB_FILE):
        return []
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return []
            return json.loads(content)
    except (json.JSONDecodeError, IOError):
        return []


def save_lessons(lessons):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(lessons, f, ensure_ascii=False, indent=2)


# === Декораторы ===
def teacher_required(f):
    def wrapper(*args, **kwargs):
        if 'teacher_logged_in' not in session:
            flash("🔐 Пожалуйста, войдите в аккаунт учителя.", "error")
            return redirect(url_for('teacher_login'))
        return f(*args, **kwargs)

    wrapper.__name__ = f.__name__
    return wrapper


def admin_required(f):
    def wrapper(*args, **kwargs):
        if 'admin_logged_in' not in session:
            flash("🔐 Требуется вход администратора.", "error")
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)

    wrapper.__name__ = f.__name__
    return wrapper


# === Шаблон (без футера) ===
BASE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ page_title }}</title>
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap">
    <style>
        :root {
            --primary: #4285f4;
            --primary-dark: #3367d6;
            --success: #34a853;
            --error: #ea4335;
            --light-bg: #f8f9fa;
            --card-bg: #ffffff;
            --text: #202124;
            --text-light: #5f6368;
            --border: #dadce0;
        }
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Roboto', Arial, sans-serif;
            background-color: var(--light-bg);
            color: var(--text);
            line-height: 1.6;
            padding-bottom: 40px;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            padding: 0 20px;
        }
        header {
            background: var(--primary);
            color: white;
            padding: 24px 0;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        header h1 {
            font-weight: 500;
            font-size: 28px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
        }
        .logo {
            font-size: 28px;
        }
        .content {
            margin-top: 30px;
        }
        .card {
            background: var(--card-bg);
            border-radius: 12px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.08);
            padding: 24px;
            margin-bottom: 24px;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 16px rgba(0,0,0,0.12);
        }
        .card h2 {
            font-size: 22px;
            margin-bottom: 16px;
            color: var(--primary-dark);
        }
        .lesson-title {
            font-size: 20px;
            font-weight: 500;
            margin-bottom: 8px;
            color: var(--text);
        }
        .lesson-desc {
            color: var(--text-light);
            margin-bottom: 16px;
            font-size: 15px;
        }
        .btn {
            display: inline-block;
            background: var(--primary);
            color: white;
            text-decoration: none;
            padding: 10px 20px;
            border-radius: 6px;
            font-weight: 500;
            transition: background 0.2s;
            border: none;
            cursor: pointer;
            font-size: 15px;
        }
        .btn:hover {
            background: var(--primary-dark);
        }
        .btn-download {
            background: var(--success);
        }
        .btn-download:hover {
            background: #2e8b47;
        }
        .btn-approve {
            background: var(--success);
        }
        .form-group {
            margin-bottom: 16px;
        }
        .form-group label {
            display: block;
            margin-bottom: 6px;
            font-weight: 500;
            color: var(--text);
        }
        .form-control {
            width: 100%;
            padding: 12px;
            border: 1px solid var(--border);
            border-radius: 8px;
            font-size: 15px;
            font-family: inherit;
        }
        .form-control:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 2px rgba(66, 133, 244, 0.2);
        }
        .alert {
            padding: 14px 18px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-weight: 500;
        }
        .alert-success {
            background: #e6f4ea;
            color: #137333;
            border: 1px solid #8fd694;
        }
        .alert-error {
            background: #fce8e6;
            color: #c5221f;
            border: 1px solid #f28b82;
        }
        .teacher-link {
            text-align: center;
            margin-top: 20px;
        }
        .teacher-link a {
            color: var(--primary);
            text-decoration: none;
            font-weight: 500;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        .teacher-link a:hover {
            text-decoration: underline;
        }
        footer {
            text-align: center;
            margin-top: 40px;
            color: var(--text-light);
            font-size: 14px;
        }
        @media (max-width: 600px) {
            header h1 {
                font-size: 22px;
            }
            .card {
                padding: 18px;
            }
            .btn {
                width: 100%;
                padding: 12px;
            }
        }
    </style>
</head>
<body>
    <header>
        <div class="container">
            <h1><span class="logo">📚</span> {{ page_title }}</h1>
        </div>
    </header>

    <div class="container">
        <div class="content">
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="alert alert-{{ 'success' if category == 'message' else 'error' }}">
                            {{ message }}
                        </div>
                    {% endfor %}
                {% endif %}
            {% endwith %}

            {{ content_html | safe }}
        </div>
    </div>

    <footer class="container">
    </footer>
</body>
</html>
'''


def render_page(page_title, content_html):
    return render_template_string(BASE_TEMPLATE, page_title=page_title, content_html=content_html)


# === Главная страница ===
@app.route('/')
def index():
    lessons = load_lessons()
    if lessons:
        lessons_html = ""
        for lesson in lessons:
            lessons_html += f'''
            <div class="card">
                <div class="lesson-title">{lesson["title"]}</div>
                <div class="lesson-desc">{lesson["description"]}</div>
                <a href="{url_for('download_file', filename=lesson['filename'])}" class="btn btn-download">
                    📥 Скачать файл
                </a>
            </div>
            '''
    else:
        lessons_html = '<div class="card"><p style="text-align: center; color: var(--text-light);">📭 Пока нет учебных материалов.</p></div>'

    content = f'''
    {lessons_html}
    <div class="teacher-link">
        <a href="/teacher">🔐 Войти как учитель</a> | 
        <a href="/register">📝 Подать заявку на регистрацию</a>
    </div>
    '''
    return render_page("Библиотека уроков", content)


# === Подача заявки ===
@app.route('/register', methods=['GET', 'POST'])
def register():
    if load_teacher():
        flash("✅ Учитель уже активен. Входите в аккаунт.", "success")
        return redirect(url_for('teacher_login'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')

        if not username or not password:
            flash("⚠️ Заполните все поля.", "error")
        elif password != confirm:
            flash("❌ Пароли не совпадают.", "error")
        elif len(password) < 6:
            flash("⚠️ Пароль должен быть не короче 6 символов.", "error")
        else:
            pending = load_pending()
            # Проверим, не подавал ли уже заявку
            if any(t['username'] == username for t in pending):
                flash("ℹ️ Заявка уже отправлена. Ожидайте одобрения.", "success")
            else:
                pending.append({
                    "username": username,
                    "password_hash": hash_password(password)
                })
                save_pending(pending)
                flash("✅ Заявка отправлена! Администратор рассмотрит её в ближайшее время.", "success")
            return redirect(url_for('index'))

    content = '''
    <div class="card">
        <h2>📝 Подать заявку на регистрацию</h2>
        <p style="color: var(--text-light); margin-bottom: 20px;">
            Ваша заявка будет рассмотрена администратором. После одобрения вы сможете войти.
        </p>
        <form method="POST">
            <div class="form-group">
                <label>Имя пользователя</label>
                <input type="text" name="username" class="form-control" required>
            </div>
            <div class="form-group">
                <label>Пароль (минимум 6 символов)</label>
                <input type="password" name="password" class="form-control" required>
            </div>
            <div class="form-group">
                <label>Подтвердите пароль</label>
                <input type="password" name="confirm" class="form-control" required>
            </div>
            <button type="submit" class="btn">📤 Отправить заявку</button>
        </form>
    </div>
    '''
    return render_page("📝 Заявка на регистрацию", content)


# === Вход учителя ===
@app.route('/teacher', methods=['GET', 'POST'])
def teacher_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        teacher = load_teacher()

        if teacher and teacher['username'] == username and teacher['password_hash'] == hash_password(password):
            session['teacher_logged_in'] = True
            session['teacher_name'] = username
            flash(f"✅ Добро пожаловать, {username}!", "success")
            return redirect(url_for('teacher_upload'))
        else:
            flash("❌ Неверное имя пользователя или пароль.", "error")

    content = '''
    <div class="card">
        <h2>🔐 Вход для учителя</h2>
        <form method="POST">
            <div class="form-group">
                <label>Имя пользователя</label>
                <input type="text" name="username" class="form-control" required>
            </div>
            <div class="form-group">
                <label>Пароль</label>
                <input type="password" name="password" class="form-control" required>
            </div>
            <button type="submit" class="btn">Войти</button>
        </form>
        <p style="margin-top: 16px; text-align: center;">
            <a href="/register">📝 Подать заявку на регистрацию</a>
        </p>
    </div>
    '''
    return render_page("🔐 Вход", content)


# === Админка: вход ===
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_panel'))
        else:
            flash("❌ Неверный пароль администратора.", "error")
    content = '''
    <div class="card">
        <h2>🔐 Вход администратора</h2>
        <form method="POST">
            <div class="form-group">
                <label>Пароль администратора</label>
                <input type="password" name="password" class="form-control" required>
            </div>
            <button type="submit" class="btn">Войти</button>
        </form>
    </div>
    '''
    return render_page("🔐 Админка — вход", content)


# === Админка: одобрение заявок ===
@app.route('/admin')
@admin_required
def admin_panel():
    pending = load_pending()
    teacher = load_teacher()

    pending_html = ""
    if pending:
        for i, t in enumerate(pending):
            pending_html += f'''
            <div class="card">
                <strong>👤 {t["username"]}</strong>
                <form method="POST" action="/admin/approve" style="margin-top: 12px;">
                    <input type="hidden" name="index" value="{i}">
                    <button type="submit" class="btn btn-approve">✅ Одобрить</button>
                </form>
            </div>
            '''
    else:
        pending_html = '<p style="text-align: center; color: var(--text-light);">📭 Нет заявок.</p>'

    content = f'''
    <div style="text-align: right; margin-bottom: 16px;">
        <a href="/admin/logout" style="color: var(--error);">Выйти</a>
    </div>

    <h2>✅ Активный учитель</h2>
    <div class="card">
        {"<p>Нет активного учителя</p>" if not teacher else f"<p><strong>{teacher['username']}</strong></p>"}
    </div>

    <h2>📥 Заявки на регистрацию</h2>
    {pending_html}
    '''
    return render_page("🛠️ Админка", content)


@app.route('/admin/approve', methods=['POST'])
@admin_required
def approve_teacher():
    index = int(request.form.get('index'))
    pending = load_pending()
    if 0 <= index < len(pending):
        teacher_data = pending.pop(index)
        save_teacher(teacher_data['username'], teacher_data['password_hash'])
        save_pending(pending)
        flash(f"✅ Учитель {teacher_data['username']} одобрен!", "success")
    return redirect(url_for('admin_panel'))


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('index'))


# === Выход учителя ===
@app.route('/logout')
def logout():
    session.pop('teacher_logged_in', None)
    session.pop('teacher_name', None)
    flash("👋 Вы вышли из аккаунта.", "success")
    return redirect(url_for('index'))


# === Загрузка материалов ===
@app.route('/upload', methods=['GET', 'POST'])
@teacher_required
def teacher_upload():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        file = request.files.get('file')

        if not title or not file or file.filename == '':
            flash("⚠️ Заполните название и выберите файл.", "error")
        elif not allowed_file(file.filename):
            flash("❌ Недопустимый формат файла. Разрешены: PDF, DOCX, PPTX, TXT, ZIP, JPG, PNG.", "error")
        else:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            counter = 1
            base, ext = os.path.splitext(filename)
            while os.path.exists(filepath):
                filename = f"{base}_{counter}{ext}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                counter += 1
            file.save(filepath)

            lessons = load_lessons()
            lessons.append({
                "id": len(lessons) + 1,
                "title": title,
                "description": description,
                "filename": filename
            })
            save_lessons(lessons)
            flash("✅ Материал успешно добавлен!", "success")
            return redirect(url_for('teacher_upload'))

    lessons = load_lessons()
    lessons_html = ""
    if lessons:
        for lesson in lessons:
            lessons_html += f'''
            <div class="card">
                <div class="lesson-title">{lesson["title"]}</div>
                <div class="lesson-desc">{lesson["description"]}</div>
                <a href="{url_for('download_file', filename=lesson['filename'])}" class="btn btn-download">
                    📥 {lesson["filename"]}
                </a>
            </div>
            '''
    else:
        lessons_html = '<p style="text-align: center; color: var(--text-light);">Нет загруженных материалов.</p>'

    content = f'''
    <div style="text-align: right; margin-bottom: 16px;">
        Привет, {session.get("teacher_name")}! <a href="/logout" style="color: var(--error);">Выйти</a>
    </div>

    <div class="card">
        <h2>➕ Добавить новый материал</h2>
        <form method="POST" enctype="multipart/form-data">
            <div class="form-group">
                <label>Название урока</label>
                <input type="text" name="title" class="form-control" required>
            </div>
            <div class="form-group">
                <label>Описание</label>
                <textarea name="description" class="form-control" rows="3" required></textarea>
            </div>
            <div class="form-group">
                <label>Файл (PDF, DOCX, PPTX, ZIP и др.)</label>
                <input type="file" name="file" class="form-control" accept=".pdf,.doc,.docx,.ppt,.pptx,.txt,.zip,.jpg,.png,.jpeg" required>
            </div>
            <button type="submit" class="btn">📤 Загрузить</button>
        </form>
    </div>

    <h2 style="margin: 30px 0 16px; color: var(--primary-dark);">📁 Текущие материалы</h2>
    {lessons_html}
    '''
    return render_page("➕ Загрузка материалов", content)


@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)


# === Запуск ===
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)