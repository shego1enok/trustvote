# backend/utils.py
import hashlib
import base64
import secrets
import string

def generate_session_id(length=12):
    """Генерирует уникальный идентификатор сессии голосования"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_user_hash(session_id, user_id):
    """
    Генерирует уникальный, но анонимный хэш для пользователя в рамках сессии голосования.
    Используется для предотвращения повторного голосования.
    """
    raw = f"trustvote:{session_id}:{user_id}"
    hash_obj = hashlib.sha256(raw.encode('utf-8'))
    # Сокращаем до 16 символов для удобства отображения
    return base64.urlsafe_b64encode(hash_obj.digest()).decode('utf-8')[:16]