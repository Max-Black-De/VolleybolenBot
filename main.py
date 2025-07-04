import logging
import locale
from datetime import datetime, time
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

from config.secure import secrets
from config.settings import BOT_SETTINGS, MESSAGES, ADMIN_IDS
from data.database import Database
from services.event_service import EventService
from services.notification_service import NotificationService
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
if not TOKEN:
    raise ValueError("BOT_API_TOKEN не найден в config/secure.py")

db = Database()
event_service = EventService(db)

class VolleyballBot:
    def __init__(self):
        self.application = ApplicationBuilder().token(TOKEN).build()
        self.db = Database()
        self.event_service = EventService(self.db)
        self.notification_service = NotificationService(self.application.bot, self.db)
        
    def setup_handlers(self):
        """Настройка обработчиков"""
        # Основные команды
        self.application.add_handler(CommandHandler("start", self.start_handler))
        self.application.add_handler(CommandHandler("admin", self.admin_handler))
        
        # Обработка инлайн-кнопок
        self.application.add_handler(CallbackQueryHandler(self.callback_handler))
        
        # Обработка текстовых сообщений
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.message_handler))

    def setup_jobs(self):
        """Настройка планировщика задач"""
        job_queue = self.application.job_queue
        if not job_queue:
            logger.warning("Job queue недоступен")
            return
        
        # Создание событий по расписанию (вторник и пятница в 17:00)
        job_queue.run_daily(self.create_scheduled_events, time(hour=17, minute=0), days=(1, 4))  # 1=вторник, 4=пятница
        
        # Напоминания за 2 часа до тренировки
        job_queue.run_daily(self.send_presence_reminders, time(hour=18, minute=0), days=(3, 6))  # 3=четверг, 6=воскресенье
        
        # Повторные напоминания за 1:03 до тренировки
        job_queue.run_daily(self.send_second_reminders, time(hour=18, minute=57), days=(3, 6))
        
        # Автоматическая отписка через 3 минуты после второго напоминания
        job_queue.run_daily(self.auto_leave_unconfirmed, time(hour=19, minute=0), days=(3, 6))
        
        # Очистка прошедших событий
        job_queue.run_daily(self.cleanup_past_events, time(hour=23, minute=59))
        
        # Создание первого события при запуске
        job_queue.run_once(self.create_initial_event, 0)

    async def start_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        await handle_start(update, context, self.event_service, self.notification_service, self.db)

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
        if not update.callback_query:
            return
        query = update.callback_query
        await query.answer()
        
        if not query.data:
            return
        data = query.data.split('_')
        action = data[0]
        
        if action in ['confirm', 'cancel']:
            await self.handle_leave_confirmation_callback(update, context, data)
        elif action in ['confirm_presence', 'decline_presence']:
            await self.handle_presence_confirmation_callback(update, context, data)
    
    async def message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик текстовых сообщений"""
        if not update.message or not update.message.text:
            return
        text = update.message.text
        if not update.effective_user:
            return
        user = update.effective_user
        
        # Сначала проверяем, является ли пользователь админом в админ-меню
        if user.id in ADMIN_IDS and context.user_data.get('admin_state'):
            await handle_admin_commands(update, context, self.event_service, self.notification_service, self.db)
            return

        # Проверяем, есть ли ожидающее подтверждение отписки
        pending_data = context.user_data.get('pending_leave_confirmation')
        if pending_data and pending_data['telegram_id'] == user.id:
            await self.handle_leave_text_confirmation(update, context, text)
            return

        # Обрабатываем обычные сообщения
        await handle_event_actions(update, context, text, self.event_service, self.notification_service, self.db)

    async def handle_leave_confirmation_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: list):
        """Обработка подтверждения отписки через инлайн-кнопки"""
        query = update.callback_query
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
            # Пользователь подтвердил отписку, переходим к текстовому подтверждению
            await query.edit_message_text(MESSAGES['leave_text_confirmation'])
            context.user_data['pending_leave_confirmation'] = {
                'event_id': event_id,
                'telegram_id': telegram_id
            }
    
    async def handle_leave_text_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Обработка текстового подтверждения отписки"""
        user = update.effective_user
        pending_data = context.user_data.get('pending_leave_confirmation')
        
        if not pending_data or pending_data['telegram_id'] != user.id:
            return
        
        event_id = pending_data['event_id']
        text_lower = text.lower()
        
        if text_lower == 'да':
            # Пользователь подтвердил отписку
            result = self.event_service.leave_event(event_id, user.id)
            
            if result['success']:
                await update.message.reply_text(result['message'])
                
                # Уведомляем всех об изменении
                await self.notification_service.send_participants_update(
                    event_id, user.id, user.username or f"Пользователь {user.id}", "отписался"
                )
                
                # Если кто-то переместился из резерва, уведомляем его
                if result.get('moved_participant'):
                    moved_user = result['moved_participant']
                    await self.notification_service.send_moved_to_main_notification(
                        moved_user['telegram_id'], moved_user['username']
                    )
                
                # Обновляем клавиатуру
                await update.message.reply_text(
                    "Обновлено", 
                    reply_markup=create_main_keyboard(is_joined=False)
                )
            else:
                await update.message.reply_text(result['message'])
        
        elif text_lower == 'нет':
            # Пользователь передумал
            await update.message.reply_text(MESSAGES['leave_cancelled'])
        
        # Удаляем данные подтверждения
        del context.user_data['pending_leave_confirmation']
    
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
            # Пользователь отказался от присутствия, запускаем процесс отписки
            await query.edit_message_text(MESSAGES['leave_text_confirmation'])
            context.user_data['pending_leave_confirmation'] = {
                'event_id': event_id,
                'telegram_id': telegram_id
            }
    
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
                
                # Автоматически отписываем и перемещаем из резерва
                moved_participants = self.event_service.auto_leave_unconfirmed(event['id'])
                
                # Уведомляем перемещенных участников
                for moved_participant in moved_participants:
                    await self.notification_service.send_moved_to_main_notification(
                        moved_participant['telegram_id'], moved_participant['username']
                    )
                
                # Если в резерве никого нет, уведомляем всех
                if not moved_participants:
                    await self.notification_service.send_no_reserve_notification(event['id'])
        
        except Exception as e:
            logger.error(f"Ошибка при автоматической отписке: {e}")
    
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