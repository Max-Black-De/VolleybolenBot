import logging
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes
from services.event_service import EventService
from services.notification_service import NotificationService
from data.database import Database
from utils.keyboard import create_admin_keyboard, create_event_creation_keyboard, create_settings_keyboard, create_main_keyboard, create_participant_limit_keyboard, create_group_size_keyboard
from config.settings import ADMIN_IDS
from handlers.event_handler import handle_show_chat_history

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
        
        # Проверяем, записан ли пользователь на ближайшее событие
        active_events = event_service.get_active_events()
        is_joined = False
        if active_events and update.effective_user:
            # Берем первое активное событие
            next_event = active_events[0]
            participant = db.get_participant(next_event['id'], update.effective_user.id)
            is_joined = participant is not None
        
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
        await handle_settings(update, context, text, db)
    elif admin_state == 'confirm_delete':
        await handle_confirm_delete(update, context, text, event_service)
    elif admin_state == 'group_settings':
        await handle_group_settings(update, context, text, db)
    elif admin_state == 'change_group_size':
        await handle_change_group_size(update, context, text, db)
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
    elif text == "📜 История чата":
        await handle_show_chat_history(update, context, db)
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
            days_offset = (3 - datetime.now().weekday() + 7) % 7
        elif text == "🏐 Воскресенье 20:00":
            event_name_part = "Воскресенье 20:00"
            days_offset = (6 - datetime.now().weekday() + 7) % 7
        
        if event_name_part:
            target_date = datetime.now().date() + timedelta(days=days_offset)
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


async def handle_settings(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, db: Database):
    """Обработка настроек."""
    if not update.message:
        return
    user_data = context.user_data if context.user_data is not None else {}
    
    if text == "🔙 Назад":
        user_data['admin_state'] = 'main'
        await update.message.reply_text("Админское меню:", reply_markup=create_admin_keyboard())
        return
    elif text == "👥 Лимит участников":
        await show_active_events_for_limit_change(update, context)
        return
    elif text == "⏰ Время напоминаний":
        await update.message.reply_text("Функция изменения времени напоминаний в разработке.")
        return
    elif text == "📅 Дни тренировок":
        await update.message.reply_text("Функция изменения дней тренировок в разработке.")
        return
    elif text == "🎯 Запись группами":
        await show_group_registration_settings(update, context, db)
        return
    
    await update.message.reply_text("Функция настроек пока в разработке.")


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


