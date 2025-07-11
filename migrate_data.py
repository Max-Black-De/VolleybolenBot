#!/usr/bin/env python3
"""
Скрипт для миграции данных между пересборками контейнера
Используется для сохранения данных при обновлении бота
"""

import os
import shutil
import sqlite3
import logging
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def backup_database():
    """Создать резервную копию базы данных"""
    db_path = os.getenv('DATABASE_PATH', '/data/volleyball_bot.db')
    backup_path = f"{db_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    if os.path.exists(db_path):
        try:
            shutil.copy2(db_path, backup_path)
            logger.info(f"Создана резервная копия: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Ошибка при создании резервной копии: {e}")
    return None

def restore_database():
    """Восстановить базу данных из резервной копии"""
    db_path = os.getenv('DATABASE_PATH', '/data/volleyball_bot.db')
    
    # Ищем последнюю резервную копию
    backup_files = [f for f in os.listdir('.') if f.startswith('volleyball_bot.db.backup.')]
    if backup_files:
        latest_backup = max(backup_files)
        try:
            shutil.copy2(latest_backup, db_path)
            logger.info(f"Восстановлена база данных из: {latest_backup}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при восстановлении базы данных: {e}")
    return False

def check_database_integrity():
    """Проверить целостность базы данных"""
    db_path = os.getenv('DATABASE_PATH', '/data/volleyball_bot.db')
    
    if not os.path.exists(db_path):
        logger.warning("База данных не найдена")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Проверяем основные таблицы
        tables = ['events', 'users', 'participants', 'bot_settings']
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            logger.info(f"Таблица {table}: {count} записей")
        
        conn.close()
        logger.info("Проверка целостности базы данных завершена успешно")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при проверке целостности базы данных: {e}")
        return False

if __name__ == "__main__":
    logger.info("Запуск скрипта миграции данных")
    
    # Проверяем целостность текущей базы
    if not check_database_integrity():
        logger.info("Попытка восстановления из резервной копии")
        if restore_database():
            check_database_integrity()
        else:
            logger.info("Резервная копия не найдена, будет создана новая база")
    
    # Создаем резервную копию перед обновлением
    backup_database()
    
    logger.info("Миграция данных завершена") 