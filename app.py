import os
import json
import hashlib
import uuid
import zipfile
from flask import Flask, render_template_string, request, redirect, url_for, send_from_directory, flash, session, \
    send_file
from werkzeug.utils import secure_filename

# === Настройки ===
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'ppt', 'pptx', 'txt', 'zip', 'jpg', 'png', 'jpeg', 'mp4'}
TEACHER_FILE = 'teacher.json'
PENDING_FILE = 'pending_teachers.json'
DB_FILE = 'lessons.json'

ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'school_library_secret_2024')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 МБ

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# === Вспомогательные функции ===
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_file_type(filename):
    ext = filename.rsplit('.', 1)[1].lower()
    if ext in ['jpg', 'jpeg', 'png']:
        return 'image'
    elif ext == 'pdf':
        return 'pdf'
    elif ext in ['txt']:
        return 'text'
    elif ext == 'mp4':
        return 'video'
    else:
        return 'other'


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
            flash("🔐 Требуется вход учителя.", "error")
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


# === PWA: manifest.json ===
@app.route('/manifest.json')
def manifest():
    return {
        "name": "Школьная библиотека",
        "short_name": "Библиотека",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#f8f9fa",
        "theme_color": "#4285f4",
        "icons": [{
            "src": "/static/icon-192.png",
            "sizes": "192x192",
            "type": "image/png"
        }]
    }


# === Базовый HTML-шаблон с поддержкой темной темы ===
BASE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ page_title }}</title>
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#4285f4">
    <style>
        :root {
            --bg: #ffffff;
            --card-bg: #ffffff;
            --text: #202124;
            --text-light: #5f6368;
            --border: #dadce0;
            --primary: #4285f4;
            --primary-dark: #3367d6;
            --success: #34a853;
            --error: #ea4335;
        }
        [data-theme="dark"] {
            --bg: #121212;
            --card-bg: #1e1e1e;
            --text: #e8eaed;
            --text-light: #9aa0a6;
            --border: #3c4043;
            --primary: #8ab4f8;
            --primary-dark: #7f9ed6;
            --success: #81c995;
            --error: #f28b82;
        }
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            background-color: var(--bg);
            color: var(--text);
            font-family: 'Roboto', Arial, sans-serif;
            line-height: 1.6;
            padding-bottom: 40px;
            transition: background-color 0.3s, color 0.3s;
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
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
            transition: transform 0.2s, box-shadow 0.2s;
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
        [data-theme="dark"] .alert-success {
            background: #1e3a2a;
            border-color: #3a5a40;
        }
        .alert-error {
            background: #fce8e6;
            color: #c5221f;
            border: 1px solid #f28b82;
        }
        [data-theme="dark"] .alert-error {
            background: #3a1e1e;
            border-color: #5a3a3a;
        }
        .form-control {
            width: 100%;
            padding: 12px;
            border: 1px solid var(--border);
            border-radius: 8px;
            font-size: 15px;
            background: var(--card-bg);
            color: var(--text);
        }
        footer {
            text-align: center;
            margin-top: 40px;
            color: var(--text-light);
            font-size: 14px;
        }
        @media (max-width: 600px) {
            .btn {
                width: 100%;
                padding: 12px;
            }
        }
    </style>
