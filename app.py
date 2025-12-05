# app.py
import os
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
from models import db, Note, Category, note_categories
from datetime import datetime

app = Flask(__name__)
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

db.init_app(app)

with app.app_context():
    db.create_all()

# --- Вспомогательная функция для работы с category_ids ---
def parse_category_ids(category_ids_str):
    if category_ids_str:
        return [int(id) for id in category_ids_str.split(',')]
    return []

def format_category_ids(category_list):
    return ','.join(str(cat.id) for cat in category_list)

# --- Маршрут для загрузки изображений ---
@app.route('/upload_image', methods=['POST'])
def upload_image():
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

# --- Маршруты ---
@app.route('/')
def index():
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
            Note.full_content.contains(search_query) # Поиск и по статьям
        )
    if tag_filter:
        query = query.filter(Note.tags.contains(tag_filter))

    notes = query.all()
    categories = Category.query.all()
    all_tags = set()
    for note in notes:
        if note.tags:
            all_tags.update(note.tags.split(','))

    return render_template('index.html', notes=notes, categories=categories, selected_category=category_id, search_query=search_query, all_tags=all_tags, selected_tag=tag_filter)

@app.route('/categories')
def list_categories():
    categories = Category.query.all()
    return render_template('categories.html', categories=categories)

@app.route('/categories/new', methods=['GET', 'POST'])
def create_category():
    if request.method == 'POST':
        name = request.form['name']
        if name:
            new_category = Category(name=name)
            db.session.add(new_category)
            db.session.commit()
        return redirect(url_for('list_categories'))
    return render_template('edit_category.html', category=Category())

@app.route('/categories/edit/<int:id>', methods=['GET', 'POST'])
def edit_category(id):
    category = Category.query.get_or_404(id)
    if request.method == 'POST':
        category.name = request.form['name']
        db.session.commit()
        return redirect(url_for('list_categories'))
    return render_template('edit_category.html', category=category)

@app.route('/categories/delete/<int:id>', methods=['POST'])
def delete_category(id):
    category = Category.query.get_or_404(id)
    notes = Note.query.filter(Note.category_ids.contains(str(id)))
    for note in notes:
        ids = parse_category_ids(note.category_ids)
        if id in ids:
            ids.remove(id)
            note.category_ids = format_category_ids([Category.query.get(cid) for cid in ids])
    db.session.delete(category)
    db.session.commit()
    return redirect(url_for('list_categories'))

@app.route('/edit', methods=['GET', 'POST'])
def create_note():
    all_categories = Category.query.all()
    if request.method == 'POST':
        title = request.form.get('title', '')
        content = request.form.get('content', '')
        note_type = request.form.get('type', 'note')
        selected_category_ids = request.form.getlist('categories')
        tags = request.form.get('tags', '')
        background_color = request.form.get('background_color', 'white')

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
            background_color=background_color
        )
        db.session.add(new_note)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('edit.html', note=Note(), categories=all_categories)

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_note(id):
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

        note.note_type = note_type
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('edit.html', note=note, categories=all_categories, current_category_ids=current_category_ids)

# --- НОВЫЙ маршрут: Редактирование статьи ---
@app.route('/edit_article', methods=['GET', 'POST'])
def create_article():
    all_categories = Category.query.all()
    if request.method == 'POST':
        title = request.form.get('title', '')
        summary = request.form.get('summary', '') # Краткое описание
        full_content = request.form.get('content', '') # Полный HTML-контент статьи
        # note_type для статьи
        note_type = 'article'
        selected_category_ids = request.form.getlist('categories')
        tags = request.form.get('tags', '')
        # background_color не используется для статьи, можно убрать или оставить
        background_color = request.form.get('background_color', 'white')

        preview_image = None # Изображение превью статьи
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
            background_color=background_color
        )
        db.session.add(new_article)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('edit_article.html', note=Note(), categories=all_categories)

@app.route('/edit_article/<int:id>', methods=['GET', 'POST'])
def edit_article(id):
    article = Note.query.get_or_404(id)
    if article.note_type != 'article':
        # Перенаправить, если попытались отредактировать не статью как статью
        return redirect(url_for('edit_note', id=id))

    all_categories = Category.query.all()
    current_category_ids = parse_category_ids(article.category_ids)

    if request.method == 'POST':
        article.title = request.form.get('title', '')
        article.summary = request.form.get('summary', '')
        article.full_content = request.form.get('content', '')
        # note_type остаётся 'article'
        selected_category_ids = request.form.getlist('categories')
        article.tags = request.form.get('tags', '')
        article.background_color = request.form.get('background_color', 'white')

        if 'preview_image' in request.files:
            image = request.files['preview_image']
            if image.filename != '' and allowed_file(image.filename):
                article.preview_image = secure_filename(image.filename)
                image.save(os.path.join(app.config['UPLOAD_FOLDER'], article.preview_image))

        article.category_ids = ','.join(selected_category_ids) if selected_category_ids else None
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('edit_article.html', note=article, categories=all_categories, current_category_ids=current_category_ids)

# --- НОВЫЙ маршрут: Чтение статьи ---
@app.route('/read_article/<int:id>')
def read_article(id):
    article = Note.query.get_or_404(id)
    if article.note_type != 'article':
        # Перенаправить, если попытались открыть не статью как статью
        return redirect(url_for('view_note', id=id))

    note_categories = [Category.query.get(cid) for cid in parse_category_ids(article.category_ids)]
    return render_template('read_article.html', note=article, note_categories=note_categories, display_content=article.full_content)

@app.route('/view/<int:id>')
def view_note(id):
    note = Note.query.get_or_404(id)
    display_content = note.content
    note_categories = [Category.query.get(cid) for cid in parse_category_ids(note.category_ids)]
    return render_template('view.html', note=note, display_content=display_content, note_categories=note_categories)

@app.route('/delete/<int:id>', methods=['POST'])
def delete_note(id):
    note = Note.query.get_or_404(id)
    db.session.delete(note)
    db.session.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)