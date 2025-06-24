from telebot.asyncio_helper import send_message
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from datetime import datetime, timedelta, time
import logging
import locale
import pytz
from secure import secrets

# Устанавливаем локаль на русский язык для вывода даты
locale.setlocale(locale.LC_TIME, 'C') # Локали
timezone = pytz.timezone('Europe/Yekaterinburg')

# Логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Словари для хранения информации
event_participants = {}
event_ids = {}
event_id_counter = 1
subscribed_users = set()  # Список пользователей, которые взаимодействовали с ботом
MAX_PARTICIPANTS = 18  # Лимит на количество участников тренировки
TOKEN = secrets.get('BOT_API_TOKEN')
send_time = time(17, 0, tzinfo=timezone)

# Функция для создания события на конкретную дату
def create_event_on_date(target_date):
    global event_id_counter
    event_name = f"\n\nЗапись на тренировку по волейболу \n{target_date.strftime('%A %d %B')} в 20:00"
    event_id = event_id_counter
    event_participants[event_id] = []
    event_ids[event_id] = event_name

    logger.info(f"Создано событие: {event_name} с ID: {event_id}")

    event_id_counter += 1
    return event_id, event_name

# Функция для удаления старых событий и очистки списка спортсменов
async def remove_past_events(context: ContextTypes.DEFAULT_TYPE):
    current_date = datetime.now().date()
    events_to_remove = []

    for event_id, event_name in event_ids.items():
        # Извлекаем дату события из имени события
        event_date_str = event_name.split()[3:5]  # Получаем дату как строку из имени события
        event_date = datetime.strptime(" ".join(event_date_str), '%d %B').date()

        if event_date < current_date:  # Если дата события уже прошла
            events_to_remove.append(event_id)

    for event_id in events_to_remove:
        logger.info(f"Удаление события {event_ids[event_id]} с ID: {event_id}")
        del event_participants[event_id]  # Удаляем участников события
        del event_ids[event_id]  # Удаляем само событие

# Функция для определения ближайшего тренировочного дня
def get_next_training_day():
    today = datetime.now().date()
    weekday = today.weekday()

    if weekday < 3:  # Понедельник-среда: ближайший четверг
        delta_days = 3 - weekday  # Четверг - день недели 3
    elif weekday < 6:  # Четверг-суббота: ближайшее воскресенье
        delta_days = 6 - weekday  # Воскресенье - день недели 6
    else:  # Если сегодня воскресенье, то следующий четверг
        delta_days = 4

    next_training_date = today + timedelta(days=delta_days)
    return next_training_date

# Функция для отправки приглашений пользователям
async def send_invitation_to_all(context: ContextTypes.DEFAULT_TYPE, event_id, event_name):
    for chat_id in subscribed_users:
        try:
            await context.bot.send_message(chat_id = chat_id, text = f"Новое событие:\n{event_name}!")
            logger.info(f"Приглашение на событие {event_name} отправлено пользователю {chat_id}.")
        except Exception as e:
            logger.error(f"Ошибка при отправке приглашения пользователю {chat_id}: {e}")


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

# Функция для обработки текстовых сообщений от пользователей
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.message.from_user
    event_id = next(iter(event_participants))  # Получаем первый доступный ID события (или добавьте вашу логику)
    pending_data = context.user_data.get('pending_leave_confirmation')

    # Логируем сообщение
    logger.info(f"Пользователь {user.first_name} отправил сообщение: {text}")

    if pending_data and pending_data['user_id'] == user.id:
        await handle_leave_confirmation(update, context)
        return

    if text == "Иду на тренировку!":
        # Записываем пользователя на тренировку
        await join_event(update, context, event_id, user)
    elif text == "Передумал! Отписываюсь(":
        # Отписываем пользователя от тренировки
        await leave_event(update, context, event_id, user)
    elif text == "Список участников":
        # Показываем список участников
        participants_list = await notify_participants(event_id)
        await update.message.reply_text(f"Список участников:\n{participants_list}")
    else:
        # Если сообщение не распознано, отвечаем по умолчанию
        await update.message.reply_text("Неизвестная команда. Используйте кнопки для выбора действия.")

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

# Новая функция Start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    event_id = next(iter(event_participants))
    subscribed_users.add(chat_id)  # Добавляем пользователя в список взаимодействующих
    logger.info(f"Пользователь {chat_id} начал взаимодействие с ботом.")
    reply_markup = create_static_keyboard(event_id, chat_id)

    # Если событие уже создано, отправляем пользователю информацию о нём
    for event_id, event_name in event_ids.items():
        await update.message.reply_text(f"Новое событие: {event_name}", reply_markup=reply_markup)

    # Отправляем сообщение с меню
    await update.message.reply_text("Выберите действие:", reply_markup=reply_markup)


# Функция для создания события по расписанию
async def schedule_events(context: ContextTypes.DEFAULT_TYPE):
    next_training_day = get_next_training_day()
    event_id, event_name = create_event_on_date(next_training_day)
    await send_invitation_to_all(context, event_id, event_name)


# Функция для создания первого события на ближайший день
async def create_initial_event(context: ContextTypes.DEFAULT_TYPE):
    next_training_day = get_next_training_day()
    event_id, event_name = create_event_on_date(next_training_day)
    await send_invitation_to_all(context, event_id, event_name)


if __name__ == "__main__":
    application = ApplicationBuilder().token(TOKEN).build()

    # Обработчики команд и событий
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT, handle_message))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^(да|нет)$'), handle_leave_confirmation))
    application.job_queue.run_daily(remove_past_events, time(hour=0, minute=1))

    # При запуске создаём событие на ближайший день
    application.job_queue.run_once(create_initial_event, 0)

    # Планируем создание событий по вторникам и четвергам в 17:00
    application.job_queue.run_daily(schedule_events, send_time, days=(2, 4))

    application.run_polling()