</head>
<body data-theme="{{ 'dark' if dark_mode else 'light' }}">
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
        <p>Школьная библиотека</p>
    </footer>

    <script>
        // Автоматическое определение темной темы
        if (localStorage.theme === 'dark' || 
            (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
            document.body.setAttribute('data-theme', 'dark');
        } else {
            document.body.setAttribute('data-theme', 'light');
        }
    </script>
</body>
</html>
'''


def render_page(page_title, content_html):
    dark_mode = session.get('dark_mode', False)
    return render_template_string(BASE_TEMPLATE, page_title=page_title, content_html=content_html, dark_mode=dark_mode)


# === Главная страница с поиском и фильтрацией ===
@app.route('/')
def index():
    query = request.args.get('q', '').strip().lower()
    subject_filter = request.args.get('subject', '').strip()

    lessons = load_lessons()

    # Фильтрация
    filtered = []
    for lesson in lessons:
        title_match = query in lesson['title'].lower() or query in lesson.get('description', '').lower()
        subject_match = (not subject_filter) or lesson.get('subject') == subject_filter
        if title_match and subject_match:
            filtered.append(lesson)

    # Уникальные предметы
    subjects = sorted(set(lesson.get('subject', 'Другое') for lesson in lessons))

    lessons_html = ""
    if filtered:
        for lesson in filtered:
            file_type = get_file_type(lesson['filename'])
            view_url = url_for('view_file', filename=lesson['filename']) if file_type in ['pdf', 'text',
                                                                                          'image'] else '#'
            download_url = url_for('download_file', filename=lesson['filename'])

            lessons_html += f'''
            <div class="card">
                <div style="font-size: 20px; font-weight: 500; margin-bottom: 8px;">{lesson["title"]}</div>
                <div style="color: var(--text-light); margin-bottom: 16px; font-size: 15px;">
                    {lesson.get("description", "")}
                    <br><small>📁 {lesson.get("subject", "Без категории")} • 📥 {lesson.get("downloads", 0)} скачиваний</small>
                </div>
                <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                    <a href="{download_url}" class="btn btn-download">📥 Скачать</a>
                    {'<a href="' + view_url + '" class="btn" target="_blank">👁️ Просмотреть</a>' if file_type in ['pdf', 'text', 'image'] else ''}
                </div>
            </div>
            '''
    else:
        lessons_html = '<div class="card"><p style="text-align: center; color: var(--text-light);">📭 Ничего не найдено.</p></div>'

    # Форма поиска
    filters_html = f'''
    <div class="card" style="margin-bottom: 20px;">
        <form method="GET" style="display: flex; gap: 10px; flex-wrap: wrap; align-items: end;">
            <div style="flex: 1; min-width: 200px;">
                <label>Поиск</label>
                <input type="text" name="q" value="{query}" class="form-control" placeholder="Название или описание...">
            </div>
            <div style="min-width: 150px;">
                <label>Предмет</label>
                <select name="subject" class="form-control">
                    <option value="">Все</option>
                    {" ".join(f'<option value="{s}" {"selected" if s == subject_filter else ""}>{s}</option>' for s in subjects)}
                </select>
            </div>
            <div style="align-self: end;">
                <button type="submit" class="btn">🔍 Найти</button>
            </div>
        </form>
    </div>
    '''

    content = filters_html + lessons_html + '''
    <div style="text-align: center; margin-top: 20px;">
        <a href="/teacher">🔐 Войти как учитель</a> | 
        <a href="/register">📝 Подать заявку</a>
    </div>
    '''
    return render_page("📚 Библиотека уроков", content)


# === Просмотр файлов онлайн ===
@app.route('/view/<filename>')
def view_file(filename):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(filepath):
        flash("❌ Файл не найден.", "error")
        return redirect(url_for('index'))

    file_type = get_file_type(filename)

    if file_type == 'pdf':
        content = f'<embed src="/uploads/{filename}" type="application/pdf" width="100%" height="800px">'
    elif file_type == 'text':
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                text = f.read()
            content = f'<pre style="white-space: pre-wrap; font-family: monospace; background: var(--card-bg); padding: 20px; border-radius: 8px;">{text}</pre>'
        except Exception as e:
            content = f'<p>Ошибка чтения: {e}</p>'
    elif file_type == 'image':
        content = f'<img src="/uploads/{filename}" style="max-width: 100%; height: auto; border-radius: 8px;">'
    else:
        return redirect(url_for('download_file', filename=filename))

    return render_page(f"👁️ Просмотр: {filename}",
                       f'<div class="card">{content}</div><p><a href="/">← Назад к библиотеке</a></p>')


# === Скачивание с счётчиком ===
@app.route('/download/<filename>')
def download_file(filename):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(filepath):
        flash("❌ Файл не найден.", "error")
        return redirect(url_for('index'))

    lessons = load_lessons()
    for lesson in lessons:
        if lesson['filename'] == filename:
            lesson['downloads'] = lesson.get('downloads', 0) + 1
            break
    save_lessons(lessons)

    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)


# === Регистрация ===
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
            if any(t['username'] == username for t in pending):
                flash("ℹ️ Заявка уже отправлена.", "success")
            else:
                pending.append({
                    "username": username,
                    "password_hash": hash_password(password)
                })
                save_pending(pending)
                flash("✅ Заявка отправлена! Ожидайте одобрения.", "success")
            return redirect(url_for('index'))

    content = '''
    <div class="card">
        <h2>📝 Подать заявку на регистрацию</h2>
        <form method="POST">
            <div style="margin-bottom: 16px;">
                <label>Имя пользователя</label>
                <input type="text" name="username" class="form-control" required>
            </div>
            <div style="margin-bottom: 16px;">
                <label>Пароль (минимум 6 символов)</label>
                <input type="password" name="password" class="form-control" required>
            </div>
            <div style="margin-bottom: 16px;">
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
            flash("❌ Неверное имя или пароль.", "error")

    content = '''
    <div class="card">
        <h2>🔐 Вход для учителя</h2>
        <form method="POST">
            <div style="margin-bottom: 16px;">
                <label>Имя пользователя</label>
                <input type="text" name="username" class="form-control" required>
            </div>
            <div style="margin-bottom: 16px;">
                <label>Пароль</label>
                <input type="password" name="password" class="form-control" required>
            </div>
            <button type="submit" class="btn">Войти</button>
        </form>
        <p style="margin-top: 16px; text-align: center;">
            <a href="/register">📝 Подать заявку</a>
        </p>
    </div>
    '''
    return render_page("🔐 Вход", content)


# === Админка ===
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
            <div style="margin-bottom: 16px;">
                <label>Пароль администратора</label>
                <input type="password" name="password" class="form-control" required>
            </div>
            <button type="submit" class="btn">Войти</button>
        </form>
    </div>
    '''
    return render_page("🔐 Админка — вход", content)


@app.route('/admin')
@admin_required
def admin_panel():
    pending = load_pending()
    teacher = load_teacher()
    lessons = load_lessons()
    total_files = len(lessons)
    total_downloads = sum(lesson.get('downloads', 0) for lesson in lessons)

    teacher_html = f'<p><strong>{teacher["username"]}</strong></p>' if teacher else '<p>Нет активного учителя</p>'

    pending_html = ""
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

    content = f'''
    <div style="text-align: right; margin-bottom: 16px;">
        <a href="/admin/logout" style="color: var(--error);">Выйти</a>
    </div>
    <h2>📊 Статистика</h2>
    <div class="card">
        <p>📁 Всего материалов: {total_files}</p>
        <p>📥 Всего скачиваний: {total_downloads}</p>
    </div>
    <h2>✅ Активный учитель</h2>
    <div class="card">{teacher_html}</div>
    <h2>📥 Заявки</h2>
    {pending_html or '<p>Нет заявок.</p>'}
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


@app.route('/admin/delete-teacher', methods=['POST'])
@admin_required
def delete_teacher():
    try:
        if os.path.exists(TEACHER_FILE):
            os.remove(TEACHER_FILE)
        flash("✅ Учитель удалён.", "success")
    except Exception as e:
        flash(f"❌ Ошибка удаления: {str(e)}", "error")
    return redirect(url_for('admin_panel'))


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('index'))


