#!/usr/bin/env python3
"""
Тестовый скрипт для проверки исправлений часовых поясов
"""

import pytz
from datetime import datetime, date, time
from config.settings import BOT_SETTINGS

def test_timezone_settings():
    """Тестируем настройки часового пояса"""
    print("🔧 Тестирование настроек часового пояса:")
    print(f"Часовой пояс: {BOT_SETTINGS['TIMEZONE']}")
    print(f"Название часового пояса: {BOT_SETTINGS['TIMEZONE_NAME']}")
    
    # Создаем объект часового пояса
    timezone = pytz.timezone(BOT_SETTINGS['TIMEZONE_NAME'])
    
    # Текущее время в UTC
    utc_now = datetime.now(pytz.UTC)
    print(f"Текущее время UTC: {utc_now}")
    
    # Текущее время в целевом часовом поясе
    local_now = utc_now.astimezone(timezone)
    print(f"Текущее время в {BOT_SETTINGS['TIMEZONE_NAME']}: {local_now}")
    
    # Проверяем разницу (используем naive datetime)
    naive_now = datetime.now()
    offset = timezone.utcoffset(naive_now)
    print(f"Смещение от UTC: {offset}")
    
    print()

def test_event_scheduling():
    """Тестируем планирование событий"""
    print("📅 Тестирование планирования событий:")
    
    # Пример: тренировка 26.06.2025 в 20:00
    training_date = date(2025, 6, 26)  # Четверг
    training_time = time(20, 0)  # 20:00
    
    print(f"Дата тренировки: {training_date}")
    print(f"Время тренировки: {training_time}")
    
    # Время создания события (за день до тренировки в 17:00)
    event_creation_date = date(2025, 6, 25)  # Среда
    event_creation_time = time(17, 0)  # 17:00
    
    print(f"Дата создания события: {event_creation_date}")
    print(f"Время создания события: {event_creation_time}")
    
    # Время напоминания (за 2 часа до тренировки)
    reminder_time = time(18, 0)  # 18:00
    print(f"Время напоминания: {reminder_time}")
    
    # Время очистки события (после тренировки)
    cleanup_time = time(22, 0)  # 22:00
    print(f"Время очистки события: {cleanup_time}")
    
    print()

def test_next_training_day():
    """Тестируем определение следующего тренировочного дня"""
    print("🏐 Тестирование определения следующего тренировочного дня:")
    
    # Имитируем логику из EventService
    def get_next_training_day(today: date) -> date:
        from datetime import timedelta
        weekday = today.weekday()
        if weekday < 3:  # До четверга
            delta_days = 3 - weekday
        elif weekday < 6:  # До воскресенья
            delta_days = 6 - weekday
        else:  # Воскресенье или позже
            delta_days = 4  # До следующего четверга
        return today + timedelta(days=delta_days)
    
    # Тестируем для разных дней недели
    test_dates = [
        date(2025, 6, 23),  # Понедельник
        date(2025, 6, 24),  # Вторник
        date(2025, 6, 25),  # Среда
        date(2025, 6, 26),  # Четверг
        date(2025, 6, 27),  # Пятница
        date(2025, 6, 28),  # Суббота
        date(2025, 6, 29),  # Воскресенье
    ]
    
    weekday_names = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    
    for test_date in test_dates:
        next_day = get_next_training_day(test_date)
        print(f"{test_date} ({weekday_names[test_date.weekday()]}) -> {next_day} ({weekday_names[next_day.weekday()]})")

if __name__ == "__main__":
    print("🧪 Тестирование исправлений часовых поясов\n")
    
    test_timezone_settings()
    test_event_scheduling()
    test_next_training_day()
    
    print("\n✅ Тестирование завершено!") 