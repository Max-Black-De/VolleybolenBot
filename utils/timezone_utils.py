import pytz
from datetime import datetime

def get_now_with_timezone():
    """Получить текущее время с учетом таймзоны GMT+5 (Asia/Yekaterinburg)"""
    # Всегда используем Asia/Yekaterinburg для GMT+5
    tz = pytz.timezone('Asia/Yekaterinburg')
    return datetime.now(tz) 