from telegram.ext import ContextTypes
from datetime import datetime
from logging import getLogger

from utils.events_utils import event_ids, event_participants

logger = getLogger(__name__)


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
        # logger.info(f"Удаление события {event_ids[event_id]} с ID: {event_id}")
        del event_participants[event_id]  # Удаляем участников события
        del event_ids[event_id]  # Удаляем само событие