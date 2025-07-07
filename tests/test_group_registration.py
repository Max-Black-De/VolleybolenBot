#!/usr/bin/env python3
"""
Тест функциональности записи группами
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.database import Database
from services.event_service import EventService
from datetime import date, timedelta
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_group_registration():
    """Тестирование записи группами"""
    print("🧪 Тестирование записи группами...")
    
    # Инициализация базы данных
    db = Database("test_volleyball_bot.db")
    db.init_database()
    
    # Включаем запись группами
    db.set_bot_setting('group_registration_enabled', 'true')
    db.set_bot_setting('max_group_size', '3')
    
    # Создаем тестовое событие
    event_service = EventService(db)
    tomorrow = date.today() + timedelta(days=1)
    event_id = event_service.create_event_on_date(tomorrow)
    
    print(f"✅ Создано тестовое событие с ID: {event_id}")
    
    # Тест 1: Запись одного участника
    print("\n📝 Тест 1: Запись одного участника")
    result = event_service.join_event_with_group(event_id, 1001, 1, "user1", "Иван", "Иванов")
    print(f"Результат: {result}")
    
    # Тест 2: Запись группы из 2 человек
    print("\n📝 Тест 2: Запись группы из 2 человек")
    result = event_service.join_event_with_group(event_id, 1002, 2, "user2", "Петр", "Петров")
    print(f"Результат: {result}")
    
    # Тест 3: Запись группы из 3 человек
    print("\n📝 Тест 3: Запись группы из 3 человек")
    result = event_service.join_event_with_group(event_id, 1003, 3, "user3", "Сергей", "Сергеев")
    print(f"Результат: {result}")
    
    # Тест 4: Попытка повторной записи
    print("\n📝 Тест 4: Попытка повторной записи")
    result = event_service.join_event_with_group(event_id, 1001, 1, "user1", "Иван", "Иванов")
    print(f"Результат: {result}")
    
    # Показываем список участников
    print("\n👥 Список участников:")
    participants_list = event_service.get_participants_list(event_id)
    print(participants_list)
    
    # Тест 5: Отписка одного участника
    print("\n📝 Тест 5: Отписка одного участника")
    result = event_service.leave_event(event_id, 1001)
    print(f"Результат: {result}")
    
    # Тест 6: Отписка группы
    print("\n📝 Тест 6: Отписка группы")
    result = event_service.leave_group(event_id, 1002, 2)
    print(f"Результат: {result}")
    
    # Показываем финальный список участников
    print("\n👥 Финальный список участников:")
    participants_list = event_service.get_participants_list(event_id)
    print(participants_list)
    
    # Тест настроек
    print("\n⚙️ Тест настроек:")
    print(f"Запись группами включена: {db.is_group_registration_enabled()}")
    print(f"Максимальный размер группы: {db.get_max_group_size()}")
    
    # Отключаем запись группами
    db.set_bot_setting('group_registration_enabled', 'false')
    print(f"Запись группами отключена: {db.is_group_registration_enabled()}")
    
    print("\n✅ Все тесты завершены!")

if __name__ == "__main__":
    test_group_registration() 