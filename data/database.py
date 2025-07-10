import sqlite3
import logging
from datetime import datetime, date
from typing import List, Dict, Optional
from utils.timezone_utils import get_now_with_timezone

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = "volleyball_bot.db"):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Получить соединение с базой данных"""
        return sqlite3.connect(self.db_path)
    
    def init_database(self):
        """Инициализация базы данных"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Таблица событий
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    date DATE NOT NULL,
                    time TIME NOT NULL,
                    max_participants INTEGER DEFAULT 18,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    subscribed BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица участников событий
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS participants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER,
                    user_id INTEGER,
                    status TEXT DEFAULT 'confirmed',
                    position INTEGER,
                    confirmed_presence BOOLEAN DEFAULT FALSE,
                    reminder_sent BOOLEAN DEFAULT FALSE,
                    second_reminder_sent BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (event_id) REFERENCES events (id),
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            conn.commit()
            logger.info("База данных инициализирована")
    
    # Методы для работы с событиями
    def create_event(self, name: str, event_date: date, event_time: str, max_participants: int = 18) -> int:
        """Создать новое событие"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO events (name, date, time, max_participants)
                VALUES (?, ?, ?, ?)
            ''', (name, event_date, event_time, max_participants))
            conn.commit()
            result = cursor.lastrowid
            if result is None:
                raise Exception("Не удалось создать событие")
            return result
    
    def get_active_events(self) -> List[Dict]:
        """Получить все активные события"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Используем текущую дату с таймзоной вместо SQL DATE('now')
            current_date = get_now_with_timezone().date()
            cursor.execute('''
                SELECT id, name, date, time, max_participants, status
                FROM events 
                WHERE status = 'active' AND date >= ?
                ORDER BY date, time
            ''', (current_date,))
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_event_by_id(self, event_id: int) -> Optional[Dict]:
        """Получить событие по ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, name, date, time, max_participants, status
                FROM events 
                WHERE id = ?
            ''', (event_id,))
            row = cursor.fetchone()
            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
            return None
    
    def delete_event(self, event_id: int):
        """Удалить событие"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM events WHERE id = ?', (event_id,))
            cursor.execute('DELETE FROM participants WHERE event_id = ?', (event_id,))
            conn.commit()
    
    def cleanup_past_events(self):
        """Удалить прошедшие события"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Используем текущую дату с таймзоной вместо SQL DATE('now')
            current_date = get_now_with_timezone().date()
            cursor.execute('''
                DELETE FROM events 
                WHERE date < ?
            ''', (current_date,))
            conn.commit()
    
    # Методы для работы с пользователями
    def add_user(self, telegram_id: int, username: Optional[str] = None, first_name: Optional[str] = None, last_name: Optional[str] = None) -> int:
        """Добавить пользователя или обновить существующего"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Сначала проверяем, существует ли пользователь
            cursor.execute('''
                SELECT id FROM users WHERE telegram_id = ?
            ''', (telegram_id,))
            existing_user = cursor.fetchone()
            
            if existing_user:
                # Пользователь существует, обновляем его данные
                cursor.execute('''
                    UPDATE users 
                    SET username = COALESCE(?, username),
                        first_name = COALESCE(?, first_name),
                        last_name = COALESCE(?, last_name)
                    WHERE telegram_id = ?
                ''', (username, first_name, last_name, telegram_id))
                conn.commit()
                return existing_user[0]
            else:
                # Пользователь не существует, создаем нового
                cursor.execute('''
                    INSERT INTO users (telegram_id, username, first_name, last_name)
                    VALUES (?, ?, ?, ?)
                ''', (telegram_id, username, first_name, last_name))
                conn.commit()
                result = cursor.lastrowid
                if result is None:
                    raise Exception("Не удалось добавить пользователя")
                return result
    
    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict]:
        """Получить пользователя по его telegram_id"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, telegram_id, username, first_name, last_name, subscribed
                FROM users 
                WHERE telegram_id = ?
            ''', (telegram_id,))
            row = cursor.fetchone()
            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
            return None
    
    def get_subscribed_users(self) -> List[int]:
        """Получить всех подписанных пользователей"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT telegram_id FROM users WHERE subscribed = TRUE')
            return [row[0] for row in cursor.fetchall()]
    
    def update_user_subscription(self, telegram_id: int, subscribed: bool):
        """Обновить статус подписки пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users 
                SET subscribed = ? 
                WHERE telegram_id = ?
            ''', (subscribed, telegram_id))
            conn.commit()
    
    # Методы для работы с участниками
    def add_participant(self, event_id: int, telegram_id: int, status: str = 'confirmed') -> int:
        """Добавить участника к событию"""
        user = self.get_user_by_telegram_id(telegram_id)
        if not user:
            raise Exception(f"Пользователь с telegram_id {telegram_id} не найден.")
        user_id = user['id']

        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Получить текущую позицию
            cursor.execute('''
                SELECT COUNT(*) FROM participants 
                WHERE event_id = ?
            ''', (event_id,))
            position = cursor.fetchone()[0] + 1
            
            cursor.execute('''
                INSERT INTO participants (event_id, user_id, status, position)
                VALUES (?, ?, ?, ?)
            ''', (event_id, user_id, status, position))
            conn.commit()
            result = cursor.lastrowid
            if result is None:
                raise Exception("Не удалось добавить участника")
            return result
    
    def get_event_participants(self, event_id: int) -> List[Dict]:
        """Получить всех участников события"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT p.id, p.status, p.position, p.confirmed_presence, p.reminder_sent, p.second_reminder_sent,
                       u.telegram_id, u.username, u.first_name, u.last_name
                FROM participants p
                JOIN users u ON p.user_id = u.id
                WHERE p.event_id = ?
                ORDER BY p.position
            ''', (event_id,))
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_participant(self, event_id: int, telegram_id: int) -> Optional[Dict]:
        """Получить участника события по telegram_id"""
        user = self.get_user_by_telegram_id(telegram_id)
        if not user:
            return None
        user_id = user['id']

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT p.id, p.status, p.position, p.confirmed_presence, p.reminder_sent, p.second_reminder_sent,
                       u.id as user_id, u.telegram_id, u.username, u.first_name, u.last_name
                FROM participants p
                JOIN users u ON p.user_id = u.id
                WHERE p.event_id = ? AND p.user_id = ?
            ''', (event_id, user_id))
            row = cursor.fetchone()
            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
            return None
    
    def remove_participant(self, event_id: int, telegram_id: int):
        """Удалить участника из события по telegram_id"""
        user = self.get_user_by_telegram_id(telegram_id)
        if not user:
            return
        user_id = user['id']

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM participants 
                WHERE event_id = ? AND user_id = ?
            ''', (event_id, user_id))
            conn.commit()
            self._reorder_participants(event_id)
    
    def update_participant_status(self, event_id: int, telegram_id: int, status: str):
        """Обновить статус участника"""
        user = self.get_user_by_telegram_id(telegram_id)
        if not user:
            return
        user_id = user['id']

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE participants 
                SET status = ? 
                WHERE event_id = ? AND user_id = ?
            ''', (status, event_id, user_id))
            conn.commit()
    
    def confirm_presence(self, event_id: int, telegram_id: int):
        """Подтвердить присутствие участника по telegram_id"""
        user = self.get_user_by_telegram_id(telegram_id)
        if not user:
            return
        user_id = user['id']

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE participants 
                SET confirmed_presence = TRUE 
                WHERE event_id = ? AND user_id = ?
            ''', (event_id, user_id))
            conn.commit()
    
    def mark_reminder_sent(self, event_id: int, telegram_id: int, reminder_type: str = 'first'):
        """Отметить, что напоминание отправлено, по telegram_id"""
        user = self.get_user_by_telegram_id(telegram_id)
        if not user:
            return
        user_id = user['id']

        with self.get_connection() as conn:
            cursor = conn.cursor()
            if reminder_type == 'second':
                cursor.execute('''
                    UPDATE participants 
                    SET second_reminder_sent = TRUE 
                    WHERE event_id = ? AND user_id = ?
                ''', (event_id, user_id))
            else:
                cursor.execute('''
                    UPDATE participants 
                    SET reminder_sent = TRUE 
                    WHERE event_id = ? AND user_id = ?
                ''', (event_id, user_id))
            conn.commit()
    
    def get_unconfirmed_participants(self, event_id: int) -> List[Dict]:
        """Получить участников, не подтвердивших присутствие"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT p.id, p.status, p.position, p.confirmed_presence, p.reminder_sent, p.second_reminder_sent,
                       u.telegram_id, u.username, u.first_name, u.last_name
                FROM participants p
                JOIN users u ON p.user_id = u.id
                WHERE p.event_id = ? AND p.status = 'confirmed' AND p.confirmed_presence = FALSE
                ORDER BY p.position
            ''', (event_id,))
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def _reorder_participants(self, event_id: int):
        """Пересчитать позиции участников после удаления"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id FROM participants 
                WHERE event_id = ? 
                ORDER BY position
            ''', (event_id,))
            participants = cursor.fetchall()
            
            for i, (participant_id,) in enumerate(participants, 1):
                cursor.execute('''
                    UPDATE participants 
                    SET position = ? 
                    WHERE id = ?
                ''', (i, participant_id))
            
            conn.commit()
    
    def get_reserve_participants(self, event_id: int) -> List[Dict]:
        """Получить участников в резерве"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT p.id, p.status, p.position, p.confirmed_presence, p.reminder_sent, p.second_reminder_sent,
                       u.telegram_id, u.username, u.first_name, u.last_name
                FROM participants p
                JOIN users u ON p.user_id = u.id
                WHERE p.event_id = ? AND p.status = 'reserve'
                ORDER BY p.position
            ''', (event_id,))
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def move_from_reserve_to_main(self, event_id: int) -> Optional[Dict]:
        """Переместить первого из резерва в основной состав"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Получить первого в резерве
            cursor.execute('''
                SELECT p.id, p.user_id, u.telegram_id, u.username
                FROM participants p
                JOIN users u ON p.user_id = u.id
                WHERE p.event_id = ? AND p.status = 'reserve'
                ORDER BY p.position
                LIMIT 1
            ''', (event_id,))
            
            reserve_participant = cursor.fetchone()
            if not reserve_participant:
                return None
            
            participant_id, user_id, telegram_id, username = reserve_participant
            
            # Обновить статус
            cursor.execute('''
                UPDATE participants 
                SET status = 'confirmed' 
                WHERE id = ?
            ''', (participant_id,))
            
            conn.commit()
            
            return {
                'telegram_id': telegram_id,
                'username': username
            }

    def get_all_users(self) -> List[Dict]:
        """Получить всех пользователей"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, telegram_id, username, first_name, last_name, subscribed, created_at FROM users ORDER BY id')
            users = cursor.fetchall()
            return [
                {
                    'id': row[0],
                    'telegram_id': row[1],
                    'username': row[2],
                    'first_name': row[3],
                    'last_name': row[4],
                    'subscribed': row[5],
                    'created_at': row[6]
                }
                for row in users
            ]
            
    def get_total_users_count(self) -> int:
        """Получить общее количество пользователей"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(id) FROM users')
            count = cursor.fetchone()[0]
            return count

    def get_active_events_count(self) -> int:
        """Получить количество активных событий"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(id) FROM events WHERE status = "active"')
            count = cursor.fetchone()[0]
            return count

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Получить пользователя по имени пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, telegram_id, username, first_name, last_name, subscribed
                FROM users 
                WHERE username = ?
            ''', (username,))
            row = cursor.fetchone()
            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
            return None 