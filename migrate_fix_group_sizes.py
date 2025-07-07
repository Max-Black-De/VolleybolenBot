#!/usr/bin/env python3
"""
Миграция для исправления main_group_size и reserve_group_size в существующих записях
"""

import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_fix_group_sizes():
    """Исправить main_group_size и reserve_group_size в существующих записях"""
    db_path = "volleyball_bot.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Проверяем, есть ли колонки main_group_size и reserve_group_size
        cursor.execute("PRAGMA table_info(participants)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'main_group_size' not in columns or 'reserve_group_size' not in columns:
            logger.info("Колонки main_group_size и reserve_group_size не найдены. Добавляем их...")
            
            # Добавляем колонки если их нет
            try:
                cursor.execute('ALTER TABLE participants ADD COLUMN main_group_size INTEGER')
                logger.info("Добавлена колонка main_group_size")
            except sqlite3.OperationalError:
                logger.info("Колонка main_group_size уже существует")
            
            try:
                cursor.execute('ALTER TABLE participants ADD COLUMN reserve_group_size INTEGER')
                logger.info("Добавлена колонка reserve_group_size")
            except sqlite3.OperationalError:
                logger.info("Колонка reserve_group_size уже существует")
        
        # Получаем все записи участников
        cursor.execute('''
            SELECT id, status, group_size, main_group_size, reserve_group_size
            FROM participants
        ''')
        
        participants = cursor.fetchall()
        logger.info(f"Найдено {len(participants)} записей участников для обновления")
        
        updated_count = 0
        
        for participant_id, status, group_size, main_group_size, reserve_group_size in participants:
            # Если main_group_size или reserve_group_size равны NULL, обновляем их
            if main_group_size is None or reserve_group_size is None:
                if status == 'confirmed':
                    new_main_group_size = group_size or 1
                    new_reserve_group_size = 0
                elif status == 'reserve':
                    new_main_group_size = 0
                    new_reserve_group_size = group_size or 1
                elif status == 'mixed':
                    # Для mixed-статуса оставляем как есть, если есть значения
                    if main_group_size is not None and reserve_group_size is not None:
                        continue
                    else:
                        # Если нет значений, считаем что вся группа в основном составе
                        new_main_group_size = group_size or 1
                        new_reserve_group_size = 0
                else:
                    # Неизвестный статус, считаем что в основном составе
                    new_main_group_size = group_size or 1
                    new_reserve_group_size = 0
                
                # Обновляем запись
                cursor.execute('''
                    UPDATE participants 
                    SET main_group_size = ?, reserve_group_size = ?
                    WHERE id = ?
                ''', (new_main_group_size, new_reserve_group_size, participant_id))
                
                updated_count += 1
                logger.info(f"Обновлена запись {participant_id}: статус={status}, "
                           f"group_size={group_size}, main={new_main_group_size}, reserve={new_reserve_group_size}")
        
        conn.commit()
        logger.info(f"Миграция завершена. Обновлено {updated_count} записей.")
        
    except Exception as e:
        logger.error(f"Ошибка при миграции: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_fix_group_sizes() 