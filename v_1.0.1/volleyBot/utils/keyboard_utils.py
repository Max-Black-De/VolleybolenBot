from telegram.ext import ContextTypes
from telegram import ReplyKeyboardMarkup, Update

from utils.events_utils import event_participants
from logging import getLogger

logger = getLogger(__name__)
# Функция для создания статической клавиатуры
def create_static_keyboard(event_id, chat_id):
    # Получаем список участников для данного события
    participants = event_participants.get(event_id, [])  # Используем правильный ID события

    # Проверяем, записан ли пользователь в список участников
    if any(p['user_id'] == chat_id for p in participants):
        dynamic_button_text = "Передумал! Отписываюсь("  # Если записан, изменяем текст
    else:
        dynamic_button_text = "Иду на тренировку!"  # По умолчанию

    # Создаём клавиатуру с динамической кнопкой
    keyboard = [
        [dynamic_button_text],
        ["Список участников"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

