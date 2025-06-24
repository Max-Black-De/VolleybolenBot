from telegram import Update
from telegram.ext import ContextTypes

from utils.events_utils import event_participants
from utils.notification_utils import notify_participants, notify_all_users_about_update
from utils.keyboard_utils import create_static_keyboard
import logging



logger = logging.getLogger(__name__)
# Обработка инлайн-кнопок для первой ступени
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Распарсим callback_data, чтобы получить event_id и user_id
    data = query.data.split('_')
    action = data[0]
    event_id = int(data[2])
    user_id = int(data[3])

    # Если пользователь выбрал "Нет"
    if action == "cancel":
        participants_list = await notify_participants(event_id)
        await query.edit_message_text(f"Вы передумали!🥳\n\nСписок участников:\n{participants_list}")

    # Если пользователь выбрал "Да", переходим ко второй ступени
    elif action == "confirm":
        await query.edit_message_text(
            "Если вы точно покидаете мероприятие,😮 отправьте сообщение со словом 'да'."
            "\nЕсли передумали - отправьте слово 'нет'.🙏")

        # Сохраняем информацию о пользователе, чтобы отследить его ответ во второй ступени
        context.user_data['pending_leave_confirmation'] = {
            'event_id': event_id,
            'user_id': user_id
        }

# Обработка сообщения во второй ступени
async def handle_leave_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    user = update.message.from_user
    pending_data = context.user_data.get('pending_leave_confirmation')

    # Проверяем, есть ли подтверждение на отписку у этого пользователя
    if pending_data and pending_data['user_id'] == user.id:
        event_id = pending_data['event_id']
        if text == 'да':
            # Отписываем пользователя от события
            participants = event_participants[event_id]
            # Сохраняем текущий статус юзера для проверки
            user_participant = next((p for p in participants if p['user_id'] == user.id), None)
            updated_participants = [p for p in participants if p['user_id'] != user.id]
            event_participants[event_id] = updated_participants

            await update.message.reply_text("Вы отписались от тренировки😪\nБудем рады видеть вас на следующей!")

            # Оповещаем всех пользователей об изменении
            await update.message.reply_text("Обновлено", reply_markup=create_static_keyboard(event_id, user.id))

            # Работаем с резервными участниками
            if user_participant and user_participant['status'] != 'reserve':
                for participant in participants:
                    if participant['status'] == 'reserve':
                        participant['status'] = 'confirmed'

                        # Уведомляем пользователя, что он перемещён в основной список
                        try:
                            await context.bot.send_message(
                                chat_id=participant['user_id'],
                                text="🎉Урааа!🎉\n🤩Вы попали в основной состав, увидимся на тренировке!"
                            )
                        except Exception as e:
                            logger.error(f"Ошибка при отправке уведомления пользователю {participant['username']}: {e}")

                        # Уведомляем остальных участников
                        for other_participant in participants:
                            if other_participant['user_id'] != participant['user_id']:
                                try:
                                    await context.bot.send_message(
                                        chat_id=other_participant['user_id'],
                                        text=f"Пользователь {participant['username']} перемещён в основной состав."
                                    )
                                    await update.message.reply_text(
                                        f"Обновлённый список участников:\n{await notify_participants(event_id)}")
                                except Exception as e:
                                    logger.error(f"Ошибка при отправке уведомления другим участникам: {e}")

                        # После обновления одного резервного участника выходим из цикла
                        break

                # Оповещаем всех пользователей об изменении
                await notify_all_users_about_update(context, event_id, user.id, user.first_name, "отписался")
                await update.message.reply_text("Обновлено", reply_markup=create_static_keyboard(event_id, user.id))

        elif text == 'нет':
            await update.message.reply_text("Отписка отменена.\n🎉Урааа! Вы остаётесь с нами!🙏")

        # Удаляем данные подтверждения, чтобы завершить процесс
        del context.user_data['pending_leave_confirmation']

    else:
        # Если нет ожидающего подтверждения, продолжаем обычную обработку сообщений
        await update.message.reply_text("Неизвестная команда.")