from typing import Optional
import logging
from telegram import Update
from telegram.ext import ContextTypes
from services.event_service import EventService
from services.notification_service import NotificationService
from services.chat_history_service import ChatHistoryService
from data.database import Database
from utils.keyboard import create_main_keyboard, create_leave_confirmation_keyboard, create_group_size_keyboard, create_group_leave_keyboard, create_partial_leave_keyboard
from config.settings import MESSAGES

logger = logging.getLogger(__name__)

async def handle_event_actions(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, 
                              event_service: EventService, notification_service: NotificationService, 
                              db: Database, chat_history_service: Optional[ChatHistoryService] = None):
    """Обработка основных действий с событиями"""
    if not update.message:
        return
        
    user = update.effective_user
    if not user:
        return
        
    text = text.strip()
    user_data = context.user_data if context.user_data is not None else {}
    current_state = user_data.get('current_state')
    
    # Получаем активное событие
    active_events = event_service.get_active_events()
    if not active_events:
        await update.message.reply_text("В данный момент нет активных событий.")
        return
    
    # Берем первое активное событие
    current_event = active_events[0]
    event_id = current_event['id']
    
    # Проверяем, записан ли пользователь
    participant = db.get_participant(event_id, user.id)
    is_joined = participant is not None
    
    # --- Универсальный сброс состояния и показ актуальной клавиатуры при любой ошибке или невалидном действии ---
    async def reset_and_show_keyboard():
        user_data.pop('current_state', None)
        if db and event_id and user and hasattr(user, 'id'):
            await show_actual_keyboard(update, db, event_id, user.id)
    # ---
    

    
    # Обработка команд, которые должны работать независимо от состояния
    if text == "Список участников":
        await handle_show_participants(update, context, event_service, event_id)
        await reset_and_show_keyboard()
        return
    
    # Обработка состояний для записи группами
    if current_state == 'choosing_group_size':
        await handle_group_size_selection(update, context, text, event_service, notification_service, event_id, user, chat_history_service, db)
        return
    elif current_state == 'choosing_partial_leave':
        # Обработка выбора количества для отписки
        # Проверяем, что participant существует
        if not participant:
            await update.message.reply_text("❌ Вы не записаны на это событие.")
            await reset_and_show_keyboard()
            return
        
        # Парсим количество для отписки
        try:
            # Ищем число в тексте
            import re
            match = re.search(r'(\d+)', text)
            if match:
                reduce_by = int(match.group(1))
                
                # Проверяем, что число не больше размера группы
                if reduce_by > participant.get('group_size', 1):
                    await update.message.reply_text(f"❌ Нельзя отписать больше людей, чем в группе ({participant.get('group_size', 1)}).")
                    return
                
                # Выполняем частичную отписку
                result = event_service.reduce_group_size(event_id, user.id, reduce_by)
                await update.message.reply_text(result['message'])
                
                # Получаем обновлённого участника
                updated_participant = db.get_participant(event_id, user.id)
                
                # Если в группе остался 1 человек или меньше, сбрасываем состояние
                if not updated_participant or updated_participant.get('group_size', 1) <= 1:
                    user_data.pop('current_state', None)
                    await show_actual_keyboard(update, db, event_id, user.id)
                else:
                    # Если в группе осталось больше 1, можно снова частично отписаться
                    await update.message.reply_text(
                        f"В вашей группе осталось {updated_participant.get('group_size', 1)} человек. Хотите отписать ещё кого-то?",
                        reply_markup=create_partial_leave_keyboard(updated_participant.get('group_size', 1), db.get_max_group_size() if db else 3)
                    )
            else:
                # Если не удалось распарсить число, показываем клавиатуру снова
                if participant and participant.get('group_size', 1) > 1:
                    await update.message.reply_text(
                        "❌ Неверный формат. Выберите количество для отписки:",
                        reply_markup=create_partial_leave_keyboard(participant.get('group_size', 1), db.get_max_group_size() if db else 3)
                    )
                else:
                    await reset_and_show_keyboard()
                    
        except (ValueError, IndexError):
            # Если произошла ошибка, показываем клавиатуру снова
            if participant and participant.get('group_size', 1) > 1:
                await update.message.reply_text(
                    "❌ Неверный формат. Выберите количество для отписки:",
                    reply_markup=create_partial_leave_keyboard(participant.get('group_size', 1), db.get_max_group_size() if db else 3)
                )
            else:
                await reset_and_show_keyboard()
        return
    elif current_state == 'choosing_leave_type':
        await handle_leave_type_selection(update, context, text, event_service, notification_service, event_id, user, db)
        await reset_and_show_keyboard()
        return
    
    if text == "Иду на тренировку!":
        # Проверяем, включена ли запись группами
        if db and db.is_group_registration_enabled():
            user_data['current_state'] = 'choosing_group_size'
            max_group_size = db.get_max_group_size()
            await update.message.reply_text(
                f"👥 Введите размер группы (максимум {max_group_size} человек):"
            )
            return
        else:
            await handle_join_event(update, context, event_service, notification_service, event_id, user, chat_history_service)
            await show_actual_keyboard(update, db, event_id, user.id)
    
    elif text == "Передумал! Отписываюсь(":
        # Проверяем, включена ли запись группами и есть ли группа у пользователя
        if db.is_group_registration_enabled() and participant and participant.get('group_size', 1) > 1:
            user_data['current_state'] = 'choosing_partial_leave'
            group_size = participant.get('group_size', 1)
            max_group_size = db.get_max_group_size() if db else 3
            logger.info(f"Отправляем инлайн-клавиатуру для частичной отписки: группа из {group_size} человек")
            
            keyboard = create_partial_leave_keyboard(group_size, max_group_size)

            
            await update.message.reply_text(
                f"👥 Сколько человек отписать? (группа из {group_size})",
                reply_markup=keyboard
            )

            await reset_and_show_keyboard()
        else:
            await handle_leave_event(update, context, event_service, notification_service, event_id, user)
            await show_actual_keyboard(update, db, event_id, user.id)
    
    else:
        await update.message.reply_text("Неизвестная команда. Используйте кнопки для выбора действия.")
        await reset_and_show_keyboard()