async def show_active_events_for_limit_change(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать активные события для изменения лимита участников."""
    if not update.message:
        return
    
    from services.event_service import EventService
    from data.database import Database
    db = Database()
    event_service = EventService(db)
    active_events = event_service.get_active_events()
    
    if not active_events:
        await update.message.reply_text("Нет активных событий для изменения лимита.")
        return
    
    # Берем первое активное событие (самое ближайшее)
    event = active_events[0]
    current_limit = event['max_participants']
    
    events_text = f"📅 Событие: {event['name']}\n"
    events_text += f"👥 Текущий лимит: {current_limit} участников\n\n"
    events_text += "Выберите новый лимит участников:"
    
    user_data = context.user_data if context.user_data is not None else {}
    user_data['admin_state'] = 'change_participant_limit'
    user_data['current_event_id'] = event['id']
    
    await update.message.reply_text(events_text, reply_markup=create_participant_limit_keyboard())


async def handle_change_participant_limit(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, 
                                         event_service: EventService, notification_service: NotificationService):
    """Обработка изменения лимита участников."""
    if not update.message:
        return
    
    user_data = context.user_data if context.user_data is not None else {}
    
    if text == "🔙 Назад":
        user_data['admin_state'] = 'settings'
        await update.message.reply_text("Настройки:", reply_markup=create_settings_keyboard())
        return
    
    # Извлекаем число из текста (например, "👥 4 участника" -> 4)
    import re
    match = re.search(r'(\d+)', text)
    if match:
        new_limit = int(match.group(1))
        event_id = user_data.get('current_event_id')
        if event_id:
            event = event_service.get_event_by_id(event_id)
            if event:
                old_limit = event['max_participants']
                result = event_service.change_participant_limit(event_id, new_limit)
                
                if result['success']:
                    await update.message.reply_text(
                        f"✅ Лимит участников изменен с {old_limit} на {new_limit} для события '{event['name']}'"
                    )
                else:
                    await update.message.reply_text(f"❌ Ошибка: {result['message']}")
            else:
                await update.message.reply_text("❌ Событие не найдено.")
        else:
            await update.message.reply_text("❌ Не найдено активных событий.")
    else:
        await update.message.reply_text("❌ Неверный формат. Выберите лимит из списка.")
    
    user_data['admin_state'] = 'settings'
    await update.message.reply_text("Настройки:", reply_markup=create_settings_keyboard())


async def show_group_registration_settings(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """Показать настройки записи группами."""
    if not update.message:
        return
    
    is_enabled = db.is_group_registration_enabled()
    max_size = db.get_max_group_size()
    
    status_text = "✅ Включена" if is_enabled else "❌ Отключена"
    
    message = f"""🎯 **Настройки записи группами**

📊 **Статус:** {status_text}
👥 **Максимальный размер группы:** {max_size} человек

**Возможности:**
• Пользователи могут записываться группами (себя + дети/друзья)
• При отписке можно отписать одного или всех из группы
• Если главный участник не подтверждает присутствие - отписывается вся группа

**Управление:**
• Включить/выключить запись группами
• Изменить максимальный размер группы"""
    
    keyboard = [
        ["✅ Включить группы", "❌ Отключить группы"],
        ["👥 Изменить размер группы"],
        ["🔙 Назад"]
    ]
    from telegram import ReplyKeyboardMarkup
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    user_data = context.user_data if context.user_data is not None else {}
    user_data['admin_state'] = 'group_settings'
    
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')


async def handle_group_settings(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, db: Database):
    """Обработка настроек записи группами."""
    if not update.message:
        return
    
    user_data = context.user_data if context.user_data is not None else {}
    
    if text == "🔙 Назад":
        user_data['admin_state'] = 'settings'
        await update.message.reply_text("Настройки:", reply_markup=create_settings_keyboard())
        return
    elif text == "✅ Включить группы":
        db.set_bot_setting('group_registration_enabled', 'true')
        await update.message.reply_text("✅ Запись группами включена!")
        await show_group_registration_settings(update, context, db)
        return
    elif text == "❌ Отключить группы":
        db.set_bot_setting('group_registration_enabled', 'false')
        await update.message.reply_text("❌ Запись группами отключена!")
        await show_group_registration_settings(update, context, db)
        return
    elif text == "👥 Изменить размер группы":
        user_data['admin_state'] = 'change_group_size'
        current_size = db.get_max_group_size()
        await update.message.reply_text(
            f"👥 Введите максимальный размер группы (от 1 до 5, текущий: {current_size}):"
        )
        return
    
    await update.message.reply_text("Неизвестная команда. Выберите действие из меню.")


async def handle_change_group_size(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, db: Database):
    """Обработка изменения размера группы."""
    if not update.message:
        return
    
    user_data = context.user_data if context.user_data is not None else {}
    
    if text == "🔙 Отмена":
        user_data['admin_state'] = 'group_settings'
        await show_group_registration_settings(update, context, db)
        return
    
    # Извлекаем число из текста
    import re
    match = re.search(r'(\d+)', text)
    if match:
        new_size = int(match.group(1))
        if 1 <= new_size <= 5:  # Ограничиваем разумными пределами
            db.set_bot_setting('max_group_size', str(new_size))
            await update.message.reply_text(f"✅ Максимальный размер группы изменен на {new_size} человек!")
        else:
            await update.message.reply_text("❌ Размер группы должен быть от 1 до 5 человек.")
    else:
        await update.message.reply_text("❌ Неверный формат. Введите число от 1 до 5.")
    
    user_data['admin_state'] = 'group_settings'
    await show_group_registration_settings(update, context, db) 