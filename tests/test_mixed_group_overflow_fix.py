#!/usr/bin/env python3
"""
Тест для проверки исправления бага с превышением лимита при mixed-группах
"""

import sys
import os
import tempfile
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from datetime import date, timedelta
from data.database import Database
from services.event_service import EventService
from services.notification_service import NotificationService
from unittest.mock import Mock

class TestMixedGroupOverflowFix(unittest.TestCase):
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
        # --- конец миграции ---
        
        # Создаем тестовое событие напрямую в базе
        target_date = date.today() + timedelta(days=1)
        self.event_id = self.db.create_event(
            name=f"Тестовая тренировка {target_date}",
            event_date=target_date,
            event_time="19:00",
            max_participants=6
        )
        
        # Добавляем тестовых пользователей
        self.users = []
        for i in range(10):
            user_id = self.db.add_user(1000 + i, f"user{i}", f"User{i}", f"Last{i}")
            self.users.append(1000 + i)
    
    def tearDown(self):
        self.temp_db_file.close()
        os.unlink(self.temp_db_file.name)

    def test_mixed_group_overflow_scenario(self):
        """Тест сценария, когда mixed-группа превышает лимит"""
        print("\n=== Тест сценария превышения лимита mixed-группами ===")
        
        # 1. Добавляем группу из 3 человек (все в основном составе)
        result1 = self.event_service.join_event_with_group(
            self.event_id, self.users[0], 3, "user0", "User0", "Last0"
        )
        print(f"Добавлена группа 1: {result1}")
        self.assertTrue(result1['success'])
        self.assertEqual(result1['status'], 'confirmed')
        
        # 2. Добавляем группу из 4 человек (3 в основном, 1 в резерве - mixed)
        result2 = self.event_service.join_event_with_group(
            self.event_id, self.users[1], 4, "user1", "User1", "Last1"
        )
        print(f"Добавлена группа 2: {result2}")
        self.assertTrue(result2['success'])
        self.assertEqual(result2['status'], 'mixed')
        self.assertEqual(result2['main_group_size'], 3)
        self.assertEqual(result2['reserve_group_size'], 1)
        
        # 3. Проверяем текущий состав
        participants = self.db.get_event_participants(self.event_id)
        confirmed_count = sum(p.get('main_group_size', 0) or 0 for p in participants if p['status'] in ['confirmed', 'mixed'])
        print(f"Людей в основном составе: {confirmed_count}/6")
        self.assertEqual(confirmed_count, 6)  # 3 + 3 = 6
        
        # 4. Добавляем еще одного человека (должен попасть в резерв)
        result3 = self.event_service.join_event(
            self.event_id, self.users[2], "user2", "User2", "Last2"
        )
        print(f"Добавлен одиночный участник: {result3}")
        self.assertTrue(result3['success'])
        self.assertEqual(result3['status'], 'reserve')
        
        # 5. Теперь отписываем одного человека из первой группы
        result4 = self.event_service.reduce_group_size(self.event_id, self.users[0], 1)
        print(f"Отписан 1 человек из группы 1: {result4}")
        self.assertTrue(result4['success'])
        
        # 6. Проверяем, что mixed-группа корректно перераспределилась
        participants = self.db.get_event_participants(self.event_id)
        
        # Находим mixed-группу (или бывшую mixed-группу, которая стала confirmed)
        mixed_group = None
        confirmed_group = None
        for p in participants:
            if p['status'] == 'mixed':
                mixed_group = p
                break
            elif p['status'] == 'confirmed' and p.get('group_size', 1) > 1:
                # Это может быть бывшая mixed-группа, которая стала confirmed
                confirmed_group = p
        
        # После отписки 1 человека из группы 3, группа становится из 2 человек
        # и вся помещается в основной состав (статус меняется с mixed на confirmed)
        if mixed_group is None and confirmed_group is not None:
            # Mixed-группа стала confirmed - это правильно
            main_size = confirmed_group.get('main_group_size', 0) if confirmed_group else 0
            reserve_size = confirmed_group.get('reserve_group_size', 0) if confirmed_group else 0
            print(f"Бывшая mixed-группа стала confirmed: {main_size} осн., {reserve_size} рез.")
            
            # После отписки 1 человека из первой группы (3→2), освободилось место
            # и mixed-группа теперь может поместить всех 4 человек в основной состав
            self.assertEqual(main_size, 4)  # Вся бывшая mixed-группа теперь в основном
            self.assertEqual(reserve_size, 0)
        else:
            # Если mixed-группа осталась, проверяем её размеры
            main_size = mixed_group.get('main_group_size', 0) if mixed_group else 0
            reserve_size = mixed_group.get('reserve_group_size', 0) if mixed_group else 0
            print(f"Mixed-группа после перераспределения: {main_size} осн., {reserve_size} рез.")
            
            # Должно быть 4 в основном (3 из mixed + 1 из одиночного), 0 в резерве
            self.assertEqual(main_size, 4)
            self.assertEqual(reserve_size, 0)
        
        # Проверяем общее количество людей в основном составе
        confirmed_count = sum(p.get('main_group_size', 0) or 0 for p in participants if p['status'] in ['confirmed', 'mixed'])
        print(f"Итоговое количество в основном составе: {confirmed_count}/6")
        self.assertEqual(confirmed_count, 6)  # Не должно превышать лимит
    
    def test_recalculate_participant_statuses(self):
        """Тест функции перераспределения статусов"""
        print("\n=== Тест функции перераспределения статусов ===")
        
        # 1. Добавляем несколько групп
        self.event_service.join_event_with_group(self.event_id, self.users[0], 3, "user0", "User0", "Last0")
        self.event_service.join_event_with_group(self.event_id, self.users[1], 4, "user1", "User1", "Last1")
        self.event_service.join_event(self.event_id, self.users[2], "user2", "User2", "Last2")
        
        # 2. Проверяем исходное состояние
        participants = self.db.get_event_participants(self.event_id)
        confirmed_count = sum(p.get('main_group_size', 0) or 0 for p in participants if p['status'] in ['confirmed', 'mixed'])
        print(f"До перераспределения: {confirmed_count}/6")
        
        # 3. Вызываем перераспределение
        self.db.recalculate_participant_statuses(self.event_id)
        
        # 4. Проверяем результат
        participants = self.db.get_event_participants(self.event_id)
        confirmed_count = sum(p.get('main_group_size', 0) or 0 for p in participants if p['status'] in ['confirmed', 'mixed'])
        print(f"После перераспределения: {confirmed_count}/6")
        
        # Проверяем, что лимит не превышен
        self.assertLessEqual(confirmed_count, 6)
        
        # Проверяем, что все mixed-группы корректно обработаны
        for p in participants:
            if p['status'] == 'mixed':
                main_size = p.get('main_group_size', 0) or 0
                reserve_size = p.get('reserve_group_size', 0) or 0
                group_size = p.get('group_size', 1)
                print(f"Mixed-группа: {main_size} + {reserve_size} = {group_size}")
                self.assertEqual(main_size + reserve_size, group_size)
    
    def test_limit_change_with_mixed_groups(self):
        """Тест изменения лимита с mixed-группами"""
        print("\n=== Тест изменения лимита с mixed-группами ===")
        
        # 1. Добавляем группы
        self.event_service.join_event_with_group(self.event_id, self.users[0], 3, "user0", "User0", "Last0")
        self.event_service.join_event_with_group(self.event_id, self.users[1], 4, "user1", "User1", "Last1")
        
        # 2. Уменьшаем лимит до 4
        result = self.event_service.change_participant_limit(self.event_id, 4)
        print(f"Изменение лимита: {result}")
        self.assertTrue(result['success'])
        
        # 3. Проверяем результат
        participants = self.db.get_event_participants(self.event_id)
        confirmed_count = sum(p.get('main_group_size', 0) or 0 for p in participants if p['status'] in ['confirmed', 'mixed'])
        print(f"После изменения лимита: {confirmed_count}/4")
        
        # Должно быть не больше 4 в основном составе
        self.assertLessEqual(confirmed_count, 4)
        
        # Проверяем, что mixed-группы корректно перераспределились
        mixed_groups = [p for p in participants if p['status'] == 'mixed']
        for p in mixed_groups:
            main_size = p.get('main_group_size', 0) or 0
            reserve_size = p.get('reserve_group_size', 0) or 0
            group_size = p.get('group_size', 1)
            print(f"Mixed-группа после изменения лимита: {main_size} + {reserve_size} = {group_size}")
            self.assertEqual(main_size + reserve_size, group_size)

if __name__ == '__main__':
    unittest.main(verbosity=2) 