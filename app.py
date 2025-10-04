import os
from flask import Flask, render_template_string, request, redirect, url_for, send_from_directory, flash
import json
from werkzeug.utils import secure_filename

# === Настройки ===
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'ppt', 'pptx', 'txt', 'zip', 'jpg', 'png', 'jpeg'}

# 🔑 Пароль берём из переменной окружения (на Render зададим его там)
TEACHER_PASSWORD = os.environ.get('TEACHER_PASSWORD', 'teacher123')

DB_FILE = 'lessons.json'

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'school_library_secret_2024')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 МБ

# Создаём папку при запуске
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# === Вспомогательные функции ===
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
        save_lessons([])
        return []

def save_lessons(lessons):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(lessons, f, ensure_ascii=False, indent=2)

# === HTML-шаблоны (встроены) ===
BASE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Библиотека уроков</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 30px auto; padding: 0 15px; }
        .alert { padding: 12px; margin: 15px 0; border-radius: 6px; }
        .alert-error { background: #ffe6e6; color: #d32f2f; }
        .alert-success { background: #e8f5e9; color: #2e7d32; }
        .lesson { border: 1px solid #ddd; padding: 15px; margin: 15px 0; border-radius: 6px; }
        a { color: #1a73e8; text-decoration: none; }
        a:hover { text-decoration: underline; }
        input, textarea, button { width: 100%; padding: 8px; margin: 5px 0; box-sizing: border-box; }
        button { background: #4285f4; color: white; border: none; cursor: pointer; }
        button:hover { background: #3367d6; }
    </style>
</head>
<body>
    <h1>📚 {% block title %}{% endblock %}</h1>
    {% block content %}{% endblock %}
</body>
</html>
'''

INDEX_TEMPLATE = BASE_TEMPLATE.replace(
    '{% block title %}{% endblock %}', 'Библиотека уроков (для учеников)'
).replace(
    '{% block content %}{% endblock %}', '''
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% for category, message in messages %}
            <div class="alert alert-{{ 'error' if 'error' in category else 'success' }}">{{ message }}</div>
        {% endfor %}
    {% endwith %}

    {% if lessons %}
        {% for lesson in lessons %}
        <div class="lesson">
            <h3>{{ lesson.title }}</h3>
            <p><em>{{ lesson.description }}</em></p>
            <p><a href="{{ url_for('download_file', filename=lesson.filename) }}">📥 Скачать: {{ lesson.filename }}</a></p>
        </div>
        {% endfor %}
    {% else %}
        <p>📭 Пока нет материалов.</p>
    {% endif %}

    <hr>
    <p style="text-align: center;"><a href="/teacher">🔐 Учитель? Войдите здесь</a></p>
'''
)

LOGIN_TEMPLATE = BASE_TEMPLATE.replace(
    '{% block title %}{% endblock %}', 'Вход для учителя'
).replace(
    '{% block content %}{% endblock %}', '''
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% for category, message in messages %}
            <div class="alert alert-{{ 'error' if 'error' in category else 'success' }}">{{ message }}</div>
        {% endfor %}
    {% endwith %}

    <form method="POST" style="max-width: 400px; margin: 0 auto;">
        <label>Пароль учителя:</label>
        <input type="password" name="password" required>
        <button type="submit">Войти</button>
    </form>
'''
)

UPLOAD_TEMPLATE = BASE_TEMPLATE.replace(
    '{% block title %}{% endblock %}', 'Загрузка материалов (учитель)'
).replace(
    '{% block content %}{% endblock %}', '''
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% for category, message in messages %}
            <div class="alert alert-{{ 'error' if 'error' in category else 'success' }}">{{ message }}</div>
        {% endfor %}
    {% endwith %}

    <h3>Добавить материал</h3>
    <form method="POST" enctype="multipart/form-data" style="max-width: 600px;">
        <input type="text" name="title" placeholder="Название" required>
        <textarea name="description" placeholder="Описание" rows="3" required></textarea>
        <input type="file" name="file" accept=".pdf,.doc,.docx,.ppt,.pptx,.txt,.zip,.jpg,.png" required>
        <button type="submit">Загрузить</button>
    </form>

    <hr>
    <h3>Текущие материалы</h3>
    {% if lessons %}
        {% for lesson in lessons %}
        <div class="lesson">
            <strong>{{ lesson.title }}</strong> — <a href="{{ url_for('download_file', filename=lesson.filename) }}">{{ lesson.filename }}</a>
        </div>
        {% endfor %}
    {% else %}
        <p>Нет материалов.</p>
    {% endif %}

    <p><a href="/">Посмотреть как ученик</a></p>
'''
)

# === Роуты ===
@app.route('/')
def index():
    lessons = load_lessons()
    return render_template_string(INDEX_TEMPLATE, lessons=lessons)

@app.route('/teacher', methods=['GET', 'POST'])
def teacher_login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == TEACHER_PASSWORD:
            return redirect(url_for('teacher_upload'))
        else:
            flash("❌ Неверный пароль!", "error")
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/upload', methods=['GET', 'POST'])
def teacher_upload():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        file = request.files.get('file')

        if not title or not file or file.filename == '':
            flash("⚠️ Заполните все поля.", "error")
        elif not allowed_file(file.filename):
            flash("❌ Недопустимый формат файла.", "error")
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
            flash("✅ Успешно добавлено!", "success")
            return redirect(url_for('teacher_upload'))

    lessons = load_lessons()
    return render_template_string(UPLOAD_TEMPLATE, lessons=lessons)

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

# === Запуск для Render ===
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)