async def handle_join_event(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                           event_service: EventService, notification_service: NotificationService, 
                           event_id: int, user, chat_history_service: Optional[ChatHistoryService] = None):
    """Обработка записи на событие"""
    if not update.message:
        return
        
    db = event_service.db if hasattr(event_service, 'db') else None
    try:
        result = event_service.join_event(
            event_id, 
            user.id, 
            user.username, 
            user.first_name, 
            user.last_name
        )
        
        if result['success']:
            await update.message.reply_text(result['message'])
            
            # Сохраняем сообщение бота в историю
            if chat_history_service:
                chat_history_service.save_bot_message(user.id, result['message'], event_id)
            
            # Получаем информацию о событии
            event_info = event_service.get_event_by_id(event_id)
            
            # Показываем список участников
            participants_list = event_service.get_participants_list(event_id, event_info)
            await update.message.reply_text(participants_list)
            
            # Сохраняем список участников в историю
            if chat_history_service:
                chat_history_service.save_bot_message(user.id, participants_list, event_id)
            
            # Уведомляем всех об изменении
            await notification_service.send_participants_update(
                event_id, user.id, user.username or f"Пользователь {user.id}", "записался"
            )
            
            # Обновляем клавиатуру
            if db and event_id and user and hasattr(user, 'id'):
                await show_actual_keyboard(update, db, event_id, user.id)
        else:
            await update.message.reply_text(
                result['message'],
                reply_markup=create_main_keyboard(is_joined=True)
            )
            
            # Сохраняем сообщение об ошибке в историю
            if chat_history_service:
                chat_history_service.save_bot_message(user.id, result['message'], event_id)
    
    except Exception as e:
        logger.error(f"Ошибка при записи на событие: {e}", exc_info=True)
        await notification_service.send_error_notification(user.id, "Ошибка при записи на событие")
        if db and event_id and user and hasattr(user, 'id'):
            await show_actual_keyboard(update, db, event_id, user.id)

async def handle_leave_event(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                            event_service: EventService, notification_service: NotificationService, 
                            event_id: int, user):
    """Обработка отписки от события (с кнопочным подтверждением)"""
    if not update.message:
        return
    db = event_service.db if hasattr(event_service, 'db') else None
    try:
        # Создаем клавиатуру для подтверждения
        keyboard = create_leave_confirmation_keyboard(event_id=event_id, telegram_id=user.id)
        
        await update.message.reply_text(
            MESSAGES['leave_confirmation'],
            reply_markup=keyboard
        )
        if db and event_id and user and hasattr(user, 'id'):
            await show_actual_keyboard(update, db, event_id, user.id)
    except Exception as e:
        logger.error(f"Ошибка при отписке от события: {e}", exc_info=True)
        await notification_service.send_error_notification(user.id, "Ошибка при отписке от события")
        if db and event_id and user and hasattr(user, 'id'):
            await show_actual_keyboard(update, db, event_id, user.id)

