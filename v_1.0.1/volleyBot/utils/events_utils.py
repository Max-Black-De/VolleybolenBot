from datetime import datetime, timedelta, time
from logging import getLogger
import locale
import pytz

logger = getLogger(__name__)

# Устанавливаем локаль на русский язык для вывода даты
locale.setlocale(locale.LC_ALL) # Локали
timezone = pytz.timezone('Asia/Yekaterinburg')

# Словари для хранения информации
event_participants = {}
event_ids = {}
event_id_counter = 1
send_time = time(17, 0, tzinfo=timezone)
# subscribed_users = set()  # Список пользователей, которые взаимодействовали с ботом

# Лимит на кол-во участников тренировки
MAX_PARTICIPANTS = 18

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

# Функция для получения текущего события
def get_current_event():
    event_id = next(iter(event_participants))  # Логика выбора события
    return event_id, event_ids[event_id]

