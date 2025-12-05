# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# Таблица связи многие-ко-многим для тегов/категорий (если нужно)
note_categories = db.Table('note_categories',
    db.Column('note_id', db.Integer, db.ForeignKey('note.id'), primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('category.id'), primary_key=True)
)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    # Связь с заметками
    notes = db.relationship('Note', secondary=note_categories, lazy='subquery', backref=db.backref('categories', lazy=True))

    def __repr__(self):
        return f'<Category {self.name}>'

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    full_content = db.Column(db.Text, nullable=True)
    image_filename = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    note_type = db.Column(db.String(20), default='note')

    # Связь с категориями
    category_ids = db.Column(db.String(200), nullable=True) # Хранит список ID категорий как строку, например "1,2,3"

    def __repr__(self):
        return f'<Note {self.title}>'