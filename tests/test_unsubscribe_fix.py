#!/usr/bin/env python3
"""
Тестовый скрипт для проверки новой логики отписки
"""

from config.settings import MESSAGES
from utils.keyboard import create_leave_confirmation_keyboard

def test_unsubscribe_flow():
    """Тестируем новый процесс отписки"""
    print("🧪 Тестирование новой логики отписки\n")
    
    # Тестируем сообщение подтверждения
    print("📝 Сообщение подтверждения:")
    print(f"'{MESSAGES['leave_confirmation']}'")
    print()
    
    # Тестируем клавиатуру подтверждения
    print("⌨️ Кнопки подтверждения:")
    keyboard = create_leave_confirmation_keyboard(event_id=1, telegram_id=12345)
    
    for row in keyboard.inline_keyboard:
        for button in row:
            print(f"  - {button.text} (callback: {button.callback_data})")
    
    print()
    
    # Тестируем callback данные
    print("🔗 Разбор callback данных:")
    callback_data = "confirm_leave_1_12345"
    parts = callback_data.split('_')
    print(f"callback_data: {callback_data}")
    print(f"action: {parts[0]}")
    print(f"event_id: {parts[2]}")
    print(f"telegram_id: {parts[3]}")
    
    print()
    print("✅ Тестирование завершено!")

if __name__ == "__main__":
    test_unsubscribe_flow() 