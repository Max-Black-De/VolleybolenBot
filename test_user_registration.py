#!/usr/bin/env python3
"""
Тестовый скрипт для проверки исправлений регистрации пользователей
"""

import sqlite3
from db.database import Database

def test_user_registration():
    """Тестируем исправленную логику регистрации пользователей"""
    db = Database()
    
    # Тестовые данные
    test_telegram_id = 999999999
    test_username = "test_user"
    test_first_name = "Test"
    test_last_name = "User"
    
    print("🧪 Тестирование исправленной регистрации пользователей...")
    
    # Шаг 1: Регистрируем пользователя впервые
    print(f"\n1️⃣ Регистрируем пользователя {test_telegram_id} впервые...")
    user_id_1 = db.add_user(test_telegram_id, test_username, test_first_name, test_last_name)
    print(f"   ✅ Создан пользователь с ID: {user_id_1}")
    
    # Проверяем, что пользователь создался
    user = db.get_user_by_telegram_id(test_telegram_id)
    print(f"   📋 Данные пользователя: {user}")
    
    # Шаг 2: Пытаемся зарегистрировать того же пользователя с новыми данными
    print(f"\n2️⃣ Регистрируем того же пользователя {test_telegram_id} с обновленными данными...")
    new_username = "updated_test_user"
    new_first_name = "Updated"
    new_last_name = "User"
    
    user_id_2 = db.add_user(test_telegram_id, new_username, new_first_name, new_last_name)
    print(f"   ✅ Возвращен ID: {user_id_2}")
    
    # Проверяем, что ID тот же самый
    if user_id_1 == user_id_2:
        print(f"   ✅ ID совпадают - дубликат не создался!")
    else:
        print(f"   ❌ ID не совпадают - создался дубликат!")
    
    # Проверяем обновленные данные
    updated_user = db.get_user_by_telegram_id(test_telegram_id)
    print(f"   📋 Обновленные данные: {updated_user}")
    
    # Шаг 3: Проверяем количество записей
    print(f"\n3️⃣ Проверяем количество записей для telegram_id {test_telegram_id}...")
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users WHERE telegram_id = ?', (test_telegram_id,))
        count = cursor.fetchone()[0]
        print(f"   📊 Количество записей: {count}")
        
        if count == 1:
            print(f"   ✅ Отлично! Только одна запись - дубликатов нет!")
        else:
            print(f"   ❌ Проблема! Найдено {count} записей - есть дубликаты!")
    
    # Шаг 4: Очистка тестовых данных
    print(f"\n4️⃣ Очищаем тестовые данные...")
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM users WHERE telegram_id = ?', (test_telegram_id,))
        conn.commit()
        print(f"   ✅ Тестовые данные удалены")
    
    print(f"\n🎉 Тест завершен!")

if __name__ == "__main__":
    test_user_registration() 