# app.py
from flask import Flask, render_template, request, redirect, url_for
from models import db, Note, Category
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///notes.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

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

# --- Маршруты ---
@app.route('/')
def index():
    # Получаем ID категории из параметров URL (если есть)
    category_id = request.args.get('category', type=int)
    search_query = request.args.get('search', '')

    query = Note.query.order_by(Note.created_at.desc())

    if category_id:
        category = Category.query.get_or_404(category_id)
        # Фильтруем заметки по ID категории, хранящейся в строке
        query = query.filter(Note.category_ids.contains(str(category_id)))
    if search_query:
        query = query.filter(
            Note.title.contains(search_query) |
            Note.content.contains(search_query)
        )

    notes = query.all()

    # Получаем все категории для боковой панели
    categories = Category.query.all()

    return render_template('index.html', notes=notes, categories=categories, selected_category=category_id, search_query=search_query)

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
    # Удаляем категорию из всех заметок, которые её содержат
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
        title = request.form['title']
        content = request.form['content']
        note_type = request.form.get('type', 'note')
        selected_category_ids = request.form.getlist('categories') # Получаем список ID

        image_filename = None
        if 'image' in request.files:
            image = request.files['image']
            if image.filename != '':
                image_filename = image.filename

        # Форматируем список ID категорий в строку
        category_ids_str = ','.join(selected_category_ids) if selected_category_ids else None

        new_note = Note(title=title, content=content, note_type=note_type, image_filename=image_filename, category_ids=category_ids_str)
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
        note.title = request.form['title']
        note.content = request.form['content']
        note_type = request.form.get('type', 'note')

        if 'image' in request.files:
            image = request.files['image']
            if image.filename != '':
                note.image_filename = image.filename

        selected_category_ids = request.form.getlist('categories')
        note.category_ids = ','.join(selected_category_ids) if selected_category_ids else None

        note.note_type = note_type
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('edit.html', note=note, categories=all_categories, current_category_ids=current_category_ids)

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