import logging
from telegram import Update
from telegram.ext import ContextTypes
from services.event_service import EventService
from services.notification_service import NotificationService
from db.database import Database
from utils.keyboard import create_main_keyboard
from config.settings import MESSAGES

logger = logging.getLogger(__name__)

async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                       event_service: EventService, notification_service: NotificationService, db: Database):
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
            await update.message.reply_text(f"🏐 {current_event['name']}", reply_markup=keyboard)
            
            # Отправляем приветственное сообщение
            await update.message.reply_text(MESSAGES['welcome'])
            
        else:
            # Нет активных событий
            keyboard = create_main_keyboard(is_joined=False)
            await update.message.reply_text(
                "В данный момент нет активных событий.\n" + MESSAGES['welcome'],
                reply_markup=keyboard
            )
        
        logger.info(f"Пользователь {user.username} ({user.id}) начал взаимодействие с ботом")
    
    except Exception as e:
        logger.error(f"Ошибка при обработке команды start: {e}")
        await update.message.reply_text("Произошла ошибка при запуске бота. Попробуйте позже.")
