import sqlite3
import logging
from datetime import datetime, date
from typing import List, Dict, Optional

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
                    group_size INTEGER DEFAULT 1,
                    main_group_size INTEGER DEFAULT 1,
                    reserve_group_size INTEGER DEFAULT 0,
                    confirmed_presence BOOLEAN DEFAULT FALSE,
                    reminder_sent BOOLEAN DEFAULT FALSE,
                    second_reminder_sent BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (event_id) REFERENCES events (id),
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Таблица истории чата
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL,
                    message_text TEXT NOT NULL,
                    message_type TEXT DEFAULT 'user',  -- 'user', 'bot', 'system'
                    event_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (event_id) REFERENCES events (id)
                )
            ''')
            
            # Таблица настроек бота
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bot_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Инициализируем настройки по умолчанию
            cursor.execute('''
                INSERT OR IGNORE INTO bot_settings (key, value) VALUES 
                ('group_registration_enabled', 'false'),
                ('max_group_size', '3')
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
            cursor.execute('''
                SELECT id, name, date, time, max_participants, status
                FROM events 
                WHERE status = 'active' AND date >= DATE('now')
                ORDER BY date, time
            ''')
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
    
    def update_event_max_participants(self, event_id: int, new_max_participants: int):
        """Обновить максимальное количество участников события"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE events 
                SET max_participants = ? 
                WHERE id = ?
            ''', (new_max_participants, event_id))
            conn.commit()
            logger.info(f"Обновлен лимит участников события {event_id} на {new_max_participants}")
    
    def cleanup_past_events(self):
        """Удалить прошедшие события"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Удаляем события, которые прошли (дата < сегодня ИЛИ дата = сегодня, но время уже прошло)
            cursor.execute('''
                DELETE FROM events 
                WHERE date < DATE('now') 
                   OR (date = DATE('now') AND time < TIME('now'))
            ''')
            deleted_count = cursor.rowcount
            conn.commit()
            logger.info(f"Удалено {deleted_count} прошедших событий")
    
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
    def add_participant(self, event_id: int, telegram_id: int, status: str = 'confirmed'):
        """Добавить участника события"""
        user = self.get_user_by_telegram_id(telegram_id)
        if not user:
            raise Exception(f"Пользователь с telegram_id {telegram_id} не найден.")
        user_id = user['id']
        
        # Определяем main_group_size и reserve_group_size на основе статуса
        if status == 'confirmed':
            main_group_size = 1
            reserve_group_size = 0
        elif status == 'reserve':
            main_group_size = 0
            reserve_group_size = 1
        else:  # mixed - не должно быть при создании
            main_group_size = 1
            reserve_group_size = 0
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO participants (event_id, user_id, status, position, group_size, main_group_size, reserve_group_size)
                SELECT ?, ?, ?, COALESCE(MAX(position), 0) + 1, 1, ?, ?
                FROM participants WHERE event_id = ?
            ''', (event_id, user_id, status, main_group_size, reserve_group_size, event_id))
            conn.commit()
            logger.info(f"Участник {telegram_id} добавлен к событию {event_id} со статусом {status}")
    
    def add_participant_with_group(self, event_id: int, telegram_id: int, status: str = 'confirmed', group_size: int = 1, 
                                  main_group_size: Optional[int] = None, reserve_group_size: Optional[int] = None):
        """Добавить участника события с указанным размером группы"""
        user = self.get_user_by_telegram_id(telegram_id)
        if not user:
            raise Exception(f"Пользователь с telegram_id {telegram_id} не найден.")
        user_id = user['id']
        
        # Если main_group_size и reserve_group_size не указаны, вычисляем их на основе статуса
        if main_group_size is None or reserve_group_size is None:
            if status == 'confirmed':
                main_group_size = group_size
                reserve_group_size = 0
            elif status == 'reserve':
                main_group_size = 0
                reserve_group_size = group_size
            else:  # mixed - не должно быть при создании
                main_group_size = group_size
                reserve_group_size = 0
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO participants (event_id, user_id, status, position, group_size, main_group_size, reserve_group_size)
                SELECT ?, ?, ?, COALESCE(MAX(position), 0) + 1, ?, ?, ?
                FROM participants WHERE event_id = ?
            ''', (event_id, user_id, status, group_size, main_group_size, reserve_group_size, event_id))
            conn.commit()
            logger.info(f"Участник {telegram_id} добавлен к событию {event_id} со статусом {status} и группой {group_size}")
    
    def get_event_participants(self, event_id: int) -> List[Dict]:
        """Получить всех участников события"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT p.id, p.status, p.position, p.confirmed_presence, p.reminder_sent, p.second_reminder_sent,
                       p.group_size, p.main_group_size, p.reserve_group_size, u.telegram_id, u.username, u.first_name, u.last_name
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
                       p.group_size, u.id as user_id, u.telegram_id, u.username, u.first_name, u.last_name
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
    
    def reduce_group_size(self, event_id: int, telegram_id: int, reduce_by: int) -> Dict:
        """Уменьшить размер группы участника"""
        user = self.get_user_by_telegram_id(telegram_id)
        if not user:
            raise Exception(f"Пользователь с telegram_id {telegram_id} не найден.")
        user_id = user['id']
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Получаем текущие данные участника
            cursor.execute('''
                SELECT group_size, main_group_size, reserve_group_size, status
                FROM participants 
                WHERE event_id = ? AND user_id = ?
            ''', (event_id, user_id))
            
            participant = cursor.fetchone()
            if not participant:
                raise Exception(f"Участник {telegram_id} не найден в событии {event_id}")
            
            current_group_size, current_main, current_reserve, current_status = participant
            
            if reduce_by >= current_group_size:
                # Если отписываем всю группу, удаляем участника
                cursor.execute('DELETE FROM participants WHERE event_id = ? AND user_id = ?', (event_id, user_id))
                new_group_size = 0
                new_main = 0
                new_reserve = 0
                new_status = 'removed'
            else:
                # Уменьшаем размер группы
                new_group_size = current_group_size - reduce_by
                
                if current_status == 'mixed':
                    # Для смешанных групп уменьшаем сначала резерв, потом основной
                    if current_reserve >= reduce_by:
                        new_reserve = current_reserve - reduce_by
                        new_main = current_main
                    else:
                        new_reserve = 0
                        new_main = current_main - (reduce_by - current_reserve)
                    
                    # Определяем новый статус
                    if new_main == 0:
                        new_status = 'reserve'
                    elif new_reserve == 0:
                        new_status = 'confirmed'
                    else:
                        new_status = 'mixed'
                else:
                    # Для обычных групп просто уменьшаем основной размер
                    new_main = new_group_size
                    new_reserve = 0
                    new_status = current_status
                
                # Обновляем данные
                cursor.execute('''
                    UPDATE participants 
                    SET group_size = ?, main_group_size = ?, reserve_group_size = ?, status = ?
                    WHERE event_id = ? AND user_id = ?
                ''', (new_group_size, new_main, new_reserve, new_status, event_id, user_id))
            
            conn.commit()
            logger.info(f"Размер группы участника {telegram_id} уменьшен на {reduce_by}")
            
            return {
                'old_group_size': current_group_size,
                'new_group_size': new_group_size,
                'old_status': current_status,
                'new_status': new_status,
                'freed_slots': reduce_by if current_status == 'confirmed' else 0,
                'freed_reserve_slots': reduce_by if current_status == 'reserve' else 0,
                'new_main_group_size': new_main,
                'new_reserve_group_size': new_reserve
            }
    
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
        """Переместить первого из резерва в основной состав с учетом размера группы"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Получить событие и его лимит
            cursor.execute('SELECT max_participants FROM events WHERE id = ?', (event_id,))
            event = cursor.fetchone()
            if not event:
                return None
            
            max_participants = event[0]
            
            # Получить всех участников в основном составе
            cursor.execute('''
                SELECT p.group_size
                FROM participants p
                WHERE p.event_id = ? AND p.status = 'confirmed'
                ORDER BY p.position
            ''', (event_id,))
            
            confirmed_participants = cursor.fetchall()
            current_people_count = sum(group_size for (group_size,) in confirmed_participants)
            
            # Получить первого в резерве
            cursor.execute('''
                SELECT p.id, p.user_id, p.group_size, u.telegram_id, u.username
                FROM participants p
                JOIN users u ON p.user_id = u.id
                WHERE p.event_id = ? AND p.status = 'reserve'
                ORDER BY p.position
                LIMIT 1
            ''', (event_id,))
            
            reserve_participant = cursor.fetchone()
            if not reserve_participant:
                return None
            
            participant_id, user_id, group_size, telegram_id, username = reserve_participant
            
            # Проверяем, поместится ли группа в основной состав
            if current_people_count + group_size <= max_participants:
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
            else:
                # Группа не помещается в основной состав
                return None

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
        """Получить пользователя по username"""
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
    
    # Методы для работы с историей чата
    def save_message(self, telegram_id: int, message_text: str, message_type: str = 'user', event_id: Optional[int] = None):
        """Сохранить сообщение в историю чата"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO chat_history (telegram_id, message_text, message_type, event_id)
                VALUES (?, ?, ?, ?)
            ''', (telegram_id, message_text, message_type, event_id))
            conn.commit()
    
    def get_chat_history(self, telegram_id: int, limit: int = 50) -> List[Dict]:
        """Получить историю чата для пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, telegram_id, message_text, message_type, event_id, created_at
                FROM chat_history 
                WHERE telegram_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (telegram_id, limit))
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_recent_chat_history(self, telegram_id: int, hours: int = 24) -> List[Dict]:
        """Получить историю чата за последние N часов"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, telegram_id, message_text, message_type, event_id, created_at
                FROM chat_history 
                WHERE telegram_id = ? AND created_at >= datetime('now', '-{} hours')
                ORDER BY created_at ASC
            '''.format(hours), (telegram_id,))
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def clear_chat_history(self, telegram_id: int):
        """Очистить историю чата для пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM chat_history WHERE telegram_id = ?', (telegram_id,))
            conn.commit()
    
    def get_chat_history_count(self, telegram_id: int) -> int:
        """Получить количество сообщений в истории чата пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM chat_history 
                WHERE telegram_id = ?
            ''', (telegram_id,))
            return cursor.fetchone()[0]
    
    # Методы для работы с настройками бота
    def get_bot_setting(self, key: str) -> Optional[str]:
        """Получить настройку бота по ключу"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT value FROM bot_settings 
                WHERE key = ?
            ''', (key,))
            row = cursor.fetchone()
            return row[0] if row else None
    
    def set_bot_setting(self, key: str, value: str):
        """Установить настройку бота"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO bot_settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (key, value))
            conn.commit()
            logger.info(f"Настройка {key} установлена в {value}")
    
    def is_group_registration_enabled(self) -> bool:
        """Проверить, включена ли запись группами"""
        setting = self.get_bot_setting('group_registration_enabled')
        return setting == 'true'
    
    def get_max_group_size(self) -> int:
        """Получить максимальный размер группы"""
        setting = self.get_bot_setting('max_group_size')
        return int(setting) if setting else 3

    def move_people_from_reserve_to_main(self, event_id: int, freed_slots: int) -> list:
        """Переместить людей из резерва в основной состав поштучно, корректно обновляя mixed-группы"""
        moved = []
        with self.get_connection() as conn:
            cursor = conn.cursor()
            while freed_slots > 0:
                # Получаем всех резервистов по позиции
                cursor.execute('''
                    SELECT p.id, p.user_id, p.group_size, p.main_group_size, p.reserve_group_size, p.status, u.telegram_id, u.username
                    FROM participants p
                    JOIN users u ON p.user_id = u.id
                    WHERE p.event_id = ? AND p.status IN ('reserve', 'mixed')
                    ORDER BY p.position
                ''', (event_id,))
                reserve_participants = cursor.fetchall()
                if not reserve_participants:
                    break
                # Берём первого резервиста
                p_id, user_id, group_size, main_group_size, reserve_group_size, status, telegram_id, username = reserve_participants[0]
                
                # Обрабатываем None значения
                main_group_size = main_group_size or 0
                reserve_group_size = reserve_group_size or 0
                
                if status == 'reserve':
                    # Если вся группа в резерве, переводим поштучно
                    if group_size == 1:
                        # Вся группа помещается
                        cursor.execute('UPDATE participants SET status = \'confirmed\', main_group_size = 1, reserve_group_size = 0 WHERE id = ?', (p_id,))
                        moved.append({'telegram_id': telegram_id, 'username': username})
                        freed_slots -= 1
                    else:
                        # Переводим одного человека из группы
                        new_main = 1
                        new_reserve = group_size - 1
                        cursor.execute('''
                            UPDATE participants SET status = 'mixed', main_group_size = ?, reserve_group_size = ?, group_size = ? WHERE id = ?
                        ''', (new_main, new_reserve, group_size, p_id))
                        moved.append({'telegram_id': telegram_id, 'username': username})
                        freed_slots -= 1
                elif status == 'mixed':
                    # В mixed-группе часть уже в основном составе, часть в резерве
                    if reserve_group_size > 0:
                        new_main = main_group_size + 1
                        new_reserve = reserve_group_size - 1
                        new_status = 'confirmed' if new_reserve == 0 else 'mixed'
                        cursor.execute('''
                            UPDATE participants SET main_group_size = ?, reserve_group_size = ?, status = ? WHERE id = ?
                        ''', (new_main, new_reserve, new_status, p_id))
                        moved.append({'telegram_id': telegram_id, 'username': username})
                        freed_slots -= 1
                    else:
                        # Нет резервистов в mixed-группе, пропускаем
                        break
                else:
                    break
            conn.commit()
        return moved

    def recalculate_participant_statuses(self, event_id: int):
        """Пересчитать статусы всех участников события с полным перераспределением по позициям"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Получаем лимит события
            cursor.execute('SELECT max_participants FROM events WHERE id = ?', (event_id,))
            event = cursor.fetchone()
            if not event:
                return
            max_participants = event[0]
            
            # Получаем всех участников, отсортированных по позиции
            cursor.execute('''
                SELECT id, group_size, main_group_size, reserve_group_size, status, position
                FROM participants 
                WHERE event_id = ?
                ORDER BY position
            ''', (event_id,))
            
            participants = cursor.fetchall()
            
            # Перераспределяем участников поштучно
            current_people_count = 0
            updated_participants = []
            
            for participant_id, group_size, main_group_size, reserve_group_size, current_status, position in participants:
                # Обрабатываем None значения
                main_group_size = main_group_size or 0
                reserve_group_size = reserve_group_size or 0
                
                # Определяем, сколько людей из группы поместится в основной состав
                available_slots = max_participants - current_people_count
                new_main_size = min(group_size, available_slots)
                new_reserve_size = group_size - new_main_size
                
                # Определяем новый статус
                if new_main_size == 0:
                    new_status = 'reserve'
                elif new_reserve_size == 0:
                    new_status = 'confirmed'
                else:
                    new_status = 'mixed'
                
                # Обновляем данные участника
                cursor.execute('''
                    UPDATE participants 
                    SET status = ?, main_group_size = ?, reserve_group_size = ?
                    WHERE id = ?
                ''', (new_status, new_main_size, new_reserve_size, participant_id))
                
                # Увеличиваем счетчик людей в основном составе
                current_people_count += new_main_size
                
                updated_participants.append({
                    'id': participant_id,
                    'old_status': current_status,
                    'new_status': new_status,
                    'old_main': main_group_size,
                    'new_main': new_main_size,
                    'old_reserve': reserve_group_size,
                    'new_reserve': new_reserve_size
                })
            
            conn.commit()
            
            # Логируем изменения
            changes = [p for p in updated_participants if p['old_status'] != p['new_status'] or 
                      p['old_main'] != p['new_main'] or p['old_reserve'] != p['new_reserve']]
            
            if changes:
                logger.info(f"Перераспределены участники события {event_id}: {len(changes)} изменений")
                for change in changes:
                    logger.info(f"Участник {change['id']}: {change['old_status']}->{change['new_status']}, "
                              f"основной: {change['old_main']}->{change['new_main']}, "
                              f"резерв: {change['old_reserve']}->{change['new_reserve']}")
            else:
                logger.info(f"Пересчитаны статусы участников для события {event_id} (изменений нет)") 