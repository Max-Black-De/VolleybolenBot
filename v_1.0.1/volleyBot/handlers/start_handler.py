from telegram.ext import ContextTypes
from telegram import Update
from logging import getLogger
from utils.events_utils import get_current_event
from utils.keyboard_utils import create_static_keyboard

logger = getLogger(__name__)

# Список пользователей, которые взаимодействовали с ботом
subscribed_users = set()

# Функция Start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    subscribed_users.add(chat_id)  # Добавляем пользователя в список взаимодействующих
    event_id, event_name = get_current_event()
    logger.info(f"Пользователь {chat_id} начал взаимодействие с ботом.")
    reply_markup = create_static_keyboard(event_id, chat_id)
    await update.message.reply_text(f"Новое событие: {event_name}", reply_markup=reply_markup)
    await update.message.reply_text("Выберите действие:", reply_markup=reply_markup)




    # Если событие уже создано, отправляем пользователю информацию о нём
    # for event_id, event_name in event_ids.items():
    #     await update.message.reply_text(f"Новое событие: {event_name}", reply_markup=reply_markup)

    # Отправляем сообщение с меню
    # await update.message.reply_text("Выберите действие:", reply_markup=reply_markup)