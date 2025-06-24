from telegram.ext import ContextTypes
from logging import getLogger
from utils.events_utils import event_participants
from handlers.start_handler import subscribed_users


logger = getLogger(__name__)

# Функция для отправки приглашений пользователям
async def send_invitation_to_all(context: ContextTypes.DEFAULT_TYPE, event_id, event_name):
    for chat_id in subscribed_users:
        try:
            await context.bot.send_message(chat_id = chat_id, text = f"Новое событие:\n{event_name}!")
            logger.info(f"Приглашение на событие {event_name} отправлено пользователю {chat_id}.")
        except Exception as e:
            logger.error(f"Ошибка при отправке приглашения пользователю {chat_id}: {e}")

# Функция для уведомления всех пользователей об изменениях в записи на тренировку
async def notify_all_users_about_update(context: ContextTypes.DEFAULT_TYPE, event_id, userId, first_name, action):
    participants = await notify_participants(event_id)
    message_text = f"Пользователь {first_name} {action}.\n\nТекущий список участников:\n{participants}"

    for chat_id in subscribed_users:
        # Исключаем пользователя, который инициировал действие
        if chat_id == userId:
            continue  # Пропускаем уведомление для инициатора
        try:
            await context.bot.send_message(chat_id=chat_id, text=message_text)
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления пользователю {chat_id}: {e}")

# Функция для уведомления всех участников о событии
async def notify_participants(event_id):
    participants = event_participants[event_id]
    if not participants:
        return "Ещё никто не записался! Будь первым!"
    messages = []

    for idx, participant in enumerate(participants):
        status = "Резерв" if participant['status'] == 'reserve' else "Основной"
        messages.append(f"{idx + 1}. {participant['username']} - {status}")

    return "\n".join(messages)