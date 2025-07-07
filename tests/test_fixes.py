#!/usr/bin/env python3
"""
Тестовый скрипт для проверки всех исправлений
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.database import Database
from services.event_service import EventService

def test_all_fixes():
    """Тестируем все исправления"""
    print("🧪 Тестирование всех исправлений\n")
    
    # Инициализируем сервисы
    db = Database()
    event_service = EventService(db)
    
    # === ТЕСТ 1: Проверка лимита участников ===
    print("🔢 ТЕСТ 1: Проверка лимита участников")
    
    active_events = event_service.get_active_events()
    if not active_events:
        print("❌ Нет активных событий для тестирования")
        return
    
    event = active_events[0]
    event_id = event['id']
    current_limit = event['max_participants']
    
    print(f"📅 Событие: {event['name']}")
    print(f"🆔 ID события: {event_id}")
    print(f"👥 Текущий лимит: {current_limit}")
    
    # Тестируем изменение лимита
    new_limit = current_limit + 2
    result = event_service.change_participant_limit(event_id, new_limit)
    
    if result['success']:
        print("✅ Лимит участников успешно изменен!")
        print(f"📊 Перемещено в основной состав: {len(result['moved_to_main'])}")
        print(f"📊 Перемещено в резерв: {len(result['moved_to_reserve'])}")
        
        # Возвращаем лимит обратно
        result_back = event_service.change_participant_limit(event_id, current_limit)
        if result_back['success']:
            print("✅ Лимит успешно возвращен!")
        else:
            print(f"❌ Ошибка при возврате лимита: {result_back['message']}")
    else:
        print(f"❌ Ошибка при изменении лимита: {result['message']}")
    
    # === ТЕСТ 2: Проверка групповой записи с кнопками +1/+2 ===
    print("\n👥 ТЕСТ 2: Проверка групповой записи")
    
    # Включаем групповую запись
    db.set_bot_setting('group_registration_enabled', 'true')
    db.set_bot_setting('max_group_size', '3')
    
    print(f"✅ Запись группами включена: {db.is_group_registration_enabled()}")
    print(f"✅ Максимальный размер группы: {db.get_max_group_size()}")
    
    # Очищаем участников для чистого теста
    participants = db.get_event_participants(event_id)
    for participant in participants:
        db.remove_participant(event_id, participant['telegram_id'])
    
    # Тестируем запись с разными размерами групп (имитируем кнопки +1/+2)
    test_users = [
        (1001, 1, "user1", "Иван", "Иванов"),  # 1 человек
        (1002, 2, "user2", "Петр", "Петров"),  # +1 (2 человека)
        (1003, 3, "user3", "Сергей", "Сергеев"),  # +2 (3 человека)
    ]
    
    for telegram_id, group_size, username, first_name, last_name in test_users:
        result = event_service.join_event_with_group(
            event_id, telegram_id, group_size, username, first_name, last_name
        )
        print(f"Запись {first_name} (группа {group_size}): {result['success']}")
        if not result['success']:
            print(f"   Ошибка: {result['message']}")
    
    # Показываем список участников
    print("\n👥 Список участников после записи:")
    participants_list = event_service.get_participants_list(event_id, event)
    print(participants_list)
    
    # === ТЕСТ 3: Проверка отписки групп ===
    print("\n🚪 ТЕСТ 3: Проверка отписки групп")
    
    # Отписываем группу из 2 человек
    leave_result = event_service.leave_group(event_id, 1002, 2)
    print(f"Отписка группы Петра (2 чел): {leave_result['success']}")
    
    # Отписываем одиночного участника
    leave_result2 = event_service.leave_event(event_id, 1001)
    print(f"Отписка Ивана (1 чел): {leave_result2['success']}")
    
    # Показываем список после отписки
    print("\n👥 Список участников после отписки:")
    participants_list = event_service.get_participants_list(event_id, event)
    print(participants_list)
    
    # === ТЕСТ 4: Проверка настроек ===
    print("\n🔧 ТЕСТ 4: Проверка настроек")
    
    settings = {
        'group_registration_enabled': db.is_group_registration_enabled(),
        'max_group_size': db.get_max_group_size(),
    }
    
    for key, value in settings.items():
        print(f"✅ {key}: {value}")
    
    # === ТЕСТ 5: Проверка админских функций ===
    print("\n👑 ТЕСТ 5: Проверка админских функций")
    
    # Проверяем статистику
    total_users = db.get_total_users_count()
    participants = db.get_event_participants(event_id)
    participants_count = len(participants)
    
    print(f"📊 Всего пользователей: {total_users}")
    print(f"📊 Участников на событии: {participants_count}")
    
    # Проверяем, что событие можно найти по ID
    event_found = event_service.get_event_by_id(event_id)
    if event_found:
        print(f"✅ Событие найдено по ID: {event_found['name']}")
    else:
        print("❌ Событие не найдено по ID")
    
    print("\n✅ Все тесты завершены!")

if __name__ == "__main__":
    test_all_fixes() 