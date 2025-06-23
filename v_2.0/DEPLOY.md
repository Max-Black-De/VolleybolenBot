# 🚀 Деплой Telegram-бота (v_2.0) на Amvera

## 1. Клонируйте репозиторий
```bash
git clone https://github.com/Max-Black-De/VolleybolenBot.git
cd VolleybolenBot
```

## 2. Перейдите в папку v_2.0
```bash
cd v_2.0
```

## 3. Установите зависимости
```bash
pip install -r requirements.txt
```

## 4. Настройте переменные окружения
Создайте файл `.env` или настройте переменные окружения в панели Amvera:
- `BOT_API_TOKEN` — токен Telegram-бота
- `ADMIN_IDS` — список ID админов (через запятую)

Пример `.env`:
```
BOT_API_TOKEN=your_token_here
ADMIN_IDS=123456789,987654321
```

## 5. Проверьте настройки
- В файле `config/settings.py` убедитесь, что параметры соответствуют вашим требованиям.

## 6. Запуск бота
### Через Procfile (если поддерживается)
Amvera сама определит команду запуска из Procfile:
```
web: python v_2.0/main_new.py
```

### Или вручную:
```bash
python main_new.py
```

## 7. Миграция БД
База данных создаётся автоматически при первом запуске. Если нужно сбросить БД:
```bash
rm volleyball_bot.db
```

## 8. Логи и отладка
- Логи выводятся в консоль.
- Для подробного логирования отредактируйте `main_new.py`:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 9. Автозапуск (если не Procfile)
Рекомендуется настроить systemd unit или Supervisor для автозапуска.

---

**Готово! Бот будет работать на Amvera в папке v_2.0.** 