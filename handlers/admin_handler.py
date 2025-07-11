import logging
from datetime import timedelta
from telegram import Update
from telegram.ext import ContextTypes
from services.event_service import EventService
from services.notification_service import NotificationService
from data.database import Database
from utils.keyboard import create_admin_keyboard, create_event_creation_keyboard, create_settings_keyboard, create_main_keyboard, get_is_joined, create_participant_limit_keyboard
from utils.timezone_utils import get_now_with_timezone
from config.settings import ADMIN_IDS

logger = logging.getLogger(__name__)


async def handle_admin_commands(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                               event_service: EventService, notification_service: NotificationService, db: Database):
    """Обработка административных команд."""
    if not update.message or not update.message.text:
        return

    user = update.effective_user
    if not user or user.id not in ADMIN_IDS:
        await update.message.reply_text("У вас нет прав администратора.")
        return

    text = update.message.text.strip()
    user_data = context.user_data if context.user_data is not None else {}
    admin_state = user_data.get('admin_state')

    if text == "/admin":
        user_data['admin_state'] = 'main'
        await update.message.reply_text(
            "Добро пожаловать в админское меню! Выберите действие:",
            reply_markup=create_admin_keyboard()
        )
        return

    if text == "🔙 Обычный режим":
        user_data.pop('admin_state', None)
        
        # Проверяем текущее состояние пользователя для правильной клавиатуры
        if not update.effective_user:
            is_joined = False
        else:
            is_joined = get_is_joined(db, event_service, update.effective_user.id)
        
        await update.message.reply_text(
            "Вы вышли из админского режима.",
            reply_markup=create_main_keyboard(is_joined=is_joined)
        )
        return

    if admin_state == 'main':
        await handle_main_admin_menu(update, context, text, event_service, db)
    elif admin_state == 'create_event':
        await handle_create_event(update, context, text, event_service, notification_service)
    elif admin_state == 'settings':
        await handle_settings(update, context, text, event_service)
    elif admin_state == 'confirm_delete':
        await handle_confirm_delete(update, context, text, event_service)
    elif admin_state == 'participant_limit':
        await handle_participant_limit(update, context, text, event_service)
    elif admin_state is None and text in [
        "📅 Создать событие", "❌ Отменить событие", "👥 Список пользователей", 
        "📊 Статистика", "⚙️ Настройки"
    ]:
         await update.message.reply_text("Пожалуйста, войдите в админ-меню снова, отправив /admin.")
    


async def handle_main_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, 
                                 event_service: EventService, db: Database):
    """Обработка главного админского меню."""
    if not update.message:
        return

    user_data = context.user_data if context.user_data is not None else {}

    if text == "📅 Создать событие":
        user_data['admin_state'] = 'create_event'
        await update.message.reply_text(
            "Выберите тип события для создания:",
            reply_markup=create_event_creation_keyboard()
        )
    elif text == "❌ Отменить событие":
        await show_active_events_for_deletion(update, context, event_service)
    elif text == "👥 Список пользователей":
        await show_users_list(update, context, db)
    elif text == "📊 Статистика":
        await show_statistics(update, context, db)
    elif text == "⚙️ Настройки":
        user_data['admin_state'] = 'settings'
        await update.message.reply_text(
            "Настройки бота:",
            reply_markup=create_settings_keyboard()
        )
    else:
        await update.message.reply_text(
            "Неизвестная админ-команда. Выберите действие:",
            reply_markup=create_admin_keyboard()
        )


async def handle_create_event(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, 
                             event_service: EventService, notification_service: NotificationService):
    """Обработка создания события."""
    if not update.message:
        return

    user_data = context.user_data if context.user_data is not None else {}

    if text == "🔙 Назад":
        user_data['admin_state'] = 'main'
        await update.message.reply_text(
            "Админское меню:",
            reply_markup=create_admin_keyboard()
        )
        return

    try:
        event_name_part = ""
        days_offset = 0
        if text == "🏐 Четверг 20:00":
            event_name_part = "Четверг 20:00"
            days_offset = (3 - get_now_with_timezone().weekday() + 7) % 7
        elif text == "🏐 Воскресенье 20:00":
            event_name_part = "Воскресенье 20:00"
            days_offset = (6 - get_now_with_timezone().weekday() + 7) % 7
        
        if event_name_part:
            target_date = get_now_with_timezone().date() + timedelta(days=days_offset)
            event_id = event_service.create_event_on_date(target_date)
            event = event_service.get_event_by_id(event_id)
            if event:
                await notification_service.send_event_notification(event_id, event['name'])
                await update.message.reply_text(f"✅ Событие создано: {event['name']}")
            else:
                 await update.message.reply_text("❌ Не удалось создать событие.")
        elif text == "📅 Другая дата":
            await update.message.reply_text("Эта функция в разработке.")

        user_data['admin_state'] = 'main'
        await update.message.reply_text("Админское меню:", reply_markup=create_admin_keyboard())

    except Exception as e:
        logger.error(f"Ошибка при создании события: {e}")
        await update.message.reply_text(f"❌ Ошибка при создании события: {e}")


