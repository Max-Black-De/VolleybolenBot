#!/usr/bin/env python3
"""
Комплексный тест функциональности записи группами
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

def test_comprehensive_groups():
    """Комплексное тестирование записи группами"""
    print("🧪 Комплексное тестирование записи группами...")
    
    # Инициализация базы данных
    db = Database("test_comprehensive.db")
    db.init_database()
    
    # Создаем тестовое событие с лимитом 6 участников
    event_service = EventService(db)
    tomorrow = date.today() + timedelta(days=1)
    event_id = event_service.create_event_on_date(tomorrow)
    
    # Устанавливаем лимит 6 участников
    event_service.change_participant_limit(event_id, 6)
    
    print(f"✅ Создано тестовое событие с ID: {event_id}, лимит: 6 участников")
    
    # === ТЕСТ 1: Базовые настройки ===
    print("\n🔧 ТЕСТ 1: Базовые настройки")
    
    # Проверяем настройки по умолчанию
    print(f"Запись группами по умолчанию: {db.is_group_registration_enabled()}")
    print(f"Максимальный размер группы по умолчанию: {db.get_max_group_size()}")
    
    # Включаем запись группами
    db.set_bot_setting('group_registration_enabled', 'true')
    db.set_bot_setting('max_group_size', '4')
    print(f"✅ Запись группами включена: {db.is_group_registration_enabled()}")
    print(f"✅ Максимальный размер группы: {db.get_max_group_size()}")
    
    # === ТЕСТ 2: Запись участников ===
    print("\n📝 ТЕСТ 2: Запись участников")
    
    # Записываем одиночных участников
    result1 = event_service.join_event_with_group(event_id, 1001, 1, "user1", "Иван", "Иванов")
    result2 = event_service.join_event_with_group(event_id, 1002, 1, "user2", "Петр", "Петров")
    print(f"Иван (1 чел): {result1['success']}")
    print(f"Петр (1 чел): {result2['success']}")
    
    # Записываем группы
    result3 = event_service.join_event_with_group(event_id, 1003, 2, "user3", "Сергей", "Сергеев")
    result4 = event_service.join_event_with_group(event_id, 1004, 3, "user4", "Алексей", "Алексеев")
    print(f"Сергей (2 чел): {result3['success']}")
    print(f"Алексей (3 чел): {result4['success']}")
    
    # Показываем список
    print("\n👥 Список участников после записи:")
    participants_list = event_service.get_participants_list(event_id)
    print(participants_list)
    
    # === ТЕСТ 3: Проверка лимитов ===
    print("\n🔢 ТЕСТ 3: Проверка лимитов")
    
    # Пытаемся записать еще одного (должно не хватить места)
    result5 = event_service.join_event_with_group(event_id, 1005, 1, "user5", "Дмитрий", "Дмитриев")
    print(f"Дмитрий (1 чел) - должно не хватить места: {result5['success']}")
    if not result5['success']:
        print(f"   Ошибка: {result5['message']}")
    
    # === ТЕСТ 4: Отписка участников ===
    print("\n🚪 ТЕСТ 4: Отписка участников")
    
    # Отписываем одиночного участника
    leave_result1 = event_service.leave_event(event_id, 1001)
    print(f"Отписка Ивана (1 чел): {leave_result1['success']}")
    
    # Отписываем группу
    leave_result2 = event_service.leave_group(event_id, 1003, 2)
    print(f"Отписка группы Сергея (2 чел): {leave_result2['success']}")
    
    # Показываем список после отписки
    print("\n👥 Список участников после отписки:")
    participants_list = event_service.get_participants_list(event_id)
    print(participants_list)
    
    # === ТЕСТ 5: Изменение лимита участников ===
    print("\n⚙️ ТЕСТ 5: Изменение лимита участников")
    
    # Увеличиваем лимит до 8
    limit_result = event_service.change_participant_limit(event_id, 8)
    print(f"Изменение лимита с 6 на 8: {limit_result['success']}")
    if limit_result['success']:
        print(f"   Перемещено в основной состав: {len(limit_result['moved_to_main'])}")
        print(f"   Перемещено в резерв: {len(limit_result['moved_to_reserve'])}")
    
    # Показываем список после изменения лимита
    print("\n👥 Список участников после изменения лимита:")
    participants_list = event_service.get_participants_list(event_id)
    print(participants_list)
    
    # === ТЕСТ 6: Граничные случаи ===
    print("\n⚠️ ТЕСТ 6: Граничные случаи")
    
    # Попытка записи группы больше максимального размера
    result6 = event_service.join_event_with_group(event_id, 1006, 5, "user6", "Евгений", "Евгеньев")
    print(f"Евгений (5 чел) - больше максимального размера: {result6['success']}")
    if not result6['success']:
        print(f"   Ошибка: {result6['message']}")
    
    # Попытка повторной записи
    result7 = event_service.join_event_with_group(event_id, 1002, 1, "user2", "Петр", "Петров")
    print(f"Повторная запись Петра: {result7['success']}")
    if not result7['success']:
        print(f"   Ошибка: {result7['message']}")
    
    # === ТЕСТ 7: Отключение групп ===
    print("\n🔌 ТЕСТ 7: Отключение групп")
    
    # Отключаем запись группами
    db.set_bot_setting('group_registration_enabled', 'false')
    print(f"✅ Запись группами отключена: {db.is_group_registration_enabled()}")
    
    # Показываем финальный список
    print("\n👥 Финальный список участников:")
    participants_list = event_service.get_participants_list(event_id)
    print(participants_list)
    
    # === ТЕСТ 8: Статистика ===
    print("\n📊 ТЕСТ 8: Статистика")
    
    participants = db.get_event_participants(event_id)
    total_participants = len(participants)
    confirmed_participants = len([p for p in participants if p['status'] == 'confirmed'])
    reserve_participants = len([p for p in participants if p['status'] == 'reserve'])
    
    print(f"Всего участников: {total_participants}")
    print(f"Основной состав: {confirmed_participants}")
    print(f"Резерв: {reserve_participants}")
    
    # Подсчитываем общее количество людей в группах
    total_people = sum(p.get('group_size', 1) for p in participants)
    print(f"Общее количество людей (с учетом групп): {total_people}")
    
    print("\n✅ Комплексное тестирование завершено!")

if __name__ == "__main__":
    test_comprehensive_groups() 