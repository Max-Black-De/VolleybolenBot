import logging
from typing import List, Dict, Optional
from data.database import Database

logger = logging.getLogger(__name__)

class ChatHistoryService:
    def __init__(self, database: Database):
        self.db = database
    
    def save_user_message(self, telegram_id: int, message_text: str, event_id: Optional[int] = None):
        """Сохранить сообщение пользователя"""
        try:
            self.db.save_message(telegram_id, message_text, 'user', event_id)
            logger.debug(f"Сохранено сообщение пользователя {telegram_id}: {message_text[:50]}...")
        except Exception as e:
            logger.error(f"Ошибка при сохранении сообщения пользователя: {e}")
    
    def save_bot_message(self, telegram_id: int, message_text: str, event_id: Optional[int] = None):
        """Сохранить сообщение бота"""
        try:
            self.db.save_message(telegram_id, message_text, 'bot', event_id)
            logger.debug(f"Сохранено сообщение бота для {telegram_id}: {message_text[:50]}...")
        except Exception as e:
            logger.error(f"Ошибка при сохранении сообщения бота: {e}")
    
    def save_system_message(self, telegram_id: int, message_text: str, event_id: Optional[int] = None):
        """Сохранить системное сообщение"""
        try:
            self.db.save_message(telegram_id, message_text, 'system', event_id)
            logger.debug(f"Сохранено системное сообщение для {telegram_id}: {message_text[:50]}...")
        except Exception as e:
            logger.error(f"Ошибка при сохранении системного сообщения: {e}")
    
    def get_user_history(self, telegram_id: int, limit: int = 50) -> List[Dict]:
        """Получить историю чата пользователя"""
        try:
            return self.db.get_chat_history(telegram_id, limit)
        except Exception as e:
            logger.error(f"Ошибка при получении истории чата: {e}")
            return []
    
    def get_recent_history(self, telegram_id: int, hours: int = 24) -> List[Dict]:
        """Получить недавнюю историю чата"""
        try:
            return self.db.get_recent_chat_history(telegram_id, hours)
        except Exception as e:
            logger.error(f"Ошибка при получении недавней истории: {e}")
            return []
    
    def format_history_for_display(self, history: List[Dict]) -> str:
        """Форматировать историю для отображения"""
        if not history:
            return "История чата пуста."
        
        # Сортируем по времени (от старых к новым)
        sorted_history = sorted(history, key=lambda x: x['created_at'])
        
        lines = ["📜 История чата:"]
        for msg in sorted_history:
            timestamp = msg['created_at']
            if isinstance(timestamp, str):
                # Убираем время из timestamp для краткости
                time_part = timestamp.split(' ')[1][:5] if ' ' in timestamp else timestamp[:5]
            else:
                time_part = str(timestamp)[:5]
            
            message_type = msg['message_type']
            text = msg['message_text']
            
            if message_type == 'user':
                lines.append(f"👤 [{time_part}] Вы: {text}")
            elif message_type == 'bot':
                lines.append(f"🤖 [{time_part}] Бот: {text}")
            else:
                lines.append(f"⚙️ [{time_part}] Система: {text}")
        
        return "\n".join(lines)
    
    def clear_user_history(self, telegram_id: int):
        """Очистить историю пользователя"""
        try:
            self.db.clear_chat_history(telegram_id)
            logger.info(f"История чата пользователя {telegram_id} очищена")
        except Exception as e:
            logger.error(f"Ошибка при очистке истории: {e}")
    
    def get_history_stats(self, telegram_id: int) -> Dict:
        """Получить статистику истории чата"""
        try:
            total_messages = self.db.get_chat_history_count(telegram_id)
            recent_history = self.get_recent_history(telegram_id, 24)
            
            user_messages = len([msg for msg in recent_history if msg['message_type'] == 'user'])
            bot_messages = len([msg for msg in recent_history if msg['message_type'] == 'bot'])
            
            return {
                'total_messages': total_messages,
                'recent_user_messages': user_messages,
                'recent_bot_messages': bot_messages,
                'recent_total': len(recent_history)
            }
        except Exception as e:
            logger.error(f"Ошибка при получении статистики: {e}")
            return {'total_messages': 0, 'recent_user_messages': 0, 'recent_bot_messages': 0, 'recent_total': 0} 