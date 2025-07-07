#!/usr/bin/env python3
"""
Тестовый скрипт для проверки функции изменения лимита участников
"""

from data.database import Database
from services.event_service import EventService

def test_participant_limit_change():
    """Тестируем изменение лимита участников"""
    print("🧪 Тестирование изменения лимита участников\n")
    
    # Инициализируем сервисы
    db = Database()
    event_service = EventService(db)
    
    # Получаем активные события
    active_events = event_service.get_active_events()
    
    if not active_events:
        print("❌ Нет активных событий для тестирования")
        return
    
    # Берем первое активное событие
    event = active_events[0]
    event_id = event['id']
    current_limit = event['max_participants']
    
    print(f"📅 Событие: {event['name']}")
    print(f"🆔 ID события: {event_id}")
    print(f"👥 Текущий лимит: {current_limit}")
    
    # Получаем участников
    participants = event_service.get_participants_list(event_id, event)
    print(f"\n📋 Текущие участники:\n{participants}")
    
    # Тестируем увеличение лимита
    new_limit = current_limit + 2
    print(f"\n🔄 Тестируем увеличение лимита с {current_limit} до {new_limit}")
    
    result = event_service.change_participant_limit(event_id, new_limit)
    
    if result['success']:
        print("✅ Лимит успешно изменен!")
        print(f"📊 Перемещено в основной состав: {len(result['moved_to_main'])}")
        print(f"📊 Перемещено в резерв: {len(result['moved_to_reserve'])}")
        
        if result['moved_to_main']:
            print("\n🎉 Переведены в основной состав:")
            for participant in result['moved_to_main']:
                print(f"  • {participant['display_name']}")
        
        if result['moved_to_reserve']:
            print("\n⚠️ Переведены в резерв:")
            for participant in result['moved_to_reserve']:
                print(f"  • {participant['display_name']}")
        
        # Показываем обновленный список
        updated_participants = event_service.get_participants_list(event_id, event)
        print(f"\n📋 Обновленный список участников:\n{updated_participants}")
        
        # Возвращаем лимит обратно
        print(f"\n🔄 Возвращаем лимит обратно с {new_limit} до {current_limit}")
        result_back = event_service.change_participant_limit(event_id, current_limit)
        
        if result_back['success']:
            print("✅ Лимит успешно возвращен!")
            final_participants = event_service.get_participants_list(event_id, event)
            print(f"\n📋 Финальный список участников:\n{final_participants}")
        else:
            print(f"❌ Ошибка при возврате лимита: {result_back['message']}")
    
    else:
        print(f"❌ Ошибка при изменении лимита: {result['message']}")
    
    print("\n✅ Тестирование завершено!")

if __name__ == "__main__":
    test_participant_limit_change() 