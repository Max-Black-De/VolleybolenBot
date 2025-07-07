import logging
import asyncio
from typing import List, Dict
from telegram import Bot
from data.database import Database
from config.settings import MESSAGES

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self, bot: Bot, database: Database):
        self.bot = bot
        self.db = database
    
    async def send_event_notification(self, event_id: int, event_name: str):
        """Отправить уведомление о новом событии всем подписанным пользователям"""
        subscribed_users = self.db.get_subscribed_users()
        
        for telegram_id in subscribed_users:
            try:
                await self.bot.send_message(
                    chat_id=telegram_id,
                    text=f"🏐 Новое событие:\n{event_name}"
                )
                logger.info(f"Уведомление о событии {event_id} отправлено пользователю {telegram_id}")
                # Добавляем задержку между сообщениями
                await asyncio.sleep(0.1)
            except Exception as e:
                error_msg = str(e).lower()
                if "blocked" in error_msg or "forbidden" in error_msg:
                    logger.warning(f"Пользователь {telegram_id} заблокировал бота")
                    # Можно отписать пользователя от уведомлений
                    self.db.update_user_subscription(telegram_id, False)
                elif "chat not found" in error_msg:
                    logger.warning(f"Чат с пользователем {telegram_id} не найден")
                    self.db.update_user_subscription(telegram_id, False)
                else:
                    logger.error(f"Ошибка при отправке уведомления пользователю {telegram_id}: {e}")
    
    async def send_participants_update(self, event_id: int, action_user_id: int, action_username: str, action: str):
        """Отправить уведомление об изменении списка участников"""
        from services.event_service import EventService
        event_service = EventService(self.db)
        
        # Получаем информацию о событии
        event_info = event_service.get_event_by_id(event_id)
        
        participants_list = event_service.get_participants_list(event_id, event_info)
        message = f"Пользователь {action_username} {action}.\n\n{participants_list}"
        
        subscribed_users = self.db.get_subscribed_users()
        
        for telegram_id in subscribed_users:
            if telegram_id == action_user_id:
                continue  # Пропускаем пользователя, который инициировал действие
            
            try:
                await self.bot.send_message(chat_id=telegram_id, text=message)
                logger.info(f"Уведомление об изменении отправлено пользователю {telegram_id}")
            except Exception as e:
                logger.error(f"Ошибка при отправке уведомления пользователю {telegram_id}: {e}")
    
    async def send_moved_to_main_notification(self, telegram_id: int, username: str):
        """Отправить уведомление о перемещении из резерва в основной состав"""
        try:
            await self.bot.send_message(
                chat_id=telegram_id,
                text=MESSAGES['moved_to_main']
            )
            logger.info(f"Уведомление о перемещении в основной состав отправлено пользователю {telegram_id}")
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления о перемещении пользователю {telegram_id}: {e}")
    
    async def send_presence_reminder(self, event_id: int, telegram_id: int, event_name: str, reminder_type: str = 'first'):
        """Отправить напоминание о подтверждении присутствия"""
        from utils.keyboard import create_presence_confirmation_keyboard
        
        if reminder_type == 'first':
            message = MESSAGES['presence_reminder']
        else:
            message = MESSAGES['second_reminder']
        
        keyboard = create_presence_confirmation_keyboard(event_id, telegram_id)
        
        try:
            await self.bot.send_message(
                chat_id=telegram_id,
                text=f"{message}\n\n{event_name}",
                reply_markup=keyboard
            )
            logger.info(f"Напоминание о присутствии отправлено пользователю {telegram_id}")
        except Exception as e:
            logger.error(f"Ошибка при отправке напоминания пользователю {telegram_id}: {e}")
    
    async def send_auto_leave_notification(self, telegram_id: int, event_name: str):
        """Отправить уведомление об автоматической отписке"""
        try:
            await self.bot.send_message(
                chat_id=telegram_id,
                text=f"{MESSAGES['auto_leave']}\n\n{event_name}"
            )
            logger.info(f"Уведомление об автоматической отписке отправлено пользователю {telegram_id}")
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления об отписке пользователю {telegram_id}: {e}")
    
    async def send_no_reserve_notification(self, event_id: int):
        """Отправить уведомление о том, что в резерве никого нет"""
        subscribed_users = self.db.get_subscribed_users()
        event = self.db.get_event_by_id(event_id)
        
        if not event:
            return
        
        message = f"{MESSAGES['no_reserve']}\n\n{event['name']}"
        
        for telegram_id in subscribed_users:
            try:
                await self.bot.send_message(chat_id=telegram_id, text=message)
                logger.info(f"Уведомление об отсутствии резерва отправлено пользователю {telegram_id}")
            except Exception as e:
                logger.error(f"Ошибка при отправке уведомления пользователю {telegram_id}: {e}")
    
    async def send_admin_notification(self, admin_id: int, message: str):
        """Отправить уведомление администратору"""
        try:
            await self.bot.send_message(chat_id=admin_id, text=message)
            logger.info(f"Админ уведомление отправлено: {admin_id}")
        except Exception as e:
            logger.error(f"Ошибка при отправке админ уведомления {admin_id}: {e}")
    
    async def send_error_notification(self, telegram_id: int, error_message: str):
        """Отправить уведомление об ошибке"""
        try:
            await self.bot.send_message(
                chat_id=telegram_id,
                text=f"❌ Произошла ошибка: {error_message}\n\nПопробуйте позже или обратитесь к администратору."
            )
            logger.error(f"Уведомление об ошибке отправлено пользователю {telegram_id}: {error_message}")
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления об ошибке пользователю {telegram_id}: {e}") 