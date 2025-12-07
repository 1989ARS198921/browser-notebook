# app.py
# -*- coding: utf-8 -*-
import os
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, jsonify
from werkzeug.utils import secure_filename
from models import db, Note, Category, User, Task, Event, note_categories
from datetime import datetime
# --- Импорты для аутентификации ---
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
# --- /Импорты ---

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here' # Замените на реальный секретный ключ
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///notes.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# --- Настройки для загрузки файлов ---
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
# --- /Настройки ---

os.makedirs(os.path.join(app.root_path, app.config['UPLOAD_FOLDER']), exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Настройка Flask-Login ---
login_manager = LoginManager()
# login_manager.login_view = 'login' # Убираем, так как теперь / может быть публичной

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

login_manager.init_app(app)
# --- /Настройка Flask-Login ---

db.init_app(app)

with app.app_context():
    db.create_all()
with app.app_context():
    db.create_all()

# --- Вспомогательная функция для работы с category_ids ---
def parse_category_ids(category_ids_str):
    if category_ids_str:
        return [int(id) for id in category_ids_str.split(',')]
    return []

def format_category_ids(category_list):
    return ','.join(str(cat.id) for cat in category_list)

# --- НОВОЕ: Фильтр для отображения времени как "X назад" ---
def time_ago_filter(dt):
    if not dt:
        return "Неизвестно"

    from datetime import datetime, timedelta # Импортируем внутри функции
    now = datetime.utcnow()
    diff = now - dt

    if diff.days > 0:
        return f"{diff.days} дн. назад"
    elif diff.seconds >= 3600:
        hours = diff.seconds // 3600
        return f"{hours} ч. назад"
    elif diff.seconds >= 60:
        minutes = diff.seconds // 60
        return f"{minutes} мин. назад"
    else:
        return "Только что"

app.jinja_env.filters['time_ago'] = time_ago_filter
# --- /НОВОЕ ---
# --- Вспомогательная функция для работы с category_ids ---
def parse_category_ids(category_ids_str):
    if category_ids_str:
        return [int(id) for id in category_ids_str.split(',')]
    return []

def format_category_ids(category_list):
    return ','.join(str(cat.id) for cat in category_list)

# --- Маршрут для загрузки изображений ---
@app.route('/upload_image', methods=['POST'])
@login_required # Только для авторизованных пользователей
def upload_image():
    if not current_user.is_admin:
        return {'error': 'Access denied'}, 403

    if 'file' not in request.files:
        return {'error': 'No file part'}, 400

    file = request.files['file']

    if file.filename == '':
        return {'error': 'No file selected'}, 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        file_url = url_for('static', filename=f'uploads/{filename}')
        return {'location': file_url}
    else:
        return {'error': 'File type not allowed'}, 400

# --- Маршруты аутентификации ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Неверное имя пользователя или пароль.')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index')) # Возвращаем на главную (публичную)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Пользователь с таким именем уже существует.')
            return redirect(url_for('register'))

        new_user = User(username=username)
        new_user.set_password(password)
        # НЕ устанавливаем is_admin при регистрации
        db.session.add(new_user)
        db.session.commit()
        flash('Регистрация прошла успешно. Войдите в систему.')
        return redirect(url_for('login'))
    return render_template('register.html')

# --- Маршрут главной страницы (публичные статьи для не-админов) ---
@app.route('/')
def index():
    if current_user.is_authenticated and current_user.is_admin:
        # Админ может видеть админ-панель
        return redirect(url_for('admin_index'))
    else:
        # Показываем опубликованные статьи всем (авторизованным и не авторизованным)
        articles = Note.query.filter_by(note_type='article', is_published=True).order_by(Note.updated_at.desc()).all()
        return render_template('public_articles.html', articles=articles)

# --- Маршрут администратора ---
@app.route('/admin')
@login_required
def admin_index():
    if not current_user.is_admin:
        flash('Доступ запрещён.')
        return redirect(url_for('index'))

    category_id = request.args.get('category', type=int)
    search_query = request.args.get('search', '')
    tag_filter = request.args.get('tag', '')

    # --- ИСПРАВЛЕНО: Инициализируем query заранее ---
    # Начинаем с базового запроса: только для текущего пользователя
    base_query = Note.query.filter_by(user_id=current_user.id)
    # Сортировка по умолчанию
    query = base_query.order_by(Note.updated_at.desc())
    # --- /ИСПРАВЛЕНО ---

    # Применяем фильтры
    if category_id:
        # Проверяем, что категория существует
        category = Category.query.get_or_404(category_id)
        # Добавляем фильтр по категории
        query = query.filter(Note.category_ids.contains(str(category_id)))
    if search_query:
        # Добавляем фильтр по поиску
        query = query.filter(
            (Note.title.contains(search_query)) |
            (Note.content.contains(search_query)) |
            (Note.full_content.contains(search_query))
        )
    if tag_filter:
        # Добавляем фильтр по тегу
        query = query.filter(Note.tags.contains(tag_filter))

    # --- ИСПРАВЛЕНО: query теперь всегда определён ---
    notes = query.all()
    # --- /ИСПРАВЛЕНО ---

    # Получаем все категории и теги для фильтров (опционально)
    categories = Category.query.all()
    all_tags = set()
    for note in notes:
        if note.tags:
            all_tags.update(tag.strip() for tag in note.tags.split(','))

    return render_template('index.html', notes=notes, categories=categories, all_tags=all_tags)

# --- Стена записей ---
@app.route('/wall')
def wall():
    # Проверяем, админ ли это
    if current_user.is_authenticated and current_user.is_admin:
        # Админ видит всё
        all_notes = Note.query.order_by(Note.updated_at.desc()).all()
    else:
        # Не-админ видит только ОПУБЛИКОВАННЫЕ ЗАПИСИ (любого типа)
        # --- ИСПРАВЛЕНО: Фильтруем по is_published=True ---
        all_notes = Note.query.filter_by(is_published=True).order_by(Note.updated_at.desc()).all()
        # --- /ИСПРАВЛЕНО ---
        # Было: all_notes = Note.query.filter_by(note_type='article', is_published=True).order_by(...)

    # Получаем все категории и теги для возможной фильтрации (опционально)
    categories = Category.query.all()
    all_tags = set()
    for note in all_notes:
        if note.tags:
            all_tags.update(tag.strip() for tag in note.tags.split(','))

    # Передаём флаг is_admin в шаблон
    return render_template('wall.html', notes=all_notes, categories=categories, all_tags=all_tags, is_admin=current_user.is_authenticated and current_user.is_admin)

# --- API маршруты для AJAX ---
@app.route('/api/notes')
@login_required
def api_notes():
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403

    category_id = request.args.get('category', type=int)
    search_query = request.args.get('search', '')
    tag_filter = request.args.get('tag', '')

    query = Note.query.filter_by(user_id=current_user.id).order_by(Note.updated_at.desc())

    if category_id:
        category = Category.query.get_or_404(category_id)
        query = query.filter(Note.category_ids.contains(str(category_id)))
    if search_query:
        query = query.filter(
            Note.title.contains(search_query) |
            Note.content.contains(search_query) |
            Note.full_content.contains(search_query)
        )
    if tag_filter:
        query = query.filter(Note.tags.contains(tag_filter))

    notes = query.all()
    notes_data = []
    for note in notes:
        notes_data.append({
            'id': note.id,
            'title': note.title,
            'content_preview': note.content[:100] if note.content else '',
            'full_content_preview': note.full_content[:150] if note.full_content else '',
            'summary': note.summary,
            'note_type': note.note_type,
            'tags': note.tags.split(',') if note.tags else [],
            'background_color': note.background_color,
            'is_published': note.is_published,
            'created_at': note.created_at.isoformat(),
            'updated_at': note.updated_at.isoformat(),
            'image_filename': note.image_filename,
            'preview_image': note.preview_image,
        })

    categories = Category.query.all()
    categories_data = [{'id': cat.id, 'name': cat.name} for cat in categories]

    all_tags = set()
    for note in notes:
        if note.tags:
            all_tags.update(note.tags.split(','))

    return jsonify({'notes': notes_data, 'categories': categories_data, 'all_tags': list(all_tags)})

@app.route('/api/notes', methods=['POST'])
@login_required
def api_create_note():
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid JSON'}), 400

    title = data.get('title', '')
    content = data.get('content', '')
    note_type = data.get('type', 'note')
    selected_category_ids = data.get('categories', [])
    tags = data.get('tags', '')
    background_color = data.get('background_color', 'white')
    is_published = data.get('is_published', False)

    # Обработка изображения (если передаётся как base64 или через отдельный маршрут)
    # Пока опустим для простоты, можно реализовать позже

    category_ids_str = ','.join(map(str, selected_category_ids)) if selected_category_ids else None

    new_note = Note(
        title=title,
        content=content,
        note_type=note_type,
        category_ids=category_ids_str,
        tags=tags,
        background_color=background_color,
        is_published=is_published,
        user_id=current_user.id
    )
    db.session.add(new_note)
    db.session.commit()

    return jsonify({'message': 'Note created', 'note_id': new_note.id}), 201

@app.route('/api/notes/<int:id>', methods=['PUT'])
@login_required
def api_edit_note(id):
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403

    note = Note.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid JSON'}), 400

    note.title = data.get('title', note.title)
    note.content = data.get('content', note.content)
    note.note_type = data.get('type', note.note_type)
    note.category_ids = ','.join(map(str, data.get('categories', []))) if data.get('categories') else None
    note.tags = data.get('tags', note.tags)
    note.background_color = data.get('background_color', note.background_color)
    note.is_published = data.get('is_published', note.is_published)

    # Обработка изображения (если передаётся как base64 или через отдельный маршрут)
    # Пока опустим для простоты, можно реализовать позже

    db.session.commit()
    return jsonify({'message': 'Note updated'}), 200

@app.route('/api/notes/<int:id>', methods=['DELETE'])
@login_required
def api_delete_note(id):
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403

    note = Note.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(note)
    db.session.commit()
    return jsonify({'message': 'Note deleted'}), 200

# --- /API маршруты ---

# --- Маршруты для заметок ---
@app.route('/edit', methods=['GET', 'POST'])
@login_required
def create_note():
    if not current_user.is_admin:
        flash('Доступ запрещён.')
        return redirect(url_for('admin_index'))

    all_categories = Category.query.all()
    if request.method == 'POST':
        title = request.form.get('title', '')
        content = request.form.get('content', '')
        note_type = request.form.get('type', 'note')
        selected_category_ids = request.form.getlist('categories')
        tags = request.form.get('tags', '')
        background_color = request.form.get('background_color', 'white')
        # --- НОВОЕ: Обработка публикации ---
        is_published = 'is_published' in request.form
        # --- /НОВОЕ ---

        image_filename = None
        if 'image' in request.files:
            image = request.files['image']
            if image.filename != '' and allowed_file(image.filename):
                image_filename = secure_filename(image.filename)
                image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

        category_ids_str = ','.join(selected_category_ids) if selected_category_ids else None

        new_note = Note(
            title=title,
            content=content,
            note_type=note_type,
            image_filename=image_filename,
            category_ids=category_ids_str,
            tags=tags,
            background_color=background_color,
            is_published=is_published, # Сохраняем публикацию
            user_id=current_user.id # Привязываем к пользователю
        )
        db.session.add(new_note)
        db.session.commit()
        return redirect(url_for('admin_index'))
    return render_template('edit.html', note=Note(), categories=all_categories)

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_note(id):
    if not current_user.is_admin:
        flash('Доступ запрещён.')
        return redirect(url_for('admin_index'))

    note = Note.query.filter_by(id=id, user_id=current_user.id).first_or_404() # Проверяем владельца
    all_categories = Category.query.all()
    current_category_ids = parse_category_ids(note.category_ids)

    if request.method == 'POST':
        note.title = request.form.get('title', '')
        note.content = request.form.get('content', '')
        note_type = request.form.get('type', 'note')

        if 'image' in request.files:
            image = request.files['image']
            if image.filename != '' and allowed_file(image.filename):
                note.image_filename = secure_filename(image.filename)
                image.save(os.path.join(app.config['UPLOAD_FOLDER'], note.image_filename))

        selected_category_ids = request.form.getlist('categories')
        note.category_ids = ','.join(selected_category_ids) if selected_category_ids else None

        note.tags = request.form.get('tags', '')
        note.background_color = request.form.get('background_color', 'white')
        note.is_published = 'is_published' in request.form # Обновляем публикацию
        note.note_type = note_type
        db.session.commit()
        return redirect(url_for('admin_index'))
    return render_template('edit.html', note=note, categories=all_categories, current_category_ids=current_category_ids)

# --- Маршруты для статей ---
@app.route('/edit_article', methods=['GET', 'POST'])
@login_required
def create_article():
    if not current_user.is_admin:
        flash('Доступ запрещён.')
        return redirect(url_for('admin_index'))

    all_categories = Category.query.all()
    if request.method == 'POST':
        title = request.form.get('title', '')
        summary = request.form.get('summary', '')
        full_content = request.form.get('content', '')
        note_type = 'article'
        selected_category_ids = request.form.getlist('categories')
        tags = request.form.get('tags', '')
        background_color = request.form.get('background_color', 'white')
        # --- НОВОЕ: Обработка публикации ---
        is_published = 'is_published' in request.form
        # --- /НОВОЕ ---

        preview_image = None
        if 'preview_image' in request.files:
            image = request.files['preview_image']
            if image.filename != '' and allowed_file(image.filename):
                preview_image = secure_filename(image.filename)
                image.save(os.path.join(app.config['UPLOAD_FOLDER'], preview_image))

        category_ids_str = ','.join(selected_category_ids) if selected_category_ids else None

        new_article = Note(
            title=title,
            summary=summary,
            full_content=full_content,
            note_type=note_type,
            preview_image=preview_image,
            category_ids=category_ids_str,
            tags=tags,
            background_color=background_color,
            # --- ИЗМЕНЕНО: Передаём is_published ---
            is_published=is_published,
            # --- /ИЗМЕНЕНО ---
            user_id=current_user.id # Привязываем к пользователю
        )
        db.session.add(new_article)
        db.session.commit()
        return redirect(url_for('admin_index'))
    return render_template('edit_article.html', note=Note(), categories=all_categories)

@app.route('/edit_article/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_article(id):
    if not current_user.is_admin:
        flash('Доступ запрещён.')
        return redirect(url_for('admin_index'))

    article = Note.query.filter_by(id=id, note_type='article', user_id=current_user.id).first_or_404() # Проверяем владельца
    all_categories = Category.query.all()
    current_category_ids = parse_category_ids(article.category_ids)

    if request.method == 'POST':
        article.title = request.form.get('title', '')
        article.summary = request.form.get('summary', '')
        article.full_content = request.form.get('content', '')
        selected_category_ids = request.form.getlist('categories')
        article.tags = request.form.get('tags', '')
        article.background_color = request.form.get('background_color', 'white')
        # --- НОВОЕ: Обновляем публикацию ---
        article.is_published = 'is_published' in request.form
        # --- /НОВОЕ ---

        if 'preview_image' in request.files:
            image = request.files['preview_image']
            if image.filename != '' and allowed_file(image.filename):
                article.preview_image = secure_filename(image.filename)
                image.save(os.path.join(app.config['UPLOAD_FOLDER'], article.preview_image))

        article.category_ids = ','.join(selected_category_ids) if selected_category_ids else None
        db.session.commit()
        return redirect(url_for('admin_index'))
    return render_template('edit_article.html', note=article, categories=all_categories, current_category_ids=current_category_ids)

# --- Маршрут просмотра статьи ---
@app.route('/read_article/<int:id>')
def read_article(id):
    # Проверяем, что статья опубликована, если пользователь НЕ администратор
    if current_user.is_authenticated and current_user.is_admin:
        article = Note.query.filter_by(id=id, note_type='article').first_or_404()
    else:
        article = Note.query.filter_by(id=id, note_type='article', is_published=True).first_or_404()

    note_categories = [Category.query.get(cid) for cid in parse_category_ids(article.category_ids)]
    return render_template('read_article.html', note=article, note_categories=note_categories, display_content=article.full_content)

# --- Маршрут просмотра заметки (только для админов) ---
@app.route('/view/<int:id>')
@login_required
def view_note(id):
    note = Note.query.filter_by(id=id, user_id=current_user.id).first_or_404() # Проверяем владельца
    if not current_user.is_admin:
        flash('Доступ запрещён.')
        return redirect(url_for('index'))

    display_content = note.content
    note_categories = [Category.query.get(cid) for cid in parse_category_ids(note.category_ids)]
    return render_template('view.html', note=note, display_content=display_content, note_categories=note_categories)

# --- Маршрут удаления заметки ---
@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_note(id):
    if not current_user.is_admin:
        flash('Доступ запрещён.')
        return redirect(url_for('admin_index'))

    note = Note.query.filter_by(id=id, user_id=current_user.id).first_or_404() # Проверяем владельца
    db.session.delete(note)
    db.session.commit()
    return redirect(url_for('admin_index'))

# --- Маршруты для УПРАВЛЕНИЯ ЗАДАЧАМИ ---
@app.route('/tasks')
@login_required
def list_tasks():
    # Фильтруем задачи по пользователю
    tasks = Task.query.filter_by(user_id=current_user.id).order_by(Task.due_date.asc(), Task.priority.desc()).all()
    return render_template('tasks.html', tasks=tasks)

@app.route('/tasks/new', methods=['GET', 'POST'])
@login_required
def create_task():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form.get('description', '')
        due_date_str = request.form.get('due_date', '') # Может быть пустой строкой
        priority = request.form.get('priority', 'normal')

        due_date = None
        if due_date_str:
            try:
                # Пример формата: '2023-12-25T15:30' (ISO 8601-like, отправляется из input type="datetime-local")
                due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('Неверный формат даты/времени.')
                return redirect(url_for('create_task'))

        new_task = Task(title=title, description=description, due_date=due_date, priority=priority, user_id=current_user.id)
        db.session.add(new_task)
        db.session.commit()
        return redirect(url_for('list_tasks'))
    return render_template('edit_task.html', task=Task())

@app.route('/tasks/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_task(id):
    task = Task.query.filter_by(id=id, user_id=current_user.id).first_or_404() # Проверяем владельца

    if request.method == 'POST':
        task.title = request.form['title']
        task.description = request.form.get('description', '')
        due_date_str = request.form.get('due_date', '')
        task.priority = request.form.get('priority', 'normal')

        task.due_date = None
        if due_date_str:
            try:
                task.due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('Неверный формат даты/времени.')
                return redirect(url_for('edit_task', id=id))

        # Обработка выполнения задачи
        task.completed = 'completed' in request.form

        db.session.commit()
        return redirect(url_for('list_tasks'))
    return render_template('edit_task.html', task=task)

@app.route('/tasks/delete/<int:id>', methods=['POST'])
@login_required
def delete_task(id):
    task = Task.query.filter_by(id=id, user_id=current_user.id).first_or_404() # Проверяем владельца
    db.session.delete(task)
    db.session.commit()
    return redirect(url_for('list_tasks'))

# --- Маршруты для УПРАВЛЕНИЯ СОБЫТИЯМИ ---
@app.route('/events')
@login_required
def list_events():
    # Фильтруем события по пользователю
    events = Event.query.filter_by(user_id=current_user.id).order_by(Event.start_time.asc()).all()
    return render_template('events.html', events=events)

@app.route('/events/new', methods=['GET', 'POST'])
@login_required
def create_event():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form.get('description', '')
        start_time_str = request.form['start_time'] # Обязательное поле
        end_time_str = request.form.get('end_time', '') # Может быть пустым
        location = request.form.get('location', '')

        try:
            start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Неверный формат времени начала.')
            return redirect(url_for('create_event'))

        end_time = None
        if end_time_str:
            try:
                end_time = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('Неверный формат времени окончания.')
                return redirect(url_for('create_event'))

        new_event = Event(title=title, description=description, start_time=start_time, end_time=end_time, location=location, user_id=current_user.id)
        db.session.add(new_event)
        db.session.commit()
        return redirect(url_for('list_events'))
    return render_template('edit_event.html', event=Event())

@app.route('/events/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_event(id):
    event = Event.query.filter_by(id=id, user_id=current_user.id).first_or_404() # Проверяем владельца

    if request.method == 'POST':
        event.title = request.form['title']
        event.description = request.form.get('description', '')
        start_time_str = request.form['start_time']
        end_time_str = request.form.get('end_time', '')
        event.location = request.form.get('location', '')

        try:
            event.start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Неверный формат времени начала.')
            return redirect(url_for('edit_event', id=id))

        event.end_time = None
        if end_time_str:
            try:
                event.end_time = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('Неверный формат времени окончания.')
                return redirect(url_for('edit_event', id=id))

        db.session.commit()
        return redirect(url_for('list_events'))
    return render_template('edit_event.html', event=event)

@app.route('/events/delete/<int:id>', methods=['POST'])
@login_required
def delete_event(id):
    event = Event.query.filter_by(id=id, user_id=current_user.id).first_or_404() # Проверяем владельца
    db.session.delete(event)
    db.session.commit()
    return redirect(url_for('list_events'))

# --- Маршрут для получения событий в формате JSON (для FullCalendar) ---
@app.route('/api/events')
@login_required
def api_events():
    events = Event.query.filter_by(user_id=current_user.id).all()
    calendar_events = []
    for event in events:
        calendar_events.append({
            'id': event.id,
            'title': event.title,
            'start': event.start_time.isoformat(), # ISO 8601 строка
            'end': event.end_time.isoformat() if event.end_time else None,
            'description': event.description,
            'location': event.location
        })
    return jsonify(calendar_events)

# --- Маршрут для календаря ---
@app.route('/calendar')
@login_required
def calendar():
    return render_template('calendar.html')

# --- Маршруты для УПРАВЛЕНИЯ КАТЕГОРИЯМИ ---
@app.route('/categories')
@login_required
def list_categories():
    if not current_user.is_admin:
        flash('Доступ запрещён.')
        return redirect(url_for('index'))

    categories = Category.query.all()
    return render_template('categories.html', categories=categories)

@app.route('/categories/new', methods=['GET', 'POST'])
@login_required
def create_category():
    if not current_user.is_admin:
        flash('Доступ запрещён.')
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form['name']
        if name:
            new_category = Category(name=name)
            db.session.add(new_category)
            db.session.commit()
        return redirect(url_for('list_categories'))
    return render_template('edit_category.html', category=Category())

@app.route('/categories/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_category(id):
    if not current_user.is_admin:
        flash('Доступ запрещён.')
        return redirect(url_for('index'))

    category = Category.query.get_or_404(id)
    if request.method == 'POST':
        category.name = request.form['name']
        db.session.commit()
        return redirect(url_for('list_categories'))
    return render_template('edit_category.html', category=category)

@app.route('/categories/delete/<int:id>', methods=['POST'])
@login_required
def delete_category(id):
    if not current_user.is_admin:
        flash('Доступ запрещён.')
        return redirect(url_for('index'))

    category = Category.query.get_or_404(id)
    # Удаляем привязки категории из заметок
    all_notes = Note.query.all()
    for note in all_notes:
        ids = parse_category_ids(note.category_ids)
        if id in ids:
            ids.remove(id)
            note.category_ids = format_category_ids([Category.query.get(cid) for cid in ids])
    db.session.delete(category)
    db.session.commit()
    return redirect(url_for('list_categories'))

# --- Маршрут публичных статей ---
@app.route('/public_articles')
def public_articles():
    # Показываем опубликованные статьи ВСЕМ
    articles = Note.query.filter_by(note_type='article', is_published=True).order_by(Note.updated_at.desc()).all()
    return render_template('public_articles.html', articles=articles)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)