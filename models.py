# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=True)
    content = db.Column(db.Text, nullable=True) # Краткое описание или основной контент для обычных заметок
    full_content = db.Column(db.Text, nullable=True) # Полный HTML-контент статьи
    image_filename = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # --- Типы: 'note', 'list', 'image_note', 'article' ---
    note_type = db.Column(db.String(20), default='note')
    # --- Поля для Google Keep-подобного функционала ---
    tags = db.Column(db.String(500), nullable=True)
    background_color = db.Column(db.String(20), default='white')
    # --- Поля для статей ---
    summary = db.Column(db.Text, nullable=True) # Краткое описание статьи
    preview_image = db.Column(db.String(200), nullable=True) # Изображение превью статьи
    # --- /Поля для статей ---
    category_ids = db.Column(db.String(200), nullable=True)

    def __repr__(self):
        return f'<Note {self.title or "Без заголовка"}>'

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    notes = db.relationship('Note', secondary='note_categories', lazy='subquery', backref=db.backref('categories', lazy=True))

    def __repr__(self):
        return f'<Category {self.name}>'

note_categories = db.Table('note_categories',
    db.Column('note_id', db.Integer, db.ForeignKey('note.id'), primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('category.id'), primary_key=True)
)