async def handle_settings(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, event_service: EventService):
    """Обработка настроек."""
    if not update.message:
        return
    user_data = context.user_data if context.user_data is not None else {}
    
    if text == "🔙 Назад":
        user_data['admin_state'] = 'main'
        await update.message.reply_text("Админское меню:", reply_markup=create_admin_keyboard())
        return
    elif text == "👥 Лимит участников":
        current_limit = event_service.get_participant_limit()
        user_data['admin_state'] = 'participant_limit'
        await update.message.reply_text(
            f"Текущий лимит участников: {current_limit}\n\nВыберите новый лимит:",
            reply_markup=create_participant_limit_keyboard()
        )
        return
    
    await update.message.reply_text("Функция настроек пока в разработке.")


async def handle_participant_limit(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, event_service: EventService):
    """Обработка изменения лимита участников."""
    if not update.message:
        return
    user_data = context.user_data if context.user_data is not None else {}
    
    if text == "🔙 Назад":
        user_data['admin_state'] = 'settings'
        await update.message.reply_text("Настройки:", reply_markup=create_settings_keyboard())
        return
    
    # Парсим лимит из текста
    limit_map = {
        "4 участника": 4,
        "6 участников": 6,
        "12 участников": 12,
        "18 участников": 18,
        "24 участника": 24
    }
    
    if text in limit_map:
        new_limit = limit_map[text]
        old_limit = event_service.get_participant_limit()
        
        # Устанавливаем новый лимит
        event_service.set_participant_limit(new_limit)
        
        await update.message.reply_text(
            f"✅ Лимит участников изменен с {old_limit} на {new_limit}.\n\n"
            "Статусы участников пересчитаны автоматически."
        )
        
        # Возвращаемся в главное админское меню
        user_data['admin_state'] = 'main'
        await update.message.reply_text("Админское меню:", reply_markup=create_admin_keyboard())
    else:
        await update.message.reply_text(
            "Пожалуйста, выберите лимит из предложенных вариантов:",
            reply_markup=create_participant_limit_keyboard()
        )


async def show_active_events_for_deletion(update: Update, context: ContextTypes.DEFAULT_TYPE, event_service: EventService):
    """Показать активные события для удаления."""
    if not update.message:
        return
    
    active_events = event_service.get_active_events()
    
    if not active_events:
        await update.message.reply_text("Нет активных событий для удаления.")
        return
    
    events_text = "Активные события:\n\n" + "\n".join(
        [f"{i}. {event['name']} (ID: {event['id']})" for i, event in enumerate(active_events, 1)]
    )
    events_text += "\n\nДля удаления события введите его ID (например: 14):"
    
    user_data = context.user_data if context.user_data is not None else {}
    user_data['admin_state'] = 'confirm_delete'
    user_data['active_events_for_deletion'] = active_events
    
    await update.message.reply_text(events_text)


async def handle_confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, event_service: EventService):
    """Обработка подтверждения удаления события по ID."""
    if not update.message:
        return
    try:
        event_id = int(text)
        user_data = context.user_data if context.user_data is not None else {}
        active_events = user_data.get('active_events_for_deletion', [])
        event_to_delete = next((event for event in active_events if event['id'] == event_id), None)
        if event_to_delete:
            event_service.delete_event(event_to_delete['id'])
            await update.message.reply_text(f"✅ Событие '{event_to_delete['name']}' удалено.")
        else:
            events_text = "❌ Неверный ID события.\n\nДоступные события:\n" + "\n".join(
                [f"{event['name']} (ID: {event['id']})" for event in active_events]
            )
            await update.message.reply_text(events_text)
    except (ValueError, TypeError):
        await update.message.reply_text("❌ Введите корректный ID события (например: 14)")
    user_data = context.user_data if context.user_data is not None else {}
    user_data['admin_state'] = 'main'
    await update.message.reply_text("Админское меню:", reply_markup=create_admin_keyboard())


async def show_users_list(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """Показать список пользователей."""
    if not update.message:
        return
    
    users = db.get_all_users()
    
    if not users:
        await update.message.reply_text("В базе данных нет пользователей.")
        return
    
    users_text = f"Все пользователи ({len(users)}):\n\n"
    users_list = []
    for i, user in enumerate(users[:20], 1):
        username = f"@{user['username']}" if user['username'] else "Нет username"
        users_list.append(f"{i}. {user['first_name']} ({username}) - ID: {user['telegram_id']}")

    users_text += "\n".join(users_list)
    
    if len(users) > 20:
        users_text += f"\n\n... и еще {len(users) - 20} пользователей."
    
    await update.message.reply_text(users_text)


async def show_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """Показать статистику пользователей и событий, а также количество участников на ближайшее событие."""
    if not update.message:
        return
    total_users = db.get_total_users_count()
    active_events = db.get_active_events()
    total_active_events = len(active_events)
    participants_count = 0
    if active_events:
        event_id = active_events[0]['id']
        participants = db.get_event_participants(event_id)
        participants_count = len(participants)
    stat_text = (
        f"Всего пользователей: {total_users}\n"
        f"Активных событий: {total_active_events}\n"
        f"Записано на ближайшее событие: {participants_count} спортсменов"
    )
    await update.message.reply_text(stat_text) 