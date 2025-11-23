# NewsBot (Telegram) — пересказ новостей через OpenRouter

Коротко: бот забирает посты из каналов (Bot API или Pyrogram), переформулирует их с учётом вашего стиля и шлёт в ЛС/чат. Поддерживает пометки о медиа, ручной стиль и доработку результата.

## Возможности
- Переформулирование новостей через OpenRouter (по умолчанию `deepseek/deepseek-chat-v3.1:free`).
- Источники:
  - Bot API: если бот админ в канале — ловит `channel_post`.
  - Pyrogram (MTProto): следит за публичными каналами из `WATCH_CHANNELS` (без добавления бота).
- Отправка результата:
  - В ЛС (`DEST_USER_ID`) — приоритетно.
  - В указанный чат/канал (`TARGET_CHAT_ID`).
  - Иначе — в исходный канал (только Bot API).
- Пометки о медиа в конце текста: "(есть изображение)", "(есть видео)", "(есть изображение и видео)".
- Управление стилем и доработки:
  - `/style <текст>` — задать/посмотреть дополнительные указания стиля (сохраняются на чат).
  - `/revise <правки>` — доработать последний пересказ по вашим указаниям.
  - `/paraphrase` — переформулировать текст из реплая или аргумента.
  - `/me` — показать ваш user_id. `/check` — проверить, может ли бот писать в целевой чат.

## Установка
```powershell
py -m venv .venv  # или python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
Если Windows блокирует активацию: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`.

## Настройка окружения (.env)
Создайте файл `.env` рядом с `bot.py`:
```
TELEGRAM_BOT_TOKEN=123456:AA...          # токен из @BotFather
OPENROUTER_API_KEY=sk-or-...             # ключ OpenRouter
OPENROUTER_MODEL=deepseek/deepseek-chat-v3.1:free  # опц., можно менять модель

# Куда слать результат (приоритет по порядку)
DEST_USER_ID=123456789                   # ваш user_id для ЛС
TARGET_CHAT_ID=-1001234567890            # канал/чат, куда писать (если не ЛС)

# Pyrogram (для мониторинга публичных каналов)
TELEGRAM_API_ID=xxxxx
TELEGRAM_API_HASH=xxxxxxxxxxxxxxxxxxxxxxx
WATCH_CHANNELS=bankrollo,rian_ru         # списком через запятую без @
PYROGRAM_SESSION=pyrogram                # имя файла сессии (по умолчанию)

# Опционально для OpenRouter заголовка Referer
APP_URL=https://yourapp.example

# Если используете прокси для Telegram Bot API
# HTTPS_PROXY=http://user:pass@host:port
# HTTP_PROXY=http://user:pass@host:port
```

## Запуск
```powershell
.\.venv\Scripts\python .\bot.py
```
Первый запуск Pyrogram может запросить код подтверждения в консоли — следуйте инструкциям.

## Изменение модели LLM
- Через .env: `OPENROUTER_MODEL=openai/gpt-4o-mini` (пример).
- Или в коде: найдите `OPENROUTER_MODEL = "..."` в `bot.py` и замените.

## Как пользоваться
- В ЛС с ботом: `/start`, затем `/me` (узнать id), пропишите `DEST_USER_ID` в `.env`.
- Задайте стиль: `/style делай короче, первые 10 слов — крючок`.
- Проверьте отправку: `/check`.
- Бот начнёт присылать пересказ новых постов из `WATCH_CHANNELS`. Для доработки последней новости: `/revise акцентируй источник, убери лишние прилагательные`.

## Траблшутинг
- Бот пишет: `Invalid token` — перевыпустите токен в @BotFather, обновите `.env`.
- `httpx.ConnectError: getaddrinfo failed` — проблемы DNS/сети. Проверьте доступ к `https://api.telegram.org`, смените DNS (8.8.8.8/1.1.1.1), отключите VPN/фильтры, либо задайте `HTTPS_PROXY`/`HTTP_PROXY`.
- Pyrogram `Peer id invalid` — не критично. Очистите `pyrogram.session` и авторизуйтесь заново, либо дождитесь актуализации кеша.
- Сообщения не приходят в ЛС:
  - Убедитесь, что вы написали боту `/start` (иначе он не может писать вам).
  - Проверьте `/check` — должно быть "ОК: могу писать".
  - Проверьте, что указали `DEST_USER_ID` верно.
- Ничего не ловится из каналов:
  - Для Bot API — бот должен быть админом канала.
  - Для Pyrogram — проверьте логи: `watching @... -> id ...`, затем ожидайте `[Pyrogram] on_message ...` либо `[Pyrogram/Fallback] fetched ...`.

## Деплой на сервер

Для развертывания бота на Ubuntu 20.04 сервере с автоматическим запуском через systemd см. подробную инструкцию в [DEPLOY.md](DEPLOY.md).

Кратко:
1. Клонируйте репозиторий на сервер
2. Создайте виртуальное окружение и установите зависимости
3. Настройте `.env` файл
4. Установите systemd service
5. Запустите бота: `sudo systemctl start newsbot`

## Безопасность
- Не коммитьте `.env` и файлы сессий (`pyrogram.session`, `.telethon.session`).
- Храните `OPENROUTER_API_KEY` и `TELEGRAM_BOT_TOKEN` только локально/в секретах CI.

## Лицензия
MIT (на ваше усмотрение).
