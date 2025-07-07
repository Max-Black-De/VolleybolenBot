import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
from data.database import Database
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
        
        # Получаем все активные события
        active_events = self.get_active_events()
        
        # Проверяем, есть ли уже события на ближайшие дни
        next_training_day = self.get_next_training_day()
        
        # Проверяем, есть ли уже событие на эту дату
        existing_event = self.get_event_by_date(next_training_day)
        if existing_event:
            logger.info(f"Событие на {next_training_day} уже существует (ID: {existing_event['id']})")
            return [existing_event['id']]
        
        # Проверяем, не слишком ли рано создавать событие
        today = datetime.now().date()
        days_until_training = (next_training_day - today).days
        
        # Создаем событие только если до тренировки больше 1 дня
        if days_until_training > 1:
            event_id = self.create_event_on_date(next_training_day)
            event_ids.append(event_id)
            logger.info(f"Создано событие на {next_training_day} (через {days_until_training} дней)")
        else:
            logger.info(f"Слишком рано создавать событие на {next_training_day} (через {days_until_training} дней)")
        
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
        # Считаем общее количество людей в основном составе (main_group_size по всем confirmed и mixed)
        confirmed_people_count = sum(
            p.get('main_group_size', 1) or 0 for p in participants if p['status'] in ['confirmed', 'mixed']
        )
        
        status = 'confirmed' if confirmed_people_count < event['max_participants'] else 'reserve'
        if status == 'confirmed':
            formatted_date = self._format_date_russian(datetime.strptime(event['date'], '%Y-%m-%d').date())
            message = MESSAGES['joined_confirmed'].format(event_date=formatted_date)
        else:
            message = MESSAGES['joined_reserve']
        
        self.db.add_participant(event_id, telegram_id, status)
        # Пересчитываем статусы всех участников
        self.db.recalculate_participant_statuses(event_id)
        
        return {
            'success': True,
            'message': message,
            'status': status,
            'position': len([p for p in participants if p['status'] == 'confirmed']) + 1
        }
    
    def leave_event(self, event_id: int, telegram_id: int) -> Dict:
        """Отписать пользователя от события"""
        participant = self.db.get_participant(event_id, telegram_id)
        if not participant:
            return {'success': False, 'message': MESSAGES['not_joined']}
        
        group_size = participant.get('group_size', 1)
        self.db.remove_participant(event_id, telegram_id)
        
        # Перераспределяем места поштучно
        moved_participants = self.db.move_people_from_reserve_to_main(event_id, group_size)
        
        # Пересчитываем статусы всех участников
        self.db.recalculate_participant_statuses(event_id)
        
        return {
            'success': True,
            'message': MESSAGES['leave_success'],
            'moved_participants': moved_participants
        }
    
    def reduce_group_size(self, event_id: int, telegram_id: int, reduce_by: int) -> Dict:
        """Уменьшить размер группы участника"""
        participant = self.db.get_participant(event_id, telegram_id)
        if not participant:
            return {'success': False, 'message': MESSAGES['not_joined']}
        
        group_size = participant.get('group_size', 1)
        if reduce_by >= group_size:
            # Если отписываем всю группу, используем обычную отписку
            return self.leave_event(event_id, telegram_id)
        
        # Уменьшаем размер группы
        try:
            result = self.db.reduce_group_size(event_id, telegram_id, reduce_by)
        except Exception as e:
            return {'success': False, 'message': f'Ошибка при уменьшении группы: {str(e)}'}
        
        # Перемещаем людей из резерва в основной состав, если освободились места
        moved_participants = self.db.move_people_from_reserve_to_main(event_id, reduce_by)
        
        # Пересчитываем статусы всех участников
        self.db.recalculate_participant_statuses(event_id)
        
        # Формируем сообщение
        if result['new_status'] == 'removed':
            message = MESSAGES['leave_success']
        else:
            new_size = result['new_group_size']
            if result['new_status'] == 'mixed':
                main_size = result.get('new_main_group_size', 0) or 0
                reserve_size = result.get('new_reserve_group_size', 0) or 0
                message = f'Размер группы уменьшен до {new_size} человек ({main_size} в основном составе, {reserve_size} в резерве)'
            else:
                status_text = 'основном составе' if result['new_status'] == 'confirmed' else 'резерве'
                message = f'Размер группы уменьшен до {new_size} человек (в {status_text})'
        
        if moved_participants:
            moved_names = ', '.join([p['username'] for p in moved_participants])
            message += f'\nПеремещены в основной состав: {moved_names}'
        
        return {
            'success': True,
            'message': message,
            'old_group_size': result['old_group_size'],
            'new_group_size': result['new_group_size'],
            'old_status': result['old_status'],
            'new_status': result['new_status'],
            'moved_participants': moved_participants
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
        
        # Получаем лимит участников
        event = self.get_event_by_id(event_id)
        max_participants = event['max_participants'] if event else 18
        
        # Считаем реальное количество людей в основном составе и резерве
        confirmed_people_count = 0
        reserve_people_count = 0
        
        for participant in participants:
            group_size = participant.get('group_size', 1)
            status = participant['status']
            if status == 'confirmed':
                confirmed_people_count += group_size
            elif status == 'reserve':
                reserve_people_count += group_size
            elif status == 'mixed':
                main_size = participant.get('main_group_size', 0) or 0
                reserve_size = participant.get('reserve_group_size', 0) or 0
                confirmed_people_count += main_size
                reserve_people_count += reserve_size
        
        lines = [header]
        lines.append(f"📊 Основной состав: {confirmed_people_count}/{max_participants} человек")
        if reserve_people_count > 0:
            lines.append(f"📋 Резерв: {reserve_people_count} человек")
        lines.append("")
        
        # Формируем список участников
        participant_lines = []
        position = 1
        
        for participant in participants:
            status = participant['status']
            display_name = self._get_display_name(participant)
            group_size = participant.get('group_size', 1)
            main_size = participant.get('main_group_size', 0) or 0
            reserve_size = participant.get('reserve_group_size', 0) or 0
            
            # Добавляем информацию о группе только если это группа из нескольких человек
            group_info = f" (группа из {group_size})" if group_size > 1 else ""
            
            if status == 'confirmed':
                display_status = "Основной"
                participant_lines.append(f"{position}. {display_name}{group_info} - {display_status}")
                position += 1
            elif status == 'mixed':
                # Только граничная группа показывает разбивку
                parts = []
                if main_size > 0:
                    parts.append(f"Основной: {main_size}")
                if reserve_size > 0:
                    parts.append(f"Резерв: {reserve_size}")
                display_status = " + ".join(parts)
                participant_lines.append(f"{position}. {display_name}{group_info} - {display_status}")
                position += 1
            elif status == 'reserve':
                display_status = "Резерв"
                participant_lines.append(f"{position}. {display_name}{group_info} - {display_status}")
                position += 1
        
        lines.extend(participant_lines)
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
        left_participants = []
        
        for participant in unconfirmed:
            # Отписываем участника (если это группа, отписывается вся группа)
            group_size = participant.get('group_size', 1)
            self.db.remove_participant(event_id, participant['telegram_id'])
            left_participants.append(participant)
            
            # Перемещаем кого-то из резерва в основной состав
            moved = self.db.move_from_reserve_to_main(event_id)
            if moved:
                left_participants.append(moved)
        
        return left_participants
    
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
    
    def change_participant_limit(self, event_id: int, new_limit: int) -> Dict:
        """Изменить лимит участников и перераспределить их"""
        try:
            # Получаем событие
            event = self.get_event_by_id(event_id)
            if not event:
                return {'success': False, 'message': 'Событие не найдено'}
            
            old_limit = event['max_participants']
            
            # Если лимит не изменился, ничего не делаем
            if old_limit == new_limit:
                return {'success': True, 'message': 'Лимит не изменился', 'moved_to_main': [], 'moved_to_reserve': []}
            
            # Получаем всех участников, отсортированных по позиции
            participants = self.db.get_event_participants(event_id)
            participants.sort(key=lambda x: x['position'])
            
            moved_to_main = []
            moved_to_reserve = []
            
            # Обновляем лимит в базе данных
            self.db.update_event_max_participants(event_id, new_limit)
            
            # Перераспределяем участников с учетом размера групп
            current_people_count = 0
            for participant in participants:
                group_size = participant.get('group_size', 1)
                old_status = participant['status']
                
                # Проверяем, поместится ли группа в основной состав
                if current_people_count + group_size <= new_limit:
                    new_status = 'confirmed'
                    current_people_count += group_size
                else:
                    new_status = 'reserve'
                
                if new_status != old_status:
                    # Обновляем статус участника
                    self.db.update_participant_status(event_id, participant['telegram_id'], new_status)
                    
                    # Формируем информацию о перемещенном участнике
                    moved_participant = {
                        'telegram_id': participant['telegram_id'],
                        'username': participant['username'],
                        'display_name': self._get_display_name(participant)
                    }
                    
                    if new_status == 'confirmed':
                        moved_to_main.append(moved_participant)
                    else:
                        moved_to_reserve.append(moved_participant)
            
            # Пересчитываем позиции участников
            self.db._reorder_participants(event_id)
            
            # Пересчитываем статусы всех участников
            self.db.recalculate_participant_statuses(event_id)
            
            logger.info(f"Лимит участников изменен с {old_limit} на {new_limit} для события {event_id}")
            logger.info(f"Перемещено в основной состав: {len(moved_to_main)}, в резерв: {len(moved_to_reserve)}")
            
            return {
                'success': True,
                'message': f'Лимит изменен с {old_limit} на {new_limit}',
                'moved_to_main': moved_to_main,
                'moved_to_reserve': moved_to_reserve
            }
            
        except Exception as e:
            logger.error(f"Ошибка при изменении лимита участников: {e}")
            return {'success': False, 'message': f'Ошибка: {str(e)}'}
    
    def join_event_with_group(self, event_id: int, telegram_id: int, group_size: int, 
                             username: Optional[str] = None, first_name: Optional[str] = None, 
                             last_name: Optional[str] = None) -> Dict:
        """Записать пользователя на событие с указанным размером группы"""
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
        
        # Считаем общее количество людей в основном составе
        confirmed_people_count = 0
        for p in participants:
            if p['status'] == 'confirmed':
                # confirmed-группа полностью в основном составе
                confirmed_people_count += p.get('group_size', 1)
            elif p['status'] == 'mixed':
                # mixed-группа частично в основном составе
                confirmed_people_count += p.get('main_group_size', 0) or 0
        
        # Проверяем, сколько людей из группы поместится в основной состав
        available_slots = event['max_participants'] - confirmed_people_count
        main_group_size = min(group_size, max(0, available_slots))
        reserve_group_size = group_size - main_group_size
        
        if main_group_size == 0:
            # Вся группа идет в резерв
            status = 'reserve'
            message = MESSAGES['joined_reserve']
            final_group_size = group_size
        elif reserve_group_size == 0:
            # Вся группа помещается в основной состав
            status = 'confirmed'
            formatted_date = self._format_date_russian(datetime.strptime(event['date'], '%Y-%m-%d').date())
            message = MESSAGES['joined_confirmed'].format(event_date=formatted_date)
            final_group_size = group_size
        else:
            # Группа разделяется
            status = 'mixed'
            formatted_date = self._format_date_russian(datetime.strptime(event['date'], '%Y-%m-%d').date())
            message = f"Вы записаны на тренировку {formatted_date}.\n{main_group_size} человек в основном составе, {reserve_group_size} в резерве."
            final_group_size = group_size
        
        # Добавляем участника с размером группы
        self.db.add_participant_with_group(
            event_id, telegram_id, status, final_group_size,
            main_group_size if status == 'mixed' else None,
            reserve_group_size if status == 'mixed' else None
        )
        # Пересчитываем статусы всех участников
        self.db.recalculate_participant_statuses(event_id)
        
        return {
            'success': True,
            'message': message,
            'status': status,
            'position': len([p for p in participants if p['status'] == 'confirmed']) + 1,
            'group_size': final_group_size,
            'main_group_size': main_group_size,
            'reserve_group_size': reserve_group_size
        }
    
    def leave_group(self, event_id: int, telegram_id: int, group_size: int) -> Dict:
        """Отписать группу от события"""
        participant = self.db.get_participant(event_id, telegram_id)
        if not participant:
            return {'success': False, 'message': MESSAGES['not_joined']}
        
        # Удаляем участника (группа учитывается как один участник)
        self.db.remove_participant(event_id, telegram_id)
        
        # Перемещаем кого-то из резерва в основной состав
        moved_participant = self.db.move_from_reserve_to_main(event_id)
        # Пересчитываем статусы всех участников
        self.db.recalculate_participant_statuses(event_id)
        
        return {
            'success': True,
            'message': f"Группа из {group_size} человек отписана от события",
            'moved_participant': moved_participant
        } 