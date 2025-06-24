from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

def create_main_keyboard(is_joined: bool = False) -> ReplyKeyboardMarkup:
    """Создать основную клавиатуру"""
    if is_joined:
        keyboard = [
            ["Передумал! Отписываюсь("],
            ["Список участников"]
        ]
    else:
        keyboard = [
            ["Иду на тренировку!"],
            ["Список участников"]
        ]
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def create_leave_confirmation_keyboard(event_id: int, telegram_id: int) -> InlineKeyboardMarkup:
    """Создать клавиатуру для подтверждения отписки"""
    keyboard = [
        [
            InlineKeyboardButton("Да! Отписаться", callback_data=f"confirm_leave_{event_id}_{telegram_id}"),
            InlineKeyboardButton("Вернусь на треню", callback_data=f"cancel_leave_{event_id}_{telegram_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_presence_confirmation_keyboard(event_id: int, telegram_id: int) -> InlineKeyboardMarkup:
    """Создать клавиатуру для подтверждения присутствия"""
    keyboard = [
        [
            InlineKeyboardButton("Иду", callback_data=f"confirm_presence_{event_id}_{telegram_id}"),
            InlineKeyboardButton("Не иду", callback_data=f"decline_presence_{event_id}_{telegram_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_admin_keyboard() -> ReplyKeyboardMarkup:
    """Создать клавиатуру для администраторов"""
    keyboard = [
        ["📅 Создать событие", "❌ Отменить событие"],
        ["👥 Список пользователей", "📊 Статистика"],
        ["⚙️ Настройки", "🔙 Обычный режим"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def create_event_creation_keyboard() -> ReplyKeyboardMarkup:
    """Создать клавиатуру для создания событий"""
    keyboard = [
        ["🏐 Четверг 20:00", "🏐 Воскресенье 20:00"],
        ["📅 Другая дата", "🔙 Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def create_settings_keyboard() -> ReplyKeyboardMarkup:
    """Создать клавиатуру настроек"""
    keyboard = [
        ["👥 Лимит участников", "⏰ Время напоминаний"],
        ["📅 Дни тренировок", "🔙 Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

