#!/usr/bin/env python3
"""
Тест админских функций управления группами
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

def test_admin_group_functions():
    """Тестирование админских функций управления группами"""
    print("👨‍💼 Тестирование админских функций управления группами...")
    
    # Инициализация базы данных
    db = Database("test_admin.db")
    db.init_database()
    
    # Создаем тестовое событие
    event_service = EventService(db)
    tomorrow = date.today() + timedelta(days=1)
    event_id = event_service.create_event_on_date(tomorrow)
    
    print(f"✅ Создано тестовое событие с ID: {event_id}")
    
    # === ТЕСТ 1: Проверка настроек по умолчанию ===
    print("\n🔧 ТЕСТ 1: Проверка настроек по умолчанию")
    
    default_enabled = db.is_group_registration_enabled()
    default_size = db.get_max_group_size()
    
    print(f"Запись группами по умолчанию: {default_enabled}")
    print(f"Максимальный размер группы по умолчанию: {default_size}")
    
    # === ТЕСТ 2: Включение записи группами ===
    print("\n✅ ТЕСТ 2: Включение записи группами")
    
    db.set_bot_setting('group_registration_enabled', 'true')
    enabled = db.is_group_registration_enabled()
    print(f"Запись группами включена: {enabled}")
    
    # === ТЕСТ 3: Изменение размера группы ===
    print("\n👥 ТЕСТ 3: Изменение размера группы")
    
    # Тестируем разные размеры
    test_sizes = [1, 2, 3, 4, 5]
    
    for size in test_sizes:
        db.set_bot_setting('max_group_size', str(size))
        current_size = db.get_max_group_size()
        print(f"Установлен размер {size}: {current_size == size}")
    
    # === ТЕСТ 4: Тестирование записи с разными размерами ===
    print("\n📝 ТЕСТ 4: Тестирование записи с разными размерами")
    
    # Устанавливаем размер группы 3
    db.set_bot_setting('max_group_size', '3')
    
    # Записываем участников с разными размерами групп
    results = []
    
    # Группа из 1 человека
    result1 = event_service.join_event_with_group(event_id, 2001, 1, "admin1", "Админ1", "Админов1")
    results.append(("Группа 1 чел", result1['success']))
    
    # Группа из 2 человек
    result2 = event_service.join_event_with_group(event_id, 2002, 2, "admin2", "Админ2", "Админов2")
    results.append(("Группа 2 чел", result2['success']))
    
    # Группа из 3 человек
    result3 = event_service.join_event_with_group(event_id, 2003, 3, "admin3", "Админ3", "Админов3")
    results.append(("Группа 3 чел", result3['success']))
    
    # Пытаемся записать группу из 4 человек (больше лимита)
    result4 = event_service.join_event_with_group(event_id, 2004, 4, "admin4", "Админ4", "Админов4")
    results.append(("Группа 4 чел (превышение)", not result4['success']))
    
    # Выводим результаты
    for test_name, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {test_name}: {success}")
    
    # Показываем список участников
    print("\n👥 Список участников:")
    participants_list = event_service.get_participants_list(event_id)
    print(participants_list)
    
    # === ТЕСТ 5: Отключение записи группами ===
    print("\n❌ ТЕСТ 5: Отключение записи группами")
    
    db.set_bot_setting('group_registration_enabled', 'false')
    disabled = db.is_group_registration_enabled()
    print(f"Запись группами отключена: {disabled}")
    
    # === ТЕСТ 6: Проверка сохранения настроек ===
    print("\n💾 ТЕСТ 6: Проверка сохранения настроек")
    
    # Создаем новое подключение к базе
    db2 = Database("test_admin.db")
    
    # Проверяем, что настройки сохранились
    saved_enabled = db2.is_group_registration_enabled()
    saved_size = db2.get_max_group_size()
    
    print(f"Сохранено - группы отключены: {saved_enabled == False}")
    print(f"Сохранено - размер группы: {saved_size == 3}")
    
    # === ТЕСТ 7: Изменение лимита участников ===
    print("\n⚙️ ТЕСТ 7: Изменение лимита участников")
    
    # Получаем текущий лимит
    event = event_service.get_event_by_id(event_id)
    if event:
        current_limit = event['max_participants']
        print(f"Текущий лимит: {current_limit}")
        
        # Изменяем лимит
        limit_result = event_service.change_participant_limit(event_id, 12)
        print(f"Изменение лимита на 12: {limit_result['success']}")
        
        # Проверяем новый лимит
        event_updated = event_service.get_event_by_id(event_id)
        if event_updated:
            new_limit = event_updated['max_participants']
            print(f"Новый лимит: {new_limit}")
        else:
            print("❌ Не удалось получить обновленное событие")
    else:
        print("❌ Не удалось получить событие")
    
    # === ТЕСТ 8: Статистика админских функций ===
    print("\n📊 ТЕСТ 8: Статистика админских функций")
    
    participants = db.get_event_participants(event_id)
    total_participants = len(participants)
    total_people = sum(p.get('group_size', 1) for p in participants)
    
    print(f"Всего записей: {total_participants}")
    print(f"Общее количество людей: {total_people}")
    print(f"Средний размер группы: {total_people / total_participants:.1f}")
    
    # Группы по размерам
    group_sizes = {}
    for p in participants:
        size = p.get('group_size', 1)
        group_sizes[size] = group_sizes.get(size, 0) + 1
    
    print("Распределение по размерам групп:")
    for size, count in sorted(group_sizes.items()):
        print(f"  {size} человек: {count} групп")
    
    print("\n✅ Тестирование админских функций завершено!")

if __name__ == "__main__":
    test_admin_group_functions() 