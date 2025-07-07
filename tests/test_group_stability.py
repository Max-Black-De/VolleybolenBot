#!/usr/bin/env python3
"""
Тест для проверки стабильности групповой записи
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
import tempfile
from datetime import date, timedelta
from data.database import Database
from services.event_service import EventService
from services.notification_service import NotificationService
from unittest.mock import Mock

class TestGroupStability(unittest.TestCase):
    def setUp(self):
        """Настройка тестовой базы данных"""
        self.temp_db_file = tempfile.NamedTemporaryFile(delete=False)
        self.db = Database(self.temp_db_file.name)
        self.event_service = EventService(self.db)
        self.notification_service = Mock(spec=NotificationService)

        # --- Миграция: добавляем недостающие столбцы, если их нет ---
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('ALTER TABLE participants ADD COLUMN main_group_size INTEGER DEFAULT 1')
            except Exception:
                pass
            try:
                cursor.execute('ALTER TABLE participants ADD COLUMN reserve_group_size INTEGER DEFAULT 0')
            except Exception:
                pass
            conn.commit()

        # Создаем тестовое событие с лимитом 6 человек
        target_date = date.today() + timedelta(days=1)
        self.event_id = self.db.create_event(
            name=f"Тестовая тренировка {target_date}",
            event_date=target_date,
            event_time="19:00",
            max_participants=6
        )
        
        # Включаем групповую запись
        self.db.set_bot_setting('group_registration_enabled', 'true')
        self.db.set_bot_setting('max_group_size', '3')
        
        # Добавляем тестовых пользователей
        self.users = []
        for i in range(10):
            user_id = self.db.add_user(1000 + i, f"user{i}", f"User{i}", f"Last{i}")
            self.users.append(1000 + i)

    def tearDown(self):
        """Очистка после тестов"""
        if hasattr(self, 'temp_db_file'):
            self.temp_db_file.close()
            os.unlink(self.temp_db_file.name)

    def test_group_registration_stability(self):
        """Тест стабильности групповой записи"""
        print("\n=== Тест стабильности групповой записи ===")
        
        # 1. Добавляем группу из 3 человек
        result1 = self.event_service.join_event_with_group(
            self.event_id, 1001, 3, "user1", "User1", "Last1"
        )
        print(f"Добавлена группа 3 чел.: {result1['message']}")
        self.assertTrue(result1['success'])
        
        # 2. Добавляем группу из 2 человек
        result2 = self.event_service.join_event_with_group(
            self.event_id, 1002, 2, "user2", "User2", "Last2"
        )
        print(f"Добавлена группа 2 чел.: {result2['message']}")
        self.assertTrue(result2['success'])
        
        # 3. Добавляем одиночного участника
        result3 = self.event_service.join_event_with_group(
            self.event_id, 1003, 1, "user3", "User3", "Last3"
        )
        print(f"Добавлен одиночный участник: {result3['message']}")
        self.assertTrue(result3['success'])
        
        # 4. Проверяем список участников
        participants = self.db.get_event_participants(self.event_id)
        print(f"\nУчастников в событии: {len(participants)}")
        
        # Проверяем, что лимит не превышен
        confirmed_count = sum(p.get('group_size', 1) for p in participants if p['status'] == 'confirmed')
        mixed_count = sum(p.get('main_group_size', 0) or 0 for p in participants if p['status'] == 'mixed')
        total_main = confirmed_count + mixed_count
        
        print(f"Людей в основном составе: {total_main}/6")
        self.assertLessEqual(total_main, 6, "Лимит основного состава превышен!")
        
        # 5. Проверяем, что mixed-группа корректно разделена
        mixed_group = None
        for p in participants:
            if p['status'] == 'mixed':
                mixed_group = p
                break
        
        if mixed_group:
            main_size = mixed_group.get('main_group_size', 0) or 0
            reserve_size = mixed_group.get('reserve_group_size', 0) or 0
            group_size = mixed_group.get('group_size', 1)
            
            print(f"Mixed-группа: {main_size} осн. + {reserve_size} рез. = {group_size} всего")
            self.assertEqual(main_size + reserve_size, group_size, "Неправильное разделение mixed-группы")
            self.assertGreater(main_size, 0, "Mixed-группа должна иметь людей в основном составе")
            self.assertGreater(reserve_size, 0, "Mixed-группа должна иметь людей в резерве")

    def test_group_partial_leave_stability(self):
        """Тест стабильности частичной отписки группы"""
        print("\n=== Тест частичной отписки группы ===")
        
        # 1. Добавляем группу из 3 человек
        result = self.event_service.join_event_with_group(
            self.event_id, 1001, 3, "user1", "User1", "Last1"
        )
        print(f"Добавлена группа 3 чел.: {result['message']}")
        
        # 2. Частично отписываем 1 человека
        leave_result = self.event_service.reduce_group_size(self.event_id, 1001, 1)
        print(f"Отписано 1 чел.: {leave_result['message']}")
        self.assertTrue(leave_result['success'])
        
        # 3. Проверяем, что группа стала из 2 человек
        participant = self.db.get_participant(self.event_id, 1001)
        self.assertIsNotNone(participant)
        if participant:
            self.assertEqual(participant.get('group_size', 1), 2, "Размер группы должен быть 2")
        
        # 4. Проверяем, что лимит не превышен
        participants = self.db.get_event_participants(self.event_id)
        confirmed_count = sum(p.get('group_size', 1) for p in participants if p['status'] == 'confirmed')
        mixed_count = sum(p.get('main_group_size', 0) or 0 for p in participants if p['status'] == 'mixed')
        total_main = confirmed_count + mixed_count
        
        print(f"После отписки в основном составе: {total_main}/6")
        self.assertLessEqual(total_main, 6, "Лимит превышен после частичной отписки!")

    def test_mixed_group_overflow_fix(self):
        """Тест исправления бага с превышением лимита mixed-группами"""
        print("\n=== Тест исправления бага с превышением лимита ===")
        
        # 1. Добавляем группу из 4 человек (mixed: 3+1)
        result1 = self.event_service.join_event_with_group(
            self.event_id, 1001, 4, "user1", "User1", "Last1"
        )
        print(f"Добавлена группа 4 чел.: {result1['message']}")
        
        # 2. Добавляем группу из 3 человек (mixed: 2+1)
        result2 = self.event_service.join_event_with_group(
            self.event_id, 1002, 3, "user2", "User2", "Last2"
        )
        print(f"Добавлена группа 3 чел.: {result2['message']}")
        
        # 3. Проверяем, что лимит не превышен
        participants = self.db.get_event_participants(self.event_id)
        confirmed_count = sum(p.get('group_size', 1) for p in participants if p['status'] == 'confirmed')
        mixed_count = sum(p.get('main_group_size', 0) or 0 for p in participants if p['status'] == 'mixed')
        total_main = confirmed_count + mixed_count
        
        print(f"Всего в основном составе: {total_main}/6")
        self.assertLessEqual(total_main, 6, "Лимит превышен!")
        
        # 4. Проверяем, что есть mixed-группы
        mixed_groups = [p for p in participants if p['status'] == 'mixed']
        self.assertGreater(len(mixed_groups), 0, "Должны быть mixed-группы")

if __name__ == '__main__':
    unittest.main() 