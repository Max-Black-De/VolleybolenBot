#!/usr/bin/env python3
"""
Скрипт для очистки тестовых данных из базы данных
"""

import sqlite3
import logging
from datetime import datetime, date

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cleanup_test_data():
    """Очистить тестовые данные из базы данных"""
    db_path = "volleyball_bot.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        logger.info("Начинаем очистку тестовых данных...")
        
        # 1. Удаляем тестовых пользователей (по telegram_id)
        test_telegram_ids = [
            24, 26, 1001, 1002, 1003, 1004,  # Из предыдущих тестов
            2001, 2002, 2003, 2004, 2005,  # Фейковые пользователи
            3598919,  # Ваш ID (если нужно)
            # Добавьте сюда другие тестовые ID
        ]
        
        if test_telegram_ids:
            # Получаем внутренние user_id по telegram_id
            placeholders = ','.join(['?' for _ in test_telegram_ids])
            cursor.execute(f'SELECT id FROM users WHERE telegram_id IN ({placeholders})', test_telegram_ids)
            user_ids = [row[0] for row in cursor.fetchall()]
            
            if user_ids:
                # Удаляем из участников
                cursor.executemany('DELETE FROM participants WHERE user_id = ?', [(uid,) for uid in user_ids])
                logger.info(f"Удалено {cursor.rowcount} записей участников для тестовых пользователей")
                
                # Удаляем из пользователей
                cursor.executemany('DELETE FROM users WHERE id = ?', [(uid,) for uid in user_ids])
                logger.info(f"Удалено {cursor.rowcount} тестовых пользователей")
            else:
                logger.info("Тестовые пользователи не найдены")
        
        # 2. Удаляем события с тестовыми датами (прошедшие и будущие тестовые)
        today = date.today()
        
        # Удаляем все события (можно ограничить по дате если нужно)
        cursor.execute('DELETE FROM events')
        deleted_events = cursor.rowcount
        logger.info(f"Удалено {deleted_events} событий")
        
        # 3. Очищаем историю чата для тестовых пользователей
        if test_telegram_ids:
            placeholders = ','.join(['?' for _ in test_telegram_ids])
            cursor.execute(f'DELETE FROM chat_history WHERE telegram_id IN ({placeholders})', test_telegram_ids)
            logger.info(f"Удалено {cursor.rowcount} записей истории чата для тестовых пользователей")
        
        # 4. Сбрасываем настройки бота к значениям по умолчанию
        cursor.execute('DELETE FROM bot_settings')
        cursor.execute('''
            INSERT INTO bot_settings (key, value) VALUES 
            ('group_registration_enabled', 'false'),
            ('max_group_size', '3')
        ''')
        logger.info("Настройки бота сброшены к значениям по умолчанию")
        
        conn.commit()
        logger.info("Очистка тестовых данных завершена успешно!")
        
        # Показываем статистику
        cursor.execute('SELECT COUNT(*) FROM users')
        users_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM events')
        events_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM participants')
        participants_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM chat_history')
        chat_history_count = cursor.fetchone()[0]
        
        logger.info(f"\n📊 Статистика после очистки:")
        logger.info(f"Пользователей: {users_count}")
        logger.info(f"Событий: {events_count}")
        logger.info(f"Участников: {participants_count}")
        logger.info(f"Записей истории чата: {chat_history_count}")
        
    except Exception as e:
        logger.error(f"Ошибка при очистке тестовых данных: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    cleanup_test_data() 