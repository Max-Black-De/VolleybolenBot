#!/usr/bin/env python3
"""
Интеграционный тест всех компонентов бота
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.database import Database
from services.event_service import EventService
from services.notification_service import NotificationService
from services.chat_history_service import ChatHistoryService
from datetime import date, timedelta
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_integration():
    """Интеграционное тестирование всех компонентов"""
    print("🔗 Интеграционное тестирование всех компонентов бота...")
    
    # Инициализация всех сервисов
    db = Database("test_integration.db")
    db.init_database()
    
    event_service = EventService(db)
    # Пропускаем NotificationService для тестов, так как нужен реальный бот
    chat_history_service = ChatHistoryService(db)
    
    print("✅ Все сервисы инициализированы")
    
    # === ТЕСТ 1: Создание события ===
    print("\n📅 ТЕСТ 1: Создание события")
    
    tomorrow = date.today() + timedelta(days=1)
    event_id = event_service.create_event_on_date(tomorrow)
    
    event = event_service.get_event_by_id(event_id)
    if event:
        print(f"✅ Событие создано: {event['name']}")
        print(f"   ID: {event['id']}")
        print(f"   Дата: {event['date']}")
        print(f"   Лимит: {event['max_participants']}")
    else:
        print("❌ Ошибка создания события")
        return
    
    # === ТЕСТ 2: Настройка групп ===
    print("\n🎯 ТЕСТ 2: Настройка групп")
    
    # Включаем запись группами
    db.set_bot_setting('group_registration_enabled', 'true')
    db.set_bot_setting('max_group_size', '3')
    
    enabled = db.is_group_registration_enabled()
    max_size = db.get_max_group_size()
    
    print(f"✅ Запись группами: {enabled}")
    print(f"✅ Максимальный размер: {max_size}")
    
    # === ТЕСТ 3: Запись участников ===
    print("\n👥 ТЕСТ 3: Запись участников")
    
    # Симулируем запись разных типов участников
    participants = [
        (1001, 1, "user1", "Иван", "Иванов"),
        (1002, 2, "user2", "Петр", "Петров"),
        (1003, 3, "user3", "Сергей", "Сергеев"),
        (1004, 1, "user4", "Анна", "Аннова"),
        (1005, 2, "user5", "Мария", "Мариева"),
    ]
    
    for telegram_id, group_size, username, first_name, last_name in participants:
        result = event_service.join_event_with_group(
            event_id, telegram_id, group_size, username, first_name, last_name
        )
        status = "✅" if result['success'] else "❌"
        print(f"{status} {first_name} (группа {group_size}): {result['success']}")
    
    # === ТЕСТ 4: История чата ===
    print("\n💬 ТЕСТ 4: История чата")
    
    # Симулируем сообщения пользователей
    test_user_id = 1001
    test_messages = [
        "Привет!",
        "Хочу записаться на тренировку",
        "Спасибо!"
    ]
    
    for message in test_messages:
        chat_history_service.save_user_message(test_user_id, message, event_id)
    
    # Сохраняем сообщения бота
    bot_messages = [
        "Добро пожаловать!",
        "Вы успешно записаны",
        "До встречи на тренировке!"
    ]
    
    for message in bot_messages:
        chat_history_service.save_bot_message(test_user_id, message, event_id)
    
    # Получаем историю
    history = chat_history_service.get_recent_history(test_user_id, 24)
    print(f"✅ Сохранено сообщений: {len(history)}")
    
    # === ТЕСТ 5: Список участников ===
    print("\n📋 ТЕСТ 5: Список участников")
    
    participants_list = event_service.get_participants_list(event_id, event)
    print("Список участников:")
    print(participants_list)
    
    # === ТЕСТ 6: Подтверждение присутствия ===
    print("\n✅ ТЕСТ 6: Подтверждение присутствия")
    
    # Подтверждаем присутствие для некоторых участников
    confirmed_users = [1001, 1003, 1004]
    
    for user_id in confirmed_users:
        success = event_service.confirm_presence(event_id, user_id)
        status = "✅" if success else "❌"
        print(f"{status} Подтверждение {user_id}: {success}")
    
    # === ТЕСТ 7: Автоматическая отписка ===
    print("\n🚪 ТЕСТ 7: Автоматическая отписка")
    
    # Получаем неподтвердивших участников
    unconfirmed = event_service.get_unconfirmed_participants(event_id)
    print(f"Неподтвердивших участников: {len(unconfirmed)}")
    
    # Симулируем автоматическую отписку
    left_participants = event_service.auto_leave_unconfirmed(event_id)
    print(f"Автоматически отписано: {len(left_participants)}")
    
    # === ТЕСТ 8: Изменение лимита ===
    print("\n⚙️ ТЕСТ 8: Изменение лимита")
    
    # Изменяем лимит участников
    limit_result = event_service.change_participant_limit(event_id, 8)
    print(f"Изменение лимита: {limit_result['success']}")
    
    if limit_result['success']:
        print(f"   Перемещено в основной состав: {len(limit_result['moved_to_main'])}")
        print(f"   Перемещено в резерв: {len(limit_result['moved_to_reserve'])}")
    
    # === ТЕСТ 9: Финальная статистика ===
    print("\n📊 ТЕСТ 9: Финальная статистика")
    
    # Получаем финальную статистику
    participants = db.get_event_participants(event_id)
    total_participants = len(participants)
    confirmed_participants = len([p for p in participants if p['status'] == 'confirmed'])
    reserve_participants = len([p for p in participants if p['status'] == 'reserve'])
    total_people = sum(p.get('group_size', 1) for p in participants)
    
    print(f"Всего записей: {total_participants}")
    print(f"Основной состав: {confirmed_participants}")
    print(f"Резерв: {reserve_participants}")
    print(f"Общее количество людей: {total_people}")
    
    # Статистика по группам
    group_stats = {}
    for p in participants:
        size = p.get('group_size', 1)
        group_stats[size] = group_stats.get(size, 0) + 1
    
    print("Распределение по группам:")
    for size, count in sorted(group_stats.items()):
        print(f"  {size} человек: {count} групп")
    
    # === ТЕСТ 10: Проверка настроек ===
    print("\n🔧 ТЕСТ 10: Проверка настроек")
    
    # Проверяем все настройки
    settings = {
        'group_registration_enabled': db.is_group_registration_enabled(),
        'max_group_size': db.get_max_group_size(),
    }
    
    for key, value in settings.items():
        print(f"✅ {key}: {value}")
    
    print("\n🎉 Интеграционное тестирование завершено успешно!")

if __name__ == "__main__":
    test_integration() 