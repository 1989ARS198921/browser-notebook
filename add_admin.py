# add_admin.py
# -*- coding: utf-8 -*-

"""
Скрипт для добавления администратора в базу данных notes.db.
Использует модель User из models.py.
"""

from app import app, db
from models import User

def add_admin_user():
    """Добавляет администратора Ars1 с паролем Admin1."""
    username = 'Ars1'
    password = 'Admin1'

    with app.app_context():
        # Проверяем, существует ли уже пользователь с таким именем
        existing_user = User.query.filter_by(username=username).first()

        if existing_user:
            print(f"Пользователь '{username}' уже существует.")
            if existing_user.is_admin:
                print(f"Пользователь '{username}' уже является администратором.")
            else:
                print(f"Пользователь '{username}' НЕ является администратором. Обновляем...")
                existing_user.is_admin = True
                db.session.commit()
                print(f"Теперь пользователь '{username}' является администратором.")
        else:
            # Создаём нового пользователя
            new_admin = User(username=username)
            new_admin.set_password(password) # Важно: используем метод модели для хэширования
            new_admin.is_admin = True # Устанавливаем флаг администратора

            db.session.add(new_admin)
            db.session.commit()
            print(f"Администратор '{username}' успешно создан.")

if __name__ == '__main__':
    add_admin_user()