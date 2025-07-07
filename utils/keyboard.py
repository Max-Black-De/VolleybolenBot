from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
import logging

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
        ["⚙️ Настройки", "📜 История чата"],
        ["🔙 Обычный режим"]
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
        ["📅 Дни тренировок", "🎯 Запись группами"],
        ["🔙 Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def create_participant_limit_keyboard() -> ReplyKeyboardMarkup:
    """Создать клавиатуру для выбора лимита участников"""
    keyboard = [
        ["👥 4 участника", "👥 6 участников", "👥 12 участников"],
        ["👥 18 участников", "👥 24 участника"],
        ["🔙 Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def create_group_size_keyboard(max_group_size: int = 3) -> ReplyKeyboardMarkup:
    """Создать клавиатуру для выбора размера группы"""
    keyboard = []
    
    # Первая строка: "1 человек"
    keyboard.append(["👤 1 человек"])
    
    # Добавляем кнопки +1, +2, +3 в зависимости от max_group_size
    if max_group_size >= 2:
        keyboard.append(["👥 +1"])  # для записи 2 человек
    
    if max_group_size >= 3:
        keyboard.append(["👥 +2"])  # для записи 3 человек
    
    if max_group_size >= 4:
        keyboard.append(["👥 +3"])  # для записи 4 человек
    
    # Кнопка отмены
    keyboard.append(["🔙 Отмена"])
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def create_group_leave_keyboard() -> ReplyKeyboardMarkup:
    """Создать клавиатуру для отписки группы"""
    keyboard = [
        ["👤 Отписать одного", "👥 Отписать всех"],
        ["🔙 Отмена"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def create_partial_leave_keyboard(group_size: int, max_group_size: int = 3) -> InlineKeyboardMarkup:
    """Создать клавиатуру для частичной отписки группы"""
    logger = logging.getLogger(__name__)
    
    keyboard = []
    
    # Добавляем кнопки для отписки 1, 2, ... N человек (но не больше размера группы и max_group_size)
    max_leave = min(group_size, max_group_size)
    for i in range(1, max_leave + 1):
        keyboard.append([
            InlineKeyboardButton(f"Отписаться {i} чел.", callback_data=f"leave_partial_{i}")
        ])
    
    # Кнопка для отписки всей группы только если group_size > max_group_size
    if group_size > max_group_size:
        keyboard.append([
            InlineKeyboardButton("Отписаться всей группой", callback_data="leave_group_all")
        ])
    
    # Кнопка отмены - просто сворачивает клавиатуру
    keyboard.append([InlineKeyboardButton("Отмена", callback_data="cancel")])
    
    
    
    return InlineKeyboardMarkup(keyboard)

def create_leave_confirmation_keyboard(event_id: int, telegram_id: int) -> InlineKeyboardMarkup:
    """Создать клавиатуру для подтверждения отписки"""
    keyboard = [
        [
            InlineKeyboardButton("Да! Отписаться", callback_data=f"confirm_leave_{event_id}_{telegram_id}"),
            InlineKeyboardButton("Вернусь на треню", callback_data=f"cancel_leave_{event_id}_{telegram_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