async def handle_show_participants(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                  event_service: EventService, event_id: int):
    """Показать список участников"""
    if not update.message:
        return
        
    try:
        # Получаем информацию о событии
        event_info = event_service.get_event_by_id(event_id)
        
        participants_list = event_service.get_participants_list(event_id, event_info)
        await update.message.reply_text(participants_list)
    
    except Exception as e:
        logger.error(f"Ошибка при показе списка участников: {e}", exc_info=True)
        db = event_service.db if hasattr(event_service, 'db') else None
        user = update.effective_user
        await update.message.reply_text("Ошибка при получении списка участников")
        if db and event_id and user and hasattr(user, 'id'):
            await show_actual_keyboard(update, db, event_id, user.id)

async def handle_show_chat_history(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """Показать историю чата"""
    if not update.message:
        return
        
    user = update.effective_user
    if not user:
        return
        
    try:
        chat_history_service = ChatHistoryService(db)
        
        # Получаем недавнюю историю (за последние 24 часа)
        recent_history = chat_history_service.get_recent_history(user.id, 24)
        
        if recent_history:
            # Форматируем историю для отображения
            history_text = chat_history_service.format_history_for_display(recent_history)
            
            # Добавляем статистику
            stats = chat_history_service.get_history_stats(user.id)
            stats_text = f"\n\n📊 Статистика:\nВсего сообщений: {stats['total_messages']}\nЗа последние 24 часа: {stats['recent_total']}"
            
            await update.message.reply_text(history_text + stats_text)
        else:
            await update.message.reply_text("📜 История чата пуста. Начните общение с ботом!")
    
    except Exception as e:
        logger.error(f"Ошибка при показе истории чата: {e}", exc_info=True)
        await update.message.reply_text("Ошибка при получении истории чата")
        # Не вызываем show_actual_keyboard, если event_id неизвестен

async def show_actual_keyboard(update: Update, db: Database, event_id: int, user_id: int):
    """Показать пользователю только актуальные кнопки согласно его статусу в базе"""
    if not update.message:
        return
    participant = db.get_participant(event_id, user_id)
    is_joined = participant is not None
    keyboard = create_main_keyboard(is_joined=is_joined)
    # Обновляем клавиатуру с уведомлением
    await update.message.reply_text(
        "Клавиатура обновлена",
        reply_markup=keyboard
    )

async def handle_group_size_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str,
                                     event_service: EventService, notification_service: NotificationService,
                                     event_id: int, user, chat_history_service: Optional[ChatHistoryService], db: Database):
    """Обработка выбора размера группы"""
    if not update.message:
        return
    try:
        max_group_size = db.get_max_group_size() if db else 3
        group_size = None
        # Пробуем распарсить число из текста
        import re
        match = re.search(r'(\d+)', text)
        if match:
            group_size = int(match.group(1))
        # Если выбрана кнопка
        if text.startswith("+1"):
            group_size = 2
        elif text.startswith("+2"):
            group_size = 3
        elif text.startswith("+3"):
            group_size = 4
        elif text.startswith("1 человек"):
            group_size = 1
        if group_size is None or group_size < 1 or group_size > max_group_size:
            await update.message.reply_text(
                f"❌ Размер группы должен быть от 1 до {max_group_size} человек. Пожалуйста, введите число от 1 до {max_group_size}:"
            )
            # Оставляем пользователя в состоянии выбора размера группы
            user_data = context.user_data if context.user_data is not None else {}
            user_data['current_state'] = 'choosing_group_size'
            return
        # Записываем пользователя с указанным размером группы
        result = event_service.join_event_with_group(
            event_id, 
            user.id, 
            group_size,
            user.username, 
            user.first_name, 
            user.last_name
        )
        
        if result['success']:
            group_text = f" (группа из {group_size} человек)" if group_size > 1 else ""
            await update.message.reply_text(result['message'] + group_text)
            
            # Сохраняем сообщение бота в историю
            if chat_history_service:
                chat_history_service.save_bot_message(user.id, result['message'] + group_text, event_id)
            
            # Получаем информацию о событии
            event_info = event_service.get_event_by_id(event_id)
            
            # Показываем список участников
            participants_list = event_service.get_participants_list(event_id, event_info)
            await update.message.reply_text(participants_list)
            
            # Сохраняем список участников в историю
            if chat_history_service:
                chat_history_service.save_bot_message(user.id, participants_list, event_id)
            
            # Уведомляем всех об изменении
            group_info = f" (группа из {group_size})" if group_size > 1 else ""
            await notification_service.send_participants_update(
                event_id, user.id, (user.username or f"Пользователь {user.id}") + group_info, "записался"
            )
            # После успешной записи сбрасываем состояние
            user_data = context.user_data if context.user_data is not None else {}
            user_data.pop('current_state', None)
            if db and event_id and user and hasattr(user, 'id'):
                await show_actual_keyboard(update, db, event_id, user.id)
        else:
            await update.message.reply_text(result['message'])
            # Сохраняем сообщение об ошибке в историю
            if chat_history_service:
                chat_history_service.save_bot_message(user.id, result['message'], event_id)
    except Exception as e:
        logger.error(f"Ошибка при выборе размера группы: {e}", exc_info=True)
        await update.message.reply_text("Ошибка при выборе размера группы. Пожалуйста, попробуйте еще раз.")
        if db and event_id and user and hasattr(user, 'id'):
            await show_actual_keyboard(update, db, event_id, user.id)



async def handle_leave_type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str,
                                     event_service: EventService, notification_service: NotificationService,
                                     event_id: int, user, db: Database):
    """Обработка выбора типа отписки для группы"""
    if not update.message:
        return
    
    user_data = context.user_data if context.user_data is not None else {}
    
    if text == "🔙 Отмена":
        user_data.pop('current_state', None)
        await update.message.reply_text(
            "Отписка отменена.",
            reply_markup=create_main_keyboard(is_joined=True)
        )
        await show_actual_keyboard(update, db, event_id, user.id)
        return
    
    participant = db.get_participant(event_id, user.id)
    if not participant:
        await update.message.reply_text("❌ Вы не записаны на это событие.")
        user_data.pop('current_state', None)
        # Обновляем клавиатуру по статусу
        await show_actual_keyboard(update, db, event_id, user.id)
        return
    
    group_size = participant.get('group_size', 1)
    
    if text == "👤 Отписать одного":
        # Отписываем только главного участника
        result = event_service.leave_event(event_id, user.id)
        if result['success']:
            await update.message.reply_text("✅ Вы отписаны от события.")
            user_data.pop('current_state', None)
            await show_actual_keyboard(update, db, event_id, user.id)
        else:
            await update.message.reply_text(f"❌ Ошибка: {result['message']}")
        return

    elif text == "👥 Отписать всех":
        # Отписываем всю группу
        result = event_service.leave_group(event_id, user.id, group_size)
        if result['success']:
            group_text = f" (группа из {group_size} человек)" if group_size > 1 else ""
            await update.message.reply_text(f"✅ Вся группа отписана от события{group_text}.")
            user_data.pop('current_state', None)
            await show_actual_keyboard(update, db, event_id, user.id)
        else:
            await update.message.reply_text(f"❌ Ошибка: {result['message']}")
        return
    
    else:
        # Показываем клавиатуру для частичной отписки
        from utils.keyboard import create_partial_leave_keyboard
        await update.message.reply_text(
            f"👥 Выберите количество человек для отписки (группа из {group_size}):",
            reply_markup=create_partial_leave_keyboard(group_size, db.get_max_group_size() if db else 3)
        )
        return
    
    # Сбрасываем состояние и обновляем клавиатуру
    user_data.pop('current_state', None)
    await update.message.reply_text(
        "Обновлено", 
        reply_markup=create_main_keyboard(is_joined=False)
    )
    await show_actual_keyboard(update, db, event_id, user.id)

    if text == "🔙 Обычный режим":
        user_data.pop('admin_state', None)
        await update.message.reply_text(
            "Вы вышли из админского режима."
        )
        # Обновляем клавиатуру по статусу пользователя
        participant = db.get_participant(event_service.get_next_event_id(), user.id) if db else None
        is_joined = participant is not None
        await update.message.reply_text(
            "Клавиатура обновлена",
            reply_markup=create_main_keyboard(is_joined=is_joined)
        )
        await show_actual_keyboard(update, db, event_id, user.id)
        return 