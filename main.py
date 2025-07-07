import logging
import locale
import pytz
import asyncio
from datetime import datetime, time
from typing import Optional, Dict, Any
from telegram import Update, User
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

from config.secure import secrets
from config.settings import BOT_SETTINGS, MESSAGES, ADMIN_IDS
from data.database import Database
from services.event_service import EventService
from services.notification_service import NotificationService
from services.chat_history_service import ChatHistoryService
from utils.keyboard import create_main_keyboard
from handlers.start_handler import handle_start
from handlers.event_handler import handle_event_actions
from handlers.admin_handler import handle_admin_commands

# Устанавливаем локаль на русский язык для вывода даты
locale.setlocale(locale.LC_TIME, 'C')

# Логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация компонентов
TOKEN = secrets.get('BOT_API_TOKEN')
if not TOKEN or not isinstance(TOKEN, str):
    raise ValueError("BOT_API_TOKEN не найден или неверного типа в config/secure.py")

db = Database()
event_service = EventService(db)

class VolleyballBot:
    def __init__(self):
        # TOKEN уже проверен выше, поэтому здесь он точно str
        self.application = ApplicationBuilder().token(str(TOKEN)).build()
        self.db = Database()
        self.event_service = EventService(self.db)
        self.notification_service = NotificationService(self.application.bot, self.db)
        self.chat_history_service = ChatHistoryService(self.db)
        
    def setup_handlers(self):
        """Настройка обработчиков"""

        
        # Основные команды
        self.application.add_handler(CommandHandler("start", self.start_handler))
        logger.info("Добавлен обработчик CommandHandler для /start")
        
        self.application.add_handler(CommandHandler("admin", self.admin_handler))
        logger.info("Добавлен обработчик CommandHandler для /admin")
        
        # Обработка инлайн-кнопок
        self.application.add_handler(CallbackQueryHandler(self.callback_handler))
        logger.info("Добавлен обработчик CallbackQueryHandler")
        
        # Обработка текстовых сообщений
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.message_handler))
        logger.info("Добавлен обработчик MessageHandler для текстовых сообщений")
        


    def setup_jobs(self):
        """Настройка планировщика задач"""
        job_queue = self.application.job_queue
        if not job_queue:
            logger.warning("Job queue недоступен")
            return
        
        # Настраиваем часовой пояс
        timezone = pytz.timezone(BOT_SETTINGS['TIMEZONE_NAME'])
        
        # Создание событий по расписанию (вторник и пятница в 17:00)
        job_queue.run_daily(
            self.create_scheduled_events, 
            time(hour=17, minute=0), 
            days=(1, 4)  # 1=вторник, 4=пятница
        )
        
        # Напоминания за 2 часа до тренировки
        job_queue.run_daily(
            self.send_presence_reminders, 
            time(hour=18, minute=0), 
            days=(3, 6)  # 3=четверг, 6=воскресенье
        )
        
        # Повторные напоминания за 1:03 до тренировки
        job_queue.run_daily(
            self.send_second_reminders, 
            time(hour=18, minute=57), 
            days=(3, 6)
        )
        
        # Автоматическая отписка через 3 минуты после второго напоминания
        job_queue.run_daily(
            self.auto_leave_unconfirmed, 
            time(hour=19, minute=0), 
            days=(3, 6)
        )
        
        # Очистка прошедших событий (изменено на 22:00)
        job_queue.run_daily(
            self.cleanup_past_events, 
            time(hour=22, minute=0)
        )
        
        # Создание первого события при запуске
        # job_queue.run_once(self.create_initial_event, 0)  # Отключено для избежания спама

    async def start_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        await handle_start(update, context, self.event_service, self.notification_service, self.db, self.chat_history_service)

    async def admin_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик админских команд"""
        if not update.effective_user:
            logger.warning("admin_handler: нет effective_user")
            return
        user_id = update.effective_user.id
        logger.info(f"admin_handler: пользователь {user_id} пытается войти в админ-меню")
        logger.info(f"admin_handler: ADMIN_IDS = {ADMIN_IDS}")
        if user_id not in ADMIN_IDS:
            logger.warning(f"admin_handler: пользователь {user_id} не в списке администраторов")
            if update.message:
                await update.message.reply_text("У вас нет прав администратора.")
            return
        
        logger.info(f"admin_handler: пользователь {user_id} успешно вошел в админ-меню")
        await handle_admin_commands(update, context, self.event_service, self.notification_service, self.db)

    async def callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик инлайн-кнопок"""

        # Проверяем, есть ли callback_query
        if not update.callback_query:
            logger.warning("callback_handler: update.callback_query is None")
            return
            
        query = update.callback_query
        
        try:
            # Отвечаем на callback сразу
            await query.answer()
            logger.info("query.answer() выполнен успешно")
            
            if not query.data:
                logger.warning("callback_handler: query.data is None")
                return
                
            data = query.data.split('_')
            action = data[0]
            
            logger.info(f"callback_handler: data={query.data}, action={action}, data_list={data}")
            
            if action in ['confirm', 'cancel']:
    
                await self.handle_leave_confirmation_callback(update, context, data)
            elif action in ['confirm_presence', 'decline_presence']:
    
                await self.handle_presence_confirmation_callback(update, context, data)
            elif action == 'leave' or action == 'cancel':
    
                await self.handle_partial_leave_callback(update, context, data)
            else:
                logger.warning(f"callback_handler: неизвестный action={action}")
        except Exception as e:
            logger.error(f"callback_handler: ошибка при обработке callback: {e}", exc_info=True)
    
    async def message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик текстовых сообщений"""
        if not update.message or not update.message.text:
            return
        text = update.message.text
        if not update.effective_user:
            return
        user = update.effective_user
        
        # Сохраняем сообщение пользователя в историю
        self.chat_history_service.save_user_message(user.id, text)
        
        # Сначала проверяем, является ли пользователь админом в админ-меню
        if user.id in ADMIN_IDS and context.user_data.get('admin_state'):
            # Проверяем специальное состояние для изменения лимита участников
            if context.user_data.get('admin_state') == 'change_participant_limit':
                from handlers.admin_handler import handle_change_participant_limit
                await handle_change_participant_limit(update, context, text, self.event_service, self.notification_service)
                return
            else:
                await handle_admin_commands(update, context, self.event_service, self.notification_service, self.db)
                return

        # Обрабатываем обычные сообщения
        await handle_event_actions(update, context, text, self.event_service, self.notification_service, self.db, self.chat_history_service)

    async def handle_leave_confirmation_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: list):
        """Обработка подтверждения отписки через инлайн-кнопки"""
        query = update.callback_query
        if not data or len(data) < 4:
            await query.edit_message_text("❌ Ошибка: некорректная кнопка или устаревшее действие.")
            import logging
            logging.error(f"Некорректный callback_data: {data}")
            return
        action = data[0]
        event_id = int(data[2])
        telegram_id = int(data[3])
        
        if action == "cancel":
            # Пользователь передумал
            event_info = self.event_service.get_event_by_id(event_id)
            participants_list = self.event_service.get_participants_list(event_id, event_info)
            await query.edit_message_text(f"Вы передумали!🥳\n\n{participants_list}")
            return
        
        elif action == "confirm":
            # Пользователь подтвердил отписку - сразу отписываем
            result = self.event_service.leave_event(event_id, telegram_id)
            
            if result['success']:
                await query.edit_message_text(result['message'])
                
                # Уведомляем всех об изменении
                await self.notification_service.send_participants_update(
                    event_id, telegram_id, query.from_user.username or f"Пользователь {telegram_id}", "отписался"
                )
                
                # Если кто-то переместился из резерва, уведомляем его
                if result.get('moved_participant'):
                    moved_user = result['moved_participant']
                    await self.notification_service.send_moved_to_main_notification(
                        moved_user['telegram_id'], moved_user['username']
                    )
                
                # Обновляем клавиатуру
                await self.update_user_keyboard(telegram_id, event_id)
            else:
                await query.edit_message_text(result['message'])
    
    async def handle_presence_confirmation_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: list):
        """Обработка подтверждения присутствия"""
        query = update.callback_query
        action = data[0]
        event_id = int(data[2])
        telegram_id = int(data[3])
        
        if action == "confirm_presence":
            # Пользователь подтвердил присутствие
            success = self.event_service.confirm_presence(event_id, telegram_id)
            if success:
                await query.edit_message_text("✅ Присутствие подтверждено! Увидимся на тренировке!")
            else:
                await query.edit_message_text("❌ Ошибка подтверждения присутствия")
        
        elif action == "decline_presence":
            # Пользователь отказался от присутствия - сразу отписываем
            result = self.event_service.leave_event(event_id, telegram_id)
            
            if result['success']:
                await query.edit_message_text("❌ Вы отписались от тренировки за неактивность.")
                
                # Уведомляем всех об изменении
                await self.notification_service.send_participants_update(
                    event_id, telegram_id, query.from_user.username or f"Пользователь {telegram_id}", "отписался"
                )
                
                # Если кто-то переместился из резерва, уведомляем его
                if result.get('moved_participant'):
                    moved_user = result['moved_participant']
                    await self.notification_service.send_moved_to_main_notification(
                        moved_user['telegram_id'], moved_user['username']
                    )
                
                # Обновляем клавиатуру
                await self.update_user_keyboard(telegram_id, event_id)
            else:
                await query.edit_message_text("❌ Ошибка при отписке")
    
    async def handle_partial_leave_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: list):
        """Обработка частичной отписки через инлайн-кнопки"""
        query = update.callback_query
        if not query:
            logger.error("handle_partial_leave_callback: update.callback_query is None!")
            return
        # Обработка нажатия кнопки 'Отмена' - просто сворачиваем клавиатуру
        if data and data[0] == "cancel":
            try:
                await query.delete()
            except Exception as e:
                logger.error(f"Ошибка при удалении клавиатуры: {e}")
            return
        action = data[1] if len(data) > 1 else ""
        telegram_id = query.from_user.id
        # Получаем активное событие
        active_events = self.event_service.get_active_events()
        if not active_events:
            await query.edit_message_text("❌ Нет активных событий.")
            return
        event_id = active_events[0]['id']
        if action == "partial":
            # Частичная отписка
            if len(data) > 2:
                reduce_by = int(data[2])
                result = self.event_service.reduce_group_size(event_id, telegram_id, reduce_by)
                if result.get('success'):
                    await query.edit_message_text(result.get('message', ''))
                    # Уведомляем всех об изменении
                    await self.notification_service.send_participants_update(
                        event_id, telegram_id, query.from_user.username or f"Пользователь {telegram_id}", "уменьшил группу"
                    )
                    # Если кто-то переместился из резерва, уведомляем его
                    if result.get('moved_participants'):
                        for moved_user in result['moved_participants']:
                            await self.notification_service.send_moved_to_main_notification(
                                moved_user['telegram_id'], moved_user['username']
                            )
                    # Обновляем клавиатуру
                    await self.update_user_keyboard(telegram_id, event_id)
                else:
                    await query.edit_message_text(f"❌ Ошибка: {result.get('message', '')}")
            else:
                await query.edit_message_text("❌ Ошибка: не указано количество для отписки")
        elif action == "group" and len(data) > 2 and data[2] == "all":
            # Отписка всей группы
            result = self.event_service.leave_event(event_id, telegram_id)
            if result.get('success'):
                await query.edit_message_text("✅ Вся группа отписана от события.")
                # Уведомляем всех об изменении
                await self.notification_service.send_participants_update(
                    event_id, telegram_id, query.from_user.username or f"Пользователь {telegram_id}", "отписался"
                )
                # Если кто-то переместился из резерва, уведомляем его
                if result.get('moved_participant'):
                    moved_user = result['moved_participant']
                    await self.notification_service.send_moved_to_main_notification(
                        moved_user['telegram_id'], moved_user['username']
                    )
                # Обновляем клавиатуру
                await self.update_user_keyboard(telegram_id, event_id)
            else:
                await query.edit_message_text(f"❌ Ошибка: {result.get('message', '')}")
    
    # Методы для планировщика задач
    async def create_scheduled_events(self, context: ContextTypes.DEFAULT_TYPE):
        """Создание событий по расписанию"""
        try:
            event_ids = self.event_service.create_scheduled_events()
            
            for event_id in event_ids:
                event = self.event_service.get_event_by_id(event_id)
                if event:
                    await self.notification_service.send_event_notification(event_id, event['name'])
                    logger.info(f"Создано и анонсировано событие {event_id}")
        
        except Exception as e:
            logger.error(f"Ошибка при создании событий по расписанию: {e}")
    
    async def create_initial_event(self, context: ContextTypes.DEFAULT_TYPE):
        """Создание первого события при запуске бота"""
        try:
            event_ids = self.event_service.create_scheduled_events()
            
            for event_id in event_ids:
                event = self.event_service.get_event_by_id(event_id)
                if event:
                    await self.notification_service.send_event_notification(event_id, event['name'])
                    logger.info(f"Создано и анонсировано начальное событие {event_id}")
        
        except Exception as e:
            logger.error(f"Ошибка при создании начального события: {e}")
    
    async def send_presence_reminders(self, context: ContextTypes.DEFAULT_TYPE):
        """Отправка напоминаний о подтверждении присутствия"""
        try:
            active_events = self.event_service.get_active_events()
            
            for event in active_events:
                participants = self.event_service.get_participants_for_reminder(event['id'], 'first')
                
                for participant in participants:
                    await self.notification_service.send_presence_reminder(
                        event['id'], participant['telegram_id'], event['name'], 'first'
                    )
                    self.event_service.mark_reminder_sent(event['id'], participant['telegram_id'], 'first')
        
        except Exception as e:
            logger.error(f"Ошибка при отправке напоминаний: {e}")
    
    async def send_second_reminders(self, context: ContextTypes.DEFAULT_TYPE):
        """Отправка повторных напоминаний"""
        try:
            active_events = self.event_service.get_active_events()
            
            for event in active_events:
                participants = self.event_service.get_participants_for_reminder(event['id'], 'second')
                
                for participant in participants:
                    await self.notification_service.send_presence_reminder(
                        event['id'], participant['telegram_id'], event['name'], 'second'
                    )
                    self.event_service.mark_reminder_sent(event['id'], participant['telegram_id'], 'second')
        
        except Exception as e:
            logger.error(f"Ошибка при отправке повторных напоминаний: {e}")
    
    async def auto_leave_unconfirmed(self, context: ContextTypes.DEFAULT_TYPE):
        """Автоматическая отписка неподтвердивших участников"""
        try:
            active_events = self.event_service.get_active_events()
            
            for event in active_events:
                # Получаем участников для автоматической отписки
                unconfirmed = self.event_service.get_unconfirmed_participants(event['id'])
                
                for participant in unconfirmed:
                    # Отправляем уведомление об автоматической отписке
                    await self.notification_service.send_auto_leave_notification(
                        participant['telegram_id'], event['name']
                    )
                    
                    # Обновляем клавиатуру для отписанного пользователя
                    await self.update_user_keyboard(participant['telegram_id'], event['id'])
                
                # Автоматически отписываем и перемещаем из резерва
                auto_leave_result = self.event_service.auto_leave_unconfirmed(event['id'])
                moved_participants = auto_leave_result.get('moved_to_main', [])
                
                # Уведомляем перемещенных участников
                for moved_participant in moved_participants:
                    await self.notification_service.send_moved_to_main_notification(
                        moved_participant['telegram_id'], moved_participant['username']
                    )
                    # Обновляем клавиатуру для перемещенного пользователя
                    await self.update_user_keyboard(moved_participant['telegram_id'], event['id'])
                
                # Если в резерве никого нет, уведомляем всех
                if not moved_participants:
                    await self.notification_service.send_no_reserve_notification(event['id'])
        
        except Exception as e:
            logger.error(f"Ошибка при автоматической отписке: {e}")
    
    async def update_user_keyboard(self, telegram_id: int, event_id: int):
        """Обновить клавиатуру пользователя в зависимости от его текущего статуса"""
        try:
            # Проверяем текущий статус пользователя
            participant = self.db.get_participant(event_id, telegram_id)
            is_joined = participant is not None
            
            # Создаем новую клавиатуру
            keyboard = create_main_keyboard(is_joined=is_joined)
            
            # Отправляем обновленную клавиатуру с уведомлением
            await self.application.bot.send_message(
                chat_id=telegram_id,
                text="Клавиатура обновлена",
                reply_markup=keyboard
            )
            
            logger.info(f"Клавиатура обновлена для пользователя {telegram_id}, статус: {'записан' if is_joined else 'не записан'}")
            
            # Добавляем небольшую задержку для стабильности
            await asyncio.sleep(0.1)
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении клавиатуры для пользователя {telegram_id}: {e}")
    
    async def cleanup_past_events(self, context: ContextTypes.DEFAULT_TYPE):
        """Очистка прошедших событий"""
        try:
            self.event_service.cleanup_past_events()
            logger.info("Прошедшие события очищены")
        except Exception as e:
            logger.error(f"Ошибка при очистке событий: {e}")

    def run(self):
        """Запуск бота"""
        # Настраиваем обработчики и задачи
        self.setup_handlers()
        self.setup_jobs()
        
        # Запускаем бота
        logger.info("Бот запущен")
        self.application.run_polling()

if __name__ == "__main__":
    bot = VolleyballBot()
    bot.run() 