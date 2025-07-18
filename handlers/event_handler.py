import logging
from telegram import Update
from telegram.ext import ContextTypes
from services.event_service import EventService
from services.notification_service import NotificationService
from data.database import Database
from utils.keyboard import create_main_keyboard, create_leave_confirmation_keyboard, get_is_joined
from config.settings import MESSAGES

logger = logging.getLogger(__name__)

async def handle_event_actions(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, 
                              event_service: EventService, notification_service: NotificationService, db: Database):
    """Обработка основных действий с событиями"""
    if not update.message:
        return
        
    user = update.effective_user
    if not user:
        return
        
    text = text.strip()
    
    # Получаем активное событие
    active_events = event_service.get_active_events()
    if not active_events:
        await update.message.reply_text("В данный момент нет активных событий.")
        return
    
    # Берем первое активное событие
    current_event = active_events[0]
    event_id = current_event['id']
    
    # Удаляю все старые проверки статуса пользователя, оставляю только get_is_joined
    
    if text == "Иду на тренировку!":
        is_joined = get_is_joined(db, event_service, user.id)
        if is_joined:
            await update.message.reply_text(
                "Вы уже записаны на это событие.",
                reply_markup=create_main_keyboard(is_joined=True)
            )
            return
        await handle_join_event(update, context, event_service, notification_service, db, event_id, user)
    
    elif text == "Передумал! Отписываюсь(":
        is_joined = get_is_joined(db, event_service, user.id)
        if not is_joined:
            await update.message.reply_text(
                "Вы не записаны на это событие.",
                reply_markup=create_main_keyboard(is_joined=False)
            )
            return
        await handle_leave_event(update, context, event_service, notification_service, event_id, user)
    
    elif text == "Список участников":
        await handle_show_participants(update, context, event_service, event_id)
    
    else:
        # Обновляем клавиатуру в соответствии с текущим состоянием
        await update_main_keyboard(update, db, event_service, user)

async def handle_join_event(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                           event_service: EventService, notification_service: NotificationService, 
                           db: Database, event_id: int, user):
    """Обработка записи на событие"""
    if not update.message:
        return
        
    try:
        result = event_service.join_event(
            event_id, 
            user.id, 
            user.username, 
            user.first_name, 
            user.last_name
        )
        
        if result['success']:
            # Сразу подтверждаем присутствие
            event_service.confirm_presence(event_id, user.id)
            
            await update.message.reply_text(result['message'] + "\n\n✅ Ваше присутствие подтверждено!")
            
            # Получаем информацию о событии
            event_info = event_service.get_event_by_id(event_id)
            
            # Показываем список участников
            participants_list = event_service.get_participants_list(event_id, event_info)
            await update.message.reply_text(participants_list)
            
            # Уведомляем всех об изменении
            await notification_service.send_participants_update(
                event_id, user.id, user.username or f"Пользователь {user.id}", "записался"
            )
            
            # Проверяем актуальное состояние пользователя и обновляем клавиатуру
            is_joined = get_is_joined(db, event_service, user.id)
            
            await update.message.reply_text(
                "Обновлено", 
                reply_markup=create_main_keyboard(is_joined=is_joined)
            )
        else:
            # Проверяем актуальное состояние пользователя
            is_joined = get_is_joined(db, event_service, user.id)
            
            await update.message.reply_text(
                result['message'],
                reply_markup=create_main_keyboard(is_joined=is_joined)
            )
    
    except Exception as e:
        logger.error(f"Ошибка при записи на событие: {e}", exc_info=True)
        await notification_service.send_error_notification(user.id, "Ошибка при записи на событие")

async def handle_leave_event(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                            event_service: EventService, notification_service: NotificationService, 
                            event_id: int, user):
    """Обработка отписки от события"""
    if not update.message:
        return
        
    try:
        # Создаем клавиатуру для подтверждения
        keyboard = create_leave_confirmation_keyboard(event_id=event_id, telegram_id=user.id)
        
        await update.message.reply_text(
            MESSAGES['leave_confirmation'],
            reply_markup=keyboard
        )
    
    except Exception as e:
        logger.error(f"Ошибка при отписке от события: {e}", exc_info=True)
        await notification_service.send_error_notification(user.id, "Ошибка при отписке от события")

async def handle_show_participants(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                  event_service: EventService, event_id: int):
    """Показать список участников"""
    if not update.message:
        return
        
    try:
        # Получаем информацию о событии
        event_info = event_service.get_event_by_id(event_id)
        
        participants_list = event_service.get_participants_list(event_id, event_info)
        await update.message.reply_text(participants_list)
    
    except Exception as e:
        logger.error(f"Ошибка при показе списка участников: {e}", exc_info=True)
        await update.message.reply_text("Ошибка при получении списка участников") 

async def update_main_keyboard(update: Update, db: Database, event_service: EventService, user):
    """Обновить главную клавиатуру в соответствии с текущим состоянием пользователя"""
    if not update.message:
        return
        
    try:
        # Проверяем актуальное состояние пользователя
        is_joined = get_is_joined(db, event_service, user.id)
        # Обновляем клавиатуру
        await update.message.reply_text(
            "Клавиатура обновлена", 
            reply_markup=create_main_keyboard(is_joined=is_joined)
        )
    except Exception as e:
        logger.error(f"Ошибка при обновлении клавиатуры: {e}", exc_info=True) 