# backend/auth.py
import hashlib
import sqlite3
from typing import Optional
from .models import DB_PATH

# Секретная "соль" — усложняет взлом паролей
PASSWORD_SALT = "trustvote_salt_2025_secure"

def hash_password(password: str) -> str:
    """Превращает пароль в необратимый хэш"""
    return hashlib.sha256((password + PASSWORD_SALT).encode()).hexdigest()

def register_user(username: str, password: str) -> bool:
    """Регистрирует нового пользователя. Возвращает True, если успешно."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, hash_password(password))
            )
        return True
    except sqlite3.IntegrityError:
        # Пользователь с таким именем уже есть
        return False

def authenticate_user(username: str, password: str) -> Optional[int]:
    """Проверяет логин/пароль. Возвращает user_id или None."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, password_hash FROM users WHERE username = ?",
            (username,)
        )
        row = cursor.fetchone()
        if row and row[1] == hash_password(password):
            return row[0]  # id пользователя
    return None