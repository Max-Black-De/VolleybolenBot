#!/usr/bin/env python3
"""
Тестовый скрипт для проверки корректного подсчета людей в группах
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.database import Database
from services.event_service import EventService

def test_group_counting():
    """Тестируем корректный подсчет людей в группах"""
    print("🧪 Тестирование корректного подсчета людей в группах\n")
    
    # Инициализируем сервисы
    db = Database()
    event_service = EventService(db)
    
    # Включаем групповую запись
    db.set_bot_setting('group_registration_enabled', 'true')
    db.set_bot_setting('max_group_size', '3')
    
    # Получаем активное событие
    active_events = event_service.get_active_events()
    if not active_events:
        print("❌ Нет активных событий для тестирования")
        return
    
    event = active_events[0]
    event_id = event['id']
    
    print(f"📅 Событие: {event['name']}")
    print(f"👥 Лимит: {event['max_participants']} человек")
    
    # Очищаем участников для чистого теста
    participants = db.get_event_participants(event_id)
    for participant in participants:
        db.remove_participant(event_id, participant['telegram_id'])
    
    # === ТЕСТ 1: Проверка сценария из примера ===
    print("\n📋 ТЕСТ 1: Сценарий из примера (лимит 4 человека)")
    
    # Устанавливаем лимит 4 человека
    event_service.change_participant_limit(event_id, 4)
    
    # Записываем участников как в примере:
    # 1. Иван (1 чел) - должен быть в основном составе
    result1 = event_service.join_event_with_group(event_id, 1001, 1, "user1", "Иван", "Иванов")
    print(f"Иван (1 чел): {result1['success']} - {result1['status']}")
    
    # 2. Петя (3 чел) - должен быть в основном составе (1+3=4)
    result2 = event_service.join_event_with_group(event_id, 1002, 3, "user2", "Петя", "Петров")
    print(f"Петя (3 чел): {result2['success']} - {result2['status']}")
    
    # 3. Катя (2 чел) - должна быть в резерве (4+2=6 > 4)
    result3 = event_service.join_event_with_group(event_id, 1003, 2, "user3", "Катя", "Каткова")
    print(f"Катя (2 чел): {result3['success']} - {result3['status']}")
    
    # 4. Лена (1 чел) - должна быть в резерве (4+1=5 > 4)
    result4 = event_service.join_event_with_group(event_id, 1004, 1, "user4", "Лена", "Ленова")
    print(f"Лена (1 чел): {result4['success']} - {result4['status']}")
    
    # 5. Аня (1 чел) - должна быть в резерве (4+1=5 > 4)
    result5 = event_service.join_event_with_group(event_id, 1005, 1, "user5", "Аня", "Аннова")
    print(f"Аня (1 чел): {result5['success']} - {result5['status']}")
    
    # Показываем список участников
    print("\n👥 Список участников:")
    participants_list = event_service.get_participants_list(event_id, event)
    print(participants_list)
    
    # Проверяем статистику
    participants = db.get_event_participants(event_id)
    confirmed_people = sum(p.get('group_size', 1) for p in participants if p['status'] == 'confirmed')
    reserve_people = sum(p.get('group_size', 1) for p in participants if p['status'] == 'reserve')
    
    print(f"\n📊 Статистика:")
    print(f"Людей в основном составе: {confirmed_people}")
    print(f"Людей в резерве: {reserve_people}")
    print(f"Всего людей: {confirmed_people + reserve_people}")
    
    # === ТЕСТ 2: Проверка изменения лимита ===
    print("\n🔄 ТЕСТ 2: Изменение лимита")
    
    # Увеличиваем лимит до 6 человек
    limit_result = event_service.change_participant_limit(event_id, 6)
    print(f"Изменение лимита на 6: {limit_result['success']}")
    
    if limit_result['success']:
        print(f"Перемещено в основной состав: {len(limit_result['moved_to_main'])}")
        print(f"Перемещено в резерв: {len(limit_result['moved_to_reserve'])}")
        
        if limit_result['moved_to_main']:
            print("Переведены в основной состав:")
            for p in limit_result['moved_to_main']:
                print(f"  • {p['display_name']}")
    
    # Показываем обновленный список
    print("\n👥 Обновленный список участников:")
    participants_list = event_service.get_participants_list(event_id, event)
    print(participants_list)
    
    # Проверяем обновленную статистику
    participants = db.get_event_participants(event_id)
    confirmed_people = sum(p.get('group_size', 1) for p in participants if p['status'] == 'confirmed')
    reserve_people = sum(p.get('group_size', 1) for p in participants if p['status'] == 'reserve')
    
    print(f"\n📊 Обновленная статистика:")
    print(f"Людей в основном составе: {confirmed_people}")
    print(f"Людей в резерве: {reserve_people}")
    print(f"Всего людей: {confirmed_people + reserve_people}")
    
    # === ТЕСТ 3: Проверка отписки и перемещения из резерва ===
    print("\n🚪 ТЕСТ 3: Отписка и перемещение из резерва")
    
    # Отписываем Ивана (1 чел из основного состава)
    leave_result = event_service.leave_event(event_id, 1001)
    print(f"Отписка Ивана: {leave_result['success']}")
    
    if leave_result.get('moved_participant'):
        print(f"Перемещен из резерва: {leave_result['moved_participant']['username']}")
    
    # Показываем список после отписки
    print("\n👥 Список участников после отписки:")
    participants_list = event_service.get_participants_list(event_id, event)
    print(participants_list)
    
    # Проверяем финальную статистику
    participants = db.get_event_participants(event_id)
    confirmed_people = sum(p.get('group_size', 1) for p in participants if p['status'] == 'confirmed')
    reserve_people = sum(p.get('group_size', 1) for p in participants if p['status'] == 'reserve')
    
    print(f"\n📊 Финальная статистика:")
    print(f"Людей в основном составе: {confirmed_people}")
    print(f"Людей в резерве: {reserve_people}")
    print(f"Всего людей: {confirmed_people + reserve_people}")
    
    print("\n✅ Тестирование завершено!")

if __name__ == "__main__":
    test_group_counting() 