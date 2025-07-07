#!/usr/bin/env python3
"""
Миграция для добавления поддержки разделенных групп
"""

import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = 'volleyball_bot.db'

def migrate_split_groups():
    """Добавить колонки для разделенных групп"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Проверяем, существуют ли уже колонки
        cursor.execute("PRAGMA table_info(participants)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Добавляем колонку main_group_size
        if 'main_group_size' not in columns:
            cursor.execute('ALTER TABLE participants ADD COLUMN main_group_size INTEGER')
            logger.info("Добавлена колонка main_group_size")
        else:
            logger.info("Колонка main_group_size уже существует")
        
        # Добавляем колонку reserve_group_size
        if 'reserve_group_size' not in columns:
            cursor.execute('ALTER TABLE participants ADD COLUMN reserve_group_size INTEGER')
            logger.info("Добавлена колонка reserve_group_size")
        else:
            logger.info("Колонка reserve_group_size уже существует")
        
        conn.commit()
        logger.info("Миграция завершена успешно!")
        
    except Exception as e:
        logger.error(f"Ошибка при миграции: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_split_groups() 