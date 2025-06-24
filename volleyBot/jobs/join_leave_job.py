from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from utils.events_utils import event_participants, MAX_PARTICIPANTS
from utils.keyboard_utils import create_static_keyboard
from utils.notification_utils import notify_participants, notify_all_users_about_update

# Функция для записи пользователя на событие
async def join_event(update: Update, context: ContextTypes.DEFAULT_TYPE, event_id, user):
    participants = event_participants[event_id]

    if user.id in [p['user_id'] for p in participants]:
        await update.message.reply_text("Вы уже записаны.")
        return

    if len(participants) < MAX_PARTICIPANTS:
        participants.append({'user_id': user.id, 'username': user.first_name, 'status': 'confirmed'})
        await update.message.reply_text(f"Вы записаны под номером {len(participants)}.\nДобро пожаловать в основной состав!🤝")
    else:
        participants.append({'user_id': user.id, 'username': user.first_name, 'status': 'reserve'})
        await update.message.reply_text("Места закончились, вы добавлены в резерв.☕")

    await update.message.reply_text(
        f"Вы записаны на тренировку!"
        f"\n\nСписок участников:\n{await notify_participants(event_id)}")

    # Оповещаем всех пользователей об изменении
    await notify_all_users_about_update(context, event_id, user.id, user.first_name, "записался")
    await update.message.reply_text("Обновлено", reply_markup = create_static_keyboard(event_id, user.id))


# Функция для отписки пользователя от события
async def leave_event(update: Update, context: ContextTypes.DEFAULT_TYPE, event_id, user):
    participants = event_participants[event_id]

    # Если пользователь не записан на событие
    if user.id not in [p['user_id'] for p in participants]:
        await update.message.reply_text("Вы не записаны на это событие.")
        return

    # Создаем инлайн-кнопки для подтверждения
    keyboard = [
        [InlineKeyboardButton("Да", callback_data=f"confirm_leave_{event_id}_{user.id}"),
         InlineKeyboardButton("Нет", callback_data=f"cancel_leave_{event_id}_{user.id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Спрашиваем пользователя, уверен ли он
    await update.message.reply_text("Вы уверены, что не пойдёте на тренировку?", reply_markup=reply_markup)