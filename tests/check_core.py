# test_core.py — проверка ядра TrustVote
import os
import sys

# Добавляем backend в путь, чтобы импортировать модули
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.models import init_db, DB_PATH
from backend.auth import register_user, authenticate_user
from backend.utils import generate_user_hash

def test():
    print("🔍 Запуск теста ядра TrustVote...\n")

    # 1. Инициализируем базу
    print("1. Создаём базу данных...")
    init_db()
    print(f"   → База создана: {os.path.abspath(DB_PATH)}\n")

    # 2. Регистрация пользователя
    print("2. Регистрируем пользователя 'ivan' с паролем '123456'...")
    success = register_user("ivan", "123456")
    print(f"   → Регистрация успешна: {success}\n")

    # 3. Повторная регистрация (должна провалиться)
    print("3. Повторная регистрация 'ivan' (должна быть отклонена)...")
    success2 = register_user("ivan", "qwerty")
    print(f"   → Повторная регистрация успешна: {success2} (ожидаем False)\n")

    # 4. Вход с правильным паролем
    print("4. Вход с правильным паролем...")
    user_id = authenticate_user("ivan", "123456")
    print(f"   → user_id: {user_id} (ожидаем число)\n")

    # 5. Вход с неправильным паролем
    print("5. Вход с неправильным паролем...")
    user_id_bad = authenticate_user("ivan", "wrong")
    print(f"   → user_id: {user_id_bad} (ожидаем None)\n")

    # 6. Генерация хэша пользователя
    if user_id:
        print("6. Генерация хэша для голосования...")
        user_hash = generate_user_hash("elections_10A", user_id)
        print(f"   → Хэш: {user_hash}")
        print(f"   → Длина хэша: {len(user_hash)} (должно быть 64 для SHA-256)\n")

    print("✅ Тест завершён! Проверьте файл trustvote.db — он должен появиться.")

if __name__ == "__main__":
    test()