import sqlite3

DB_PATH = 'volleyball_bot.db'
USER_IDS_TO_DELETE = [24, 26, 1001, 1002, 1003]

def delete_test_users():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Получаем внутренние user_id по telegram_id
    placeholders = ','.join(['?' for _ in USER_IDS_TO_DELETE])
    cursor.execute(f'SELECT id FROM users WHERE telegram_id IN ({placeholders})', USER_IDS_TO_DELETE)
    user_ids = [row[0] for row in cursor.fetchall()]
    if user_ids:
        # Удаляем из участников
        cursor.executemany('DELETE FROM participants WHERE user_id = ?', [(uid,) for uid in user_ids])
        # Удаляем из пользователей
        cursor.executemany('DELETE FROM users WHERE id = ?', [(uid,) for uid in user_ids])
        conn.commit()
        print(f"Удалены пользователи с telegram_id: {USER_IDS_TO_DELETE}")
    else:
        print("Нет пользователей для удаления.")
    conn.close()

if __name__ == "__main__":
    delete_test_users()

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Проверяем, есть ли уже столбец group_size
cursor.execute("PRAGMA table_info(participants);")
columns = [row[1] for row in cursor.fetchall()]

if 'group_size' not in columns:
    cursor.execute("ALTER TABLE participants ADD COLUMN group_size INTEGER DEFAULT 1;")
    print("Столбец group_size успешно добавлен!")
else:
    print("Столбец group_size уже существует.")

conn.commit()
conn.close()
print("Миграция завершена!") 