# === Загрузка материалов ===
@app.route('/upload', methods=['GET', 'POST'])
@teacher_required
def teacher_upload():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        subject = request.form.get('subject', 'Другое').strip()
        file = request.files.get('file')

        if not title or not file or file.filename == '':
            flash("⚠️ Заполните название и выберите файл.", "error")
        elif not allowed_file(file.filename):
            flash("❌ Недопустимый формат файла.", "error")
        else:
            filename = secure_filename(file.filename)
            if not filename:
                ext = os.path.splitext(file.filename)[1].lower()
                if ext not in ['.pdf', '.doc', '.docx', '.ppt', '.pptx', '.txt', '.zip', '.jpg', '.jpeg', '.png',
                               '.mp4']:
                    ext = '.bin'
                filename = f"upload_{uuid.uuid4().hex}{ext}"

            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            counter = 1
            base, ext = os.path.splitext(filename)
            while os.path.exists(filepath):
                filename = f"{base}_{counter}{ext}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                counter += 1

            try:
                file.save(filepath)
            except Exception as e:
                flash(f"❌ Ошибка сохранения файла: {str(e)}", "error")
                return redirect(url_for('teacher_upload'))

            lessons = load_lessons()
            lessons.append({
                "id": len(lessons) + 1,
                "title": title,
                "description": description,
                "subject": subject,
                "filename": filename,
                "downloads": 0
            })
            try:
                save_lessons(lessons)
            except Exception as e:
                flash(f"❌ Ошибка сохранения данных: {str(e)}", "error")
                return redirect(url_for('teacher_upload'))

            flash("✅ Материал успешно добавлен!", "success")
            return redirect(url_for('teacher_upload'))

    lessons = load_lessons()
    lessons_html = ""
    if lessons:
        for lesson in lessons:
            file_type = get_file_type(lesson['filename'])
            view_url = url_for('view_file', filename=lesson['filename']) if file_type in ['pdf', 'text',
                                                                                          'image'] else '#'
            lessons_html += f'''
            <div class="card">
                <div style="font-size: 20px; font-weight: 500;">{lesson["title"]}</div>
                <div style="color: var(--text-light); margin: 8px 0;">{lesson.get("subject", "Без категории")}</div>
                <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-top: 12px;">
                    <a href="{url_for('download_file', filename=lesson['filename'])}" class="btn btn-download">📥 Скачать</a>
                    {'<a href="' + view_url + '" class="btn" target="_blank">👁️ Просмотреть</a>' if file_type in ['pdf', 'text', 'image'] else ''}
                    <form method="POST" action="{url_for('delete_lesson', lesson_id=lesson['id'])}" 
                          onsubmit="return confirm('Удалить?');">
                        <button type="submit" class="btn" style="background: var(--error);">🗑️ Удалить</button>
                    </form>
                </div>
            </div>
            '''
    else:
        lessons_html = '<p style="text-align: center; color: var(--text-light);">Нет материалов.</p>'

    content = f'''
    <div style="text-align: right; margin-bottom: 16px;">
        Привет, {session.get("teacher_name")}! 
        <a href="/logout" style="color: var(--error);">Выйти</a> | 
        <a href="/export" class="btn" style="background: #fbbc04; color: black; padding: 6px 12px;">📦 Экспорт ZIP</a>
    </div>

    <div class="card">
        <h2>➕ Добавить материал</h2>
        <form method="POST" enctype="multipart/form-data">
            <div style="margin-bottom: 16px;">
                <label>Название</label>
                <input type="text" name="title" class="form-control" required>
            </div>
            <div style="margin-bottom: 16px;">
                <label>Описание</label>
                <textarea name="description" class="form-control" rows="2" required></textarea>
            </div>
            <div style="margin-bottom: 16px;">
                <label>Предмет</label>
                <input type="text" name="subject" class="form-control" placeholder="Математика, Русский и т.д." required>
            </div>
            <div style="margin-bottom: 16px;">
                <label>Файл</label>
                <input type="file" name="file" class="form-control" accept=".pdf,.doc,.docx,.ppt,.pptx,.txt,.zip,.jpg,.png,.mp4" required>
            </div>
            <button type="submit" class="btn">📤 Загрузить</button>
        </form>
    </div>

    <h2 style="margin: 30px 0 16px; color: var(--primary-dark);">📁 Ваши материалы</h2>
    {lessons_html}
    '''
    return render_page("➕ Загрузка материалов", content)


# === Удаление материала ===
@app.route('/delete/<int:lesson_id>', methods=['POST'])
@teacher_required
def delete_lesson(lesson_id):
    lessons = load_lessons()
    lesson_to_delete = None
    for lesson in lessons:
        if lesson.get('id') == lesson_id:
            lesson_to_delete = lesson
            break

    if not lesson_to_delete:
        flash("❌ Материал не найден.", "error")
        return redirect(url_for('teacher_upload'))

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], lesson_to_delete['filename'])
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        app.logger.error(f"Ошибка удаления файла: {e}")

    lessons = [lesson for lesson in lessons if lesson.get('id') != lesson_id]
    try:
        save_lessons(lessons)
        flash("✅ Материал удалён!", "success")
    except Exception as e:
        flash(f"❌ Ошибка: {str(e)}", "error")

    return redirect(url_for('teacher_upload'))


# === Экспорт в ZIP ===
@app.route('/export')
@teacher_required
def export_all():
    zip_path = os.path.join(UPLOAD_FOLDER, 'library_export.zip')
    try:
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for root, dirs, files in os.walk(UPLOAD_FOLDER):
                for file in files:
                    if file == 'library_export.zip':
                        continue
                    full_path = os.path.join(root, file)
                    arcname = os.path.relpath(full_path, UPLOAD_FOLDER)
                    zipf.write(full_path, arcname)
        return send_file(zip_path, as_attachment=True)
    except Exception as e:
        flash(f"Ошибка экспорта: {e}", "error")
        return redirect(url_for('teacher_upload'))


# === Выход ===
@app.route('/logout')
def logout():
    session.pop('teacher_logged_in', None)
    session.pop('teacher_name', None)
    flash("👋 Вы вышли.", "success")
    return redirect(url_for('index'))


# === Запуск ===
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)