from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from datetime import time

from handlers.message_handler import handle_leave_confirmation, handle_menu_messages
from utils.events_utils import send_time
from jobs.cleanup_job import remove_past_events
from jobs.event_scheduler import schedule_events, create_initial_event
from handlers.start_handler import start
from logging_config import setup_logging
from secure.secrets import secrets

# Логирование
setup_logging()

# Список пользователей, которые взаимодействовали с ботом
# subscribed_users = set()



if __name__ == "__main__":
    application = ApplicationBuilder().token(secrets.get('BOT_API_TOKEN')).build()

    # Обработчики команд и событий
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_menu_messages))
    application.add_handler(MessageHandler(filters.TEXT, handle_menu_messages))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^(да|нет)$'), handle_leave_confirmation))
    application.job_queue.run_daily(remove_past_events, time(hour=0, minute=1))

    # При запуске создаём событие на ближайший день
    application.job_queue.run_once(create_initial_event, 0)

    # Планируем создание событий по вторникам и четвергам в 17:00
    application.job_queue.run_daily(schedule_events, send_time, days=(2, 4))

    application.run_polling()
