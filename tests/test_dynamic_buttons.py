#!/usr/bin/env python3
"""
Тест динамических кнопок записи и отписки
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.database import Database
from utils.keyboard import create_group_size_keyboard, create_partial_leave_keyboard

def test_dynamic_buttons():
    """Тестирование динамических кнопок"""
    print("🧪 Тестирование динамических кнопок")
    
    # Тестируем кнопки записи
    print("\n📝 ТЕСТ 1: Кнопки записи")
    
    # max_group_size = 2
    keyboard_2 = create_group_size_keyboard(2)
    print(f"max_group_size = 2: {len(keyboard_2.keyboard)} строк")
    for i, row in enumerate(keyboard_2.keyboard):
        print(f"  Строка {i+1}: {[btn.text for btn in row]}")
    
    # max_group_size = 3
    keyboard_3 = create_group_size_keyboard(3)
    print(f"\nmax_group_size = 3: {len(keyboard_3.keyboard)} строк")
    for i, row in enumerate(keyboard_3.keyboard):
        print(f"  Строка {i+1}: {[btn.text for btn in row]}")
    
    # max_group_size = 4
    keyboard_4 = create_group_size_keyboard(4)
    print(f"\nmax_group_size = 4: {len(keyboard_4.keyboard)} строк")
    for i, row in enumerate(keyboard_4.keyboard):
        print(f"  Строка {i+1}: {[btn.text for btn in row]}")
    
    # Тестируем кнопки отписки
    print("\n📤 ТЕСТ 2: Кнопки отписки")
    
    # Группа из 2 человек, max_group_size = 2
    leave_keyboard_2_2 = create_partial_leave_keyboard(2, 2)
    print(f"Группа из 2 чел, max_group_size = 2: {len(leave_keyboard_2_2.inline_keyboard)} строк")
    for i, row in enumerate(leave_keyboard_2_2.inline_keyboard):
        print(f"  Строка {i+1}: {[btn.text for btn in row]}")
    
    # Группа из 3 человек, max_group_size = 2
    leave_keyboard_3_2 = create_partial_leave_keyboard(3, 2)
    print(f"\nГруппа из 3 чел, max_group_size = 2: {len(leave_keyboard_3_2.inline_keyboard)} строк")
    for i, row in enumerate(leave_keyboard_3_2.inline_keyboard):
        print(f"  Строка {i+1}: {[btn.text for btn in row]}")
    
    # Группа из 3 человек, max_group_size = 3
    leave_keyboard_3_3 = create_partial_leave_keyboard(3, 3)
    print(f"\nГруппа из 3 чел, max_group_size = 3: {len(leave_keyboard_3_3.inline_keyboard)} строк")
    for i, row in enumerate(leave_keyboard_3_3.inline_keyboard):
        print(f"  Строка {i+1}: {[btn.text for btn in row]}")
    
    print("\n✅ Тестирование завершено!")

if __name__ == "__main__":
    test_dynamic_buttons() 