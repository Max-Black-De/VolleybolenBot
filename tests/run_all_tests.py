#!/usr/bin/env python3
"""
Запуск всех тестов бота
"""

import sys
import os
import subprocess
import time

def run_test(test_file):
    """Запустить тест и вернуть результат"""
    print(f"\n{'='*60}")
    print(f"🧪 Запуск теста: {test_file}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(
            [sys.executable, test_file],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("✅ Тест прошел успешно!")
            print(result.stdout)
            return True
        else:
            print("❌ Тест завершился с ошибкой!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ Тест превысил время выполнения (30 сек)")
        return False
    except Exception as e:
        print(f"❌ Ошибка запуска теста: {e}")
        return False

def main():
    """Запустить все тесты"""
    print("🚀 Запуск всех тестов Volleyball Training Bot")
    print(f"Время запуска: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Список тестов для запуска
    tests = [
        "tests/test_group_registration.py",
        "tests/test_comprehensive_groups.py", 
        "tests/test_admin_group_functions.py",
        "tests/test_integration.py"
    ]
    
    # Проверяем существование файлов
    existing_tests = []
    for test in tests:
        if os.path.exists(test):
            existing_tests.append(test)
        else:
            print(f"⚠️ Тест не найден: {test}")
    
    if not existing_tests:
        print("❌ Не найдено ни одного теста для запуска!")
        return
    
    print(f"\n📋 Найдено тестов: {len(existing_tests)}")
    
    # Запускаем тесты
    passed = 0
    failed = 0
    
    for test in existing_tests:
        if run_test(test):
            passed += 1
        else:
            failed += 1
    
    # Итоговая статистика
    print(f"\n{'='*60}")
    print("📊 ИТОГОВАЯ СТАТИСТИКА")
    print(f"{'='*60}")
    print(f"✅ Успешно: {passed}")
    print(f"❌ Провалено: {failed}")
    print(f"📈 Всего: {passed + failed}")
    
    if failed == 0:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
        print("🚀 Бот готов к использованию!")
    else:
        print(f"\n⚠️ {failed} тест(ов) провалено. Проверьте логи выше.")
    
    print(f"\nВремя завершения: {time.strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main() 