from typing import Optional
import logging
from telegram import Update
from telegram.ext import ContextTypes
from services.event_service import EventService
from services.notification_service import NotificationService
from services.chat_history_service import ChatHistoryService
from data.database import Database
from utils.keyboard import create_main_keyboard
from config.settings import MESSAGES

logger = logging.getLogger(__name__)

async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                       event_service: EventService, notification_service: NotificationService, 
                       db: Database, chat_history_service: Optional[ChatHistoryService] = None):
    """Обработчик команды /start"""
    if not update.message:
        return
        
    user = update.effective_user
    if not user:
        return
        
    try:
        # Добавляем пользователя в базу данных
        db.add_user(user.id, user.username, user.first_name, user.last_name)
        
        # Получаем активные события
        active_events = event_service.get_active_events()
        
        if active_events:
            # Берем первое активное событие
            current_event = active_events[0]
            event_id = current_event['id']
            
            # Проверяем, записан ли пользователь
            participant = db.get_participant(event_id, user.id)
            is_joined = participant is not None
            
            # Создаем клавиатуру
            keyboard = create_main_keyboard(is_joined=is_joined)
            
            # Отправляем информацию о событии
            event_message = f"🏐 {current_event['name']}"
            await update.message.reply_text(event_message, reply_markup=keyboard)
            
            # Сохраняем сообщение бота в историю
            if chat_history_service:
                chat_history_service.save_bot_message(user.id, event_message, event_id)
            
            # Отправляем приветственное сообщение
            welcome_message = MESSAGES['welcome']
            await update.message.reply_text(welcome_message)
            
            # Сохраняем приветственное сообщение в историю
            if chat_history_service:
                chat_history_service.save_bot_message(user.id, welcome_message)
            
        else:
            # Нет активных событий
            keyboard = create_main_keyboard(is_joined=False)
            no_events_message = "В данный момент нет активных событий.\n" + MESSAGES['welcome']
            await update.message.reply_text(no_events_message, reply_markup=keyboard)
            
            # Сохраняем сообщение бота в историю
            if chat_history_service:
                chat_history_service.save_bot_message(user.id, no_events_message)
        
        logger.info(f"Пользователь {user.username} ({user.id}) начал взаимодействие с ботом")
    
    except Exception as e:
        logger.error(f"Ошибка при обработке команды start: {e}")
        error_message = "Произошла ошибка при запуске бота. Попробуйте позже."
        await update.message.reply_text(error_message)
        
        # Сохраняем сообщение об ошибке в историю
        if chat_history_service:
            chat_history_service.save_bot_message(user.id, error_message)
