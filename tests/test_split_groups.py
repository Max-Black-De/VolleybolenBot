#!/usr/bin/env python3
"""
Тест для проверки логики разделения групп
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.database import Database
from services.event_service import EventService
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_split_groups():
    """Тест разделения групп при лимите участников"""
    db = Database()
    event_service = EventService(db)
    
    # Создаем тестовое событие с лимитом 4 человека
    tomorrow = datetime.now() + timedelta(days=1)
    event_date = tomorrow.date()
    
    event_id = db.create_event('Тестовая тренировка', event_date, '19:00', 4)
    
    # Очищаем участников для чистого теста
    participants = db.get_event_participants(event_id)
    for participant in participants:
        db.remove_participant(event_id, participant['telegram_id'])
    logger.info(f"Создано событие с ID: {event_id}")
    
    # Тест 1: Иван регистрируется с группой из 3 человек
    result1 = event_service.join_event_with_group(
        event_id, 1001, 3, 
        username='ivan_test', first_name='Иван', last_name='Иванов'
    )
    logger.info(f"Иван (3 чел): {result1}")
    
    # Проверяем список участников
    event = db.get_event_by_id(event_id)
    participants_list = event_service.get_participants_list(event_id, event)
    logger.info(f"Участники после Ивана:\n{participants_list}")
    
    # Тест 2: Петя регистрируется с группой из 3 человек
    result2 = event_service.join_event_with_group(
        event_id, 1002, 3, 
        username='petya_test', first_name='Петр', last_name='Петров'
    )
    logger.info(f"Петя (3 чел): {result2}")
    
    # Проверяем финальный список участников
    participants_list = event_service.get_participants_list(event_id, event)
    logger.info(f"Финальный список участников:\n{participants_list}")
    
    # Проверяем детали участников
    db_participants = db.get_event_participants(event_id)
    for p in db_participants:
        logger.info(f"Участник {p['first_name']}: статус={p['status']}, "
                   f"группа={p['group_size']}, основной={p.get('main_group_size')}, "
                   f"резерв={p.get('reserve_group_size')}")
    
    # Очищаем тестовые данные
    participants = db.get_event_participants(event_id)
    for participant in participants:
        db.remove_participant(event_id, participant['telegram_id'])
    logger.info("Тест завершен!")

if __name__ == "__main__":
    test_split_groups() 