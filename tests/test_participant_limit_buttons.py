#!/usr/bin/env python3
"""
Тестовый скрипт для проверки фиксированных кнопок изменения лимита участников
"""

from utils.keyboard import create_participant_limit_keyboard

def test_participant_limit_buttons():
    """Тестируем кнопки изменения лимита участников"""
    print("🧪 Тестирование фиксированных кнопок изменения лимита участников\n")
    
    # Создаем клавиатуру
    keyboard = create_participant_limit_keyboard()
    
    print("⌨️ Кнопки выбора лимита участников:")
    for row in keyboard.keyboard:
        for button in row:
            print(f"  - {button}")
    
    print()
    
    # Тестируем парсинг кнопок
    print("🔍 Тестирование парсинга кнопок:")
    test_buttons = [
        "👥 4 участника",
        "👥 6 участников",
        "👥 12 участников",
        "👥 18 участников", 
        "👥 24 участника",
        "🔙 Назад",
        "Неверная кнопка"
    ]
    
    for button_text in test_buttons:
        new_limit = None
        if button_text == "👥 4 участника":
            new_limit = 4
        elif button_text == "👥 6 участников":
            new_limit = 6
        elif button_text == "👥 12 участников":
            new_limit = 12
        elif button_text == "👥 18 участников":
            new_limit = 18
        elif button_text == "👥 24 участника":
            new_limit = 24
        
        if new_limit:
            print(f"  ✅ '{button_text}' → лимит {new_limit}")
        else:
            print(f"  ❌ '{button_text}' → не распознано")
    
    print()
    print("✅ Тестирование завершено!")

if __name__ == "__main__":
    test_participant_limit_buttons() 