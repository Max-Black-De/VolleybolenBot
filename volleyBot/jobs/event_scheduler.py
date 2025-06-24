from telegram.ext import ContextTypes
from utils.events_utils import create_event_on_date, get_next_training_day
from utils.notification_utils import send_invitation_to_all

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