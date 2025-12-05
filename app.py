# app.py
# -*- coding: utf-8 -*-
import os
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, jsonify
from werkzeug.utils import secure_filename
from models import db, Note, Category, User, note_categories
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

# --- ИНИЦИАЛИЗИРУЕМ SQLAlchemy ---
db.init_app(app)

# --- Создаём таблицы в контексте приложения ---
with app.app_context():
    db.create_all()

# --- Вспомогательная функция для работы с category_ids ---
def parse_category_ids(category_ids_str):
    if category_ids_str:
        return [int(id) for id in category_ids_str.split(',')]
    return []

def format_category_ids(category_list):
    return ','.join(str(cat.id) for cat in category_list)


# --- Обновлённый маршрут главной страницы (для не-админов показывает публичные статьи) ---
@app.route('/')
def index():
    # Показываем опубликованные статьи всем (авторизованным и не авторизованным)
    # Админ может перейти на /admin для управления
    articles = Note.query.filter_by(note_type='article', is_published=True).order_by(Note.updated_at.desc()).all()
    return render_template('public_articles.html', articles=articles)

# --- Обновлённый маршрут стены ---

@app.route('/wall')
def wall():
    # Проверяем, админ ли это
    if current_user.is_authenticated and current_user.is_admin:
        # Админ видит всё
        all_notes = Note.query.order_by(Note.updated_at.desc()).all()
    else:
        # Не-админ видит только опубликованные записи (любого типа)
        # ИСПРАВЛЕНО: Фильтруем по is_published=True
        all_notes = Note.query.filter_by(is_published=True).order_by(Note.updated_at.desc()).all()

    # Получаем все категории и теги для возможной фильтрации (опционально)
    categories = Category.query.all()
    all_tags = set()
    for note in all_notes:
        if note.tags:
            all_tags.update(tag.strip() for tag in note.tags.split(','))

    # Передаём флаг is_admin в шаблон, чтобы показывать кнопки редактирования/удаления админу
    return render_template('wall.html', notes=all_notes, categories=categories, all_tags=all_tags, is_admin=current_user.is_authenticated and current_user.is_admin)

# --- Обновлённый маршрут чтения статьи ---
@app.route('/read_article/<int:id>')
def read_article(id): # Убираем @login_required
    # Проверяем, что статья опубликована, если пользователь НЕ администратор
    if current_user.is_authenticated and current_user.is_admin:
        article = Note.query.filter_by(id=id, note_type='article').first_or_404()
    else:
        article = Note.query.filter_by(id=id, note_type='article', is_published=True).first_or_404()

    note_categories = [Category.query.get(cid) for cid in parse_category_ids(article.category_ids)]
    return render_template('read_article.html', note=article, note_categories=note_categories, display_content=article.full_content)

# --- НОВЫЙ маршрут просмотра публичной заметки ---
@app.route('/view_public/<int:id>')
def view_public_note(id):
    # Проверяем, что заметка публична и не является статьей
    note = Note.query.filter_by(id=id, is_public=True).filter(Note.note_type != 'article').first_or_404()

    display_content = note.content
    note_categories = [Category.query.get(cid) for cid in parse_category_ids(note.category_ids)]
    return render_template('view.html', note=note, display_content=display_content, note_categories=note_categories)

# --- Старый маршрут просмотра (только для админов) ---
@app.route('/view/<int:id>')
@login_required
def view_note(id):
    note = Note.query.filter_by(id=id).first_or_404()
    # Проверяем, что пользователь администратор, чтобы видеть обычные заметки
    if not current_user.is_admin:
        flash('Доступ запрещён.')
        return redirect(url_for('index'))

    display_content = note.content
    note_categories = [Category.query.get(cid) for cid in parse_category_ids(note.category_ids)]
    return render_template('view.html', note=note, display_content=display_content, note_categories=note_categories)


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
            # Перенаправляем на предыдущую страницу или на главную
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Неверное имя пользователя или пароль.')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    # После выхода перенаправляем на главную (публичную)
    return redirect(url_for('index'))

# --- Отдельный маршрут для админ-панели (опционально, но рекомендуется) ---
@app.route('/admin')
@login_required
def admin_index():
    if not current_user.is_admin:
        flash('Доступ запрещён.')
        return redirect(url_for('index'))

    category_id = request.args.get('category', type=int)
    search_query = request.args.get('search', '')
    tag_filter = request.args.get('tag', '')

    query = Note.query.order_by(Note.updated_at.desc())

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
    categories = Category.query.all()
    all_tags = set()
    for note in notes:
        if note.tags:
            all_tags.update(note.tags.split(','))

    return render_template('index.html', notes=notes, categories=categories, all_tags=all_tags)


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
    user_notes = Note.query.all()
    for note in user_notes:
        ids = parse_category_ids(note.category_ids)
        if id in ids:
            ids.remove(id)
            note.category_ids = format_category_ids([Category.query.get(cid) for cid in ids])
    db.session.delete(category)
    db.session.commit()
    return redirect(url_for('list_categories'))

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
            # --- ИЗМЕНЕНО: Передаём is_published ---
            is_published=is_published
            # --- /ИЗМЕНЕНО ---
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

    note = Note.query.get_or_404(id)
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
        # --- НОВОЕ: Обновляем публикацию ---
        note.is_published = 'is_published' in request.form
        # --- /НОВОЕ ---

        note.note_type = note_type
        db.session.commit()
        return redirect(url_for('admin_index'))
    return render_template('edit.html', note=note, categories=all_categories, current_category_ids=current_category_ids)

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
            is_published=is_published
            # --- /ИЗМЕНЕНО ---
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

    article = Note.query.filter_by(id=id, note_type='article').first_or_404()

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

@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_note(id):
    if not current_user.is_admin:
        flash('Доступ запрещён.')
        return redirect(url_for('admin_index'))

    note = Note.query.get_or_404(id)
    db.session.delete(note)
    db.session.commit()
    return redirect(url_for('admin_index'))

# --- Маршрут публичных статей (теперь он же главная для не-админов) ---
@app.route('/public_articles')
def public_articles():
    # Показываем только опубликованные статьи ВСЕМ
    articles = Note.query.filter_by(note_type='article', is_published=True).order_by(Note.updated_at.desc()).all()
    return render_template('public_articles.html', articles=articles)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)