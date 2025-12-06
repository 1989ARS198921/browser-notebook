# models.py
# -*- coding: utf-8 -*-
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False) # По умолчанию False

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username} (Admin: {self.is_admin})>'

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=True)
    content = db.Column(db.Text, nullable=True)
    full_content = db.Column(db.Text, nullable=True) # Полный HTML-контент статьи
    image_filename = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    note_type = db.Column(db.String(20), default='note') # 'note', 'list', 'image_note', 'article'
    tags = db.Column(db.String(500), nullable=True)
    background_color = db.Column(db.String(20), default='white')
    summary = db.Column(db.Text, nullable=True) # Краткое описание статьи
    preview_image = db.Column(db.String(200), nullable=True) # Изображение превью статьи
    category_ids = db.Column(db.String(200), nullable=True)
    # --- Новое поле: опубликована ли статья ---
    is_published = db.Column(db.Boolean, default=False) # По умолчанию False
    # --- /Новое поле ---
    # --- Новое поле: привязка к пользователю ---
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # --- /Новое поле ---

    # --- Связь с пользователем ---
    user = db.relationship('User', backref=db.backref('notes', lazy=True))
    # --- /Связь ---

    def __repr__(self):
        return f'<Note {self.title or "Без заголовка"}>'

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    due_date = db.Column(db.DateTime, nullable=True) # Срок выполнения
    completed = db.Column(db.Boolean, default=False) # Выполнена ли задача
    priority = db.Column(db.String(10), default='normal') # 'low', 'normal', 'high'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # --- Привязка к пользователю ---
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # --- /Привязка ---
    user = db.relationship('User', backref=db.backref('tasks', lazy=True))

    def __repr__(self):
        status = 'Выполнена' if self.completed else 'Не выполнена'
        return f'<Task {self.title} ({status})>'

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    start_time = db.Column(db.DateTime, nullable=False) # Начало события
    end_time = db.Column(db.DateTime, nullable=True) # Окончание события (может быть None)
    location = db.Column(db.String(300), nullable=True) # Место проведения
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # --- Привязка к пользователю ---
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # --- /Привязка ---
    user = db.relationship('User', backref=db.backref('events', lazy=True))

    def __repr__(self):
        return f'<Event {self.title} ({self.start_time.strftime("%d.%m.%Y %H:%M")})>'

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