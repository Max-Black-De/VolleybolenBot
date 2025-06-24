import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
from db.database import Database
from config.settings import BOT_SETTINGS, MESSAGES

logger = logging.getLogger(__name__)

class EventService:
    def __init__(self, database: Database):
        self.db = database
        self.max_participants = BOT_SETTINGS['MAX_PARTICIPANTS']
    
    def _format_date_russian(self, target_date: date) -> str:
        """Форматировать дату на русском языке"""
        month_names = {
            1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля',
            5: 'мая', 6: 'июня', 7: 'июля', 8: 'августа',
            9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
        }
        weekday_names = {
            0: 'понедельник', 1: 'вторник', 2: 'среда', 
            3: 'четверг', 4: 'пятница', 5: 'суббота', 6: 'воскресенье'
        }
        day = target_date.day
        month = month_names[target_date.month]
        weekday = weekday_names[target_date.weekday()]
        return f"{day} {month} {weekday}"
    
    def get_next_training_day(self) -> date:
        """Определить ближайший тренировочный день"""
        today = datetime.now().date()
        weekday = today.weekday()
        if weekday < 3:
            delta_days = 3 - weekday
        elif weekday < 6:
            delta_days = 6 - weekday
        else:
            delta_days = 4
        return today + timedelta(days=delta_days)
    
    def create_event_on_date(self, target_date: date) -> int:
        """Создать событие на конкретную дату, если его ещё нет"""
        existing_event = self.get_event_by_date(target_date)
        if existing_event:
            logger.info(f"Событие на {target_date} уже существует (ID: {existing_event['id']})")
            return existing_event['id']
        formatted_date = self._format_date_russian(target_date)
        event_name = f"Запись на тренировку по волейболу\n{formatted_date} в {BOT_SETTINGS['TRAINING_TIME']}"
        event_id = self.db.create_event(
            name=event_name,
            event_date=target_date,
            event_time=BOT_SETTINGS['TRAINING_TIME'],
            max_participants=self.max_participants
        )
        logger.info(f"Создано событие: {event_name} с ID: {event_id}")
        return event_id
    
    def create_scheduled_events(self) -> List[int]:
        """Создать события по расписанию"""
        event_ids = []
        next_training_day = self.get_next_training_day()
        event_id = self.create_event_on_date(next_training_day)
        event_ids.append(event_id)
        return event_ids
    
    def get_active_events(self) -> List[Dict]:
        """Получить все активные события"""
        return self.db.get_active_events()
    
    def get_event_by_id(self, event_id: int) -> Optional[Dict]:
        """Получить событие по ID"""
        return self.db.get_event_by_id(event_id)
    
    def delete_event(self, event_id: int):
        """Удалить событие"""
        self.db.delete_event(event_id)
        logger.info(f"Событие {event_id} удалено")
    
    def cleanup_past_events(self):
        """Удалить прошедшие события"""
        self.db.cleanup_past_events()
        logger.info("Прошедшие события удалены")
    
    def join_event(self, event_id: int, telegram_id: int, username: Optional[str] = None, first_name: Optional[str] = None, last_name: Optional[str] = None) -> Dict:
        """Записать пользователя на событие"""
        user_db = self.db.get_user_by_telegram_id(telegram_id)
        if not user_db:
            self.db.add_user(telegram_id, username, first_name, last_name)

        existing_participant = self.db.get_participant(event_id, telegram_id)
        if existing_participant:
            return {'success': False, 'message': MESSAGES['already_joined']}
        
        event = self.db.get_event_by_id(event_id)
        if not event:
            return {'success': False, 'message': 'Событие не найдено'}
        
        participants = self.db.get_event_participants(event_id)
        confirmed_count = len([p for p in participants if p['status'] == 'confirmed'])
        
        status = 'confirmed' if confirmed_count < event['max_participants'] else 'reserve'
        if status == 'confirmed':
            formatted_date = self._format_date_russian(datetime.strptime(event['date'], '%Y-%m-%d').date())
            message = MESSAGES['joined_confirmed'].format(event_date=formatted_date)
        else:
            message = MESSAGES['joined_reserve']
        
        self.db.add_participant(event_id, telegram_id, status)
        
        return {
            'success': True,
            'message': message,
            'status': status,
            'position': confirmed_count + 1
        }
    
    def leave_event(self, event_id: int, telegram_id: int) -> Dict:
        """Отписать пользователя от события"""
        participant = self.db.get_participant(event_id, telegram_id)
        if not participant:
            return {'success': False, 'message': MESSAGES['not_joined']}
        
        self.db.remove_participant(event_id, telegram_id)
        
        moved_participant = self.db.move_from_reserve_to_main(event_id)
        
        return {
            'success': True,
            'message': MESSAGES['leave_success'],
            'moved_participant': moved_participant
        }
    
    def get_participants_list(self, event_id: int, event_info: Optional[Dict] = None) -> str:
        """Получить список участников в текстовом виде"""
        participants = self.db.get_event_participants(event_id)
        
        if not participants:
            return "Ещё никто не записался! Будь первым!"
        
        if event_info:
            event_date = event_info['date']
            if isinstance(event_date, str):
                event_date = datetime.strptime(event_date, '%Y-%m-%d').date()
            formatted_date = self._format_date_russian(event_date)
            header = f"Список участников на {formatted_date}:"
        else:
            header = "Список участников:"
        
        lines = [header]
        for i, participant in enumerate(participants, 1):
            status = "Резерв" if participant['status'] == 'reserve' else "Основной"
            
            # Формируем отображаемое имя
            display_name = self._get_display_name(participant)
            
            lines.append(f"{i}. {display_name} - {status}")
        
        return "\n".join(lines)
    
    def _get_display_name(self, participant: Dict) -> str:
        """Получить отображаемое имя пользователя"""
        first_name = participant.get('first_name')
        username = participant.get('username')
        telegram_id = participant.get('telegram_id')
        
        # Приоритет: first_name -> username -> telegram_id (Вы)
        if first_name and first_name.strip():
            return first_name.strip()
        elif username and username.strip():
            return f"@{username.strip()}"
        else:
            return f"{telegram_id} (Вы)"
    
    def confirm_presence(self, event_id: int, telegram_id: int) -> bool:
        """Подтвердить присутствие участника"""
        participant = self.db.get_participant(event_id, telegram_id)
        if not participant:
            return False
        
        self.db.confirm_presence(event_id, telegram_id)
        return True
    
    def get_unconfirmed_participants(self, event_id: int) -> List[Dict]:
        """Получить участников, не подтвердивших присутствие"""
        return self.db.get_unconfirmed_participants(event_id)
    
    def auto_leave_unconfirmed(self, event_id: int) -> List[Dict]:
        """Автоматически отписать неподтвердивших участников"""
        unconfirmed = self.db.get_unconfirmed_participants(event_id)
        moved_participants = []
        
        for participant in unconfirmed:
            self.db.remove_participant(event_id, participant['telegram_id'])
            moved = self.db.move_from_reserve_to_main(event_id)
            if moved:
                moved_participants.append(moved)
        
        return moved_participants
    
    def mark_reminder_sent(self, event_id: int, telegram_id: int, reminder_type: str = 'first'):
        """Отметить, что напоминание отправлено"""
        self.db.mark_reminder_sent(event_id, telegram_id, reminder_type)
    
    def get_participants_for_reminder(self, event_id: int, reminder_type: str = 'first') -> List[Dict]:
        """Получить участников для отправки напоминания"""
        participants = self.db.get_event_participants(event_id)
        
        if reminder_type == 'first':
            return [p for p in participants if p['status'] == 'confirmed' and not p['confirmed_presence'] and not p['reminder_sent']]
        else:
            return [p for p in participants if p['status'] == 'confirmed' and not p['confirmed_presence'] and p['reminder_sent'] and not p['second_reminder_sent']]
    
    def get_event_by_date(self, target_date: date) -> Optional[Dict]:
        """Получить активное событие по дате"""
        events = self.get_active_events()
        for event in events:
            if isinstance(event['date'], str):
                event_date = datetime.strptime(event['date'], '%Y-%m-%d').date()
            else:
                event_date = event['date']
            if event_date == target_date:
                return event
        return None 