#!/usr/bin/env python3
"""
Тестовый скрипт для проверки исправления подтверждения присутствия
"""

from config.settings import MESSAGES
from utils.keyboard import create_presence_confirmation_keyboard

def test_presence_confirmation_flow():
    """Тестируем процесс подтверждения присутствия"""
    print("🧪 Тестирование подтверждения присутствия\n")
    
    # Тестируем сообщения напоминаний
    print("📝 Сообщения напоминаний:")
    print(f"Первое напоминание: '{MESSAGES['presence_reminder']}'")
    print(f"Второе напоминание: '{MESSAGES['second_reminder']}'")
    print()
    
    # Тестируем клавиатуру подтверждения присутствия
    print("⌨️ Кнопки подтверждения присутствия:")
    keyboard = create_presence_confirmation_keyboard(event_id=1, telegram_id=12345)
    
    for row in keyboard.inline_keyboard:
        for button in row:
            print(f"  - {button.text} (callback: {button.callback_data})")
    
    print()
    
    # Тестируем callback данные для подтверждения присутствия
    print("🔗 Разбор callback данных для присутствия:")
    confirm_callback = "confirm_presence_1_12345"
    decline_callback = "decline_presence_1_12345"
    
    confirm_parts = confirm_callback.split('_')
    decline_parts = decline_callback.split('_')
    
    print(f"confirm_presence callback: {confirm_callback}")
    print(f"  action: {confirm_parts[0]}_{confirm_parts[1]}")
    print(f"  event_id: {confirm_parts[2]}")
    print(f"  telegram_id: {confirm_parts[3]}")
    
    print(f"decline_presence callback: {decline_callback}")
    print(f"  action: {decline_parts[0]}_{decline_parts[1]}")
    print(f"  event_id: {decline_parts[2]}")
    print(f"  telegram_id: {decline_parts[3]}")
    
    print()
    print("✅ Тестирование завершено!")

if __name__ == "__main__":
    test_presence_confirmation_flow() 