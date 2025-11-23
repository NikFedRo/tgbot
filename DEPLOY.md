# Инструкция по деплою бота на Ubuntu 20.04

Это пошаговая инструкция по развертыванию Telegram бота на Ubuntu 20.04 сервере с использованием systemd для автоматического запуска и управления.

## Предварительные требования

- Ubuntu 20.04 или новее
- SSH доступ к серверу
- Git установлен на сервере
- Python 3.8 или новее

## Шаг 1: Подключение к серверу

```bash
ssh username@your-server-ip
```

## Шаг 2: Установка зависимостей

```bash
# Обновление пакетов
sudo apt update
sudo apt upgrade -y

# Установка Python и необходимых инструментов
sudo apt install -y python3 python3-pip python3-venv git
```

## Шаг 3: Клонирование репозитория

```bash
# Переходим в домашнюю директорию
cd ~

# Клонируем репозиторий (замените на ваш URL)
git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git tgbot

# Переходим в директорию проекта
cd tgbot
```

## Шаг 4: Создание виртуального окружения

```bash
# Создаем виртуальное окружение
python3 -m venv .venv

# Активируем виртуальное окружение
source .venv/bin/activate

# Устанавливаем зависимости
pip install --upgrade pip
pip install -r requirements.txt
```

## Шаг 5: Настройка переменных окружения

```bash
# Копируем шаблон .env
cp .env.example .env

# Редактируем .env файл (используйте nano, vim или другой редактор)
nano .env
```

Заполните все необходимые переменные:
- `TELEGRAM_BOT_TOKEN` - токен бота от @BotFather
- `OPENROUTER_API_KEY` - ключ API OpenRouter
- `DEST_USER_ID` - ваш user_id (узнайте через `/me` в боте)
- `TELEGRAM_API_ID` и `TELEGRAM_API_HASH` - для Pyrogram (получите на https://my.telegram.org/apps)
- `WATCH_CHANNELS` - каналы для мониторинга

## Шаг 6: Первый запуск (для авторизации Pyrogram)

Если вы используете Pyrogram, нужно один раз запустить бота вручную для авторизации:

```bash
# Убедитесь, что виртуальное окружение активировано
source .venv/bin/activate

# Запускаем бота
python bot.py
```

Введите код подтверждения, который придет в Telegram. После успешной авторизации остановите бота (Ctrl+C).

## Шаг 7: Установка systemd service

```bash
# Копируем service файл в systemd
sudo cp newsbot.service /etc/systemd/system/newsbot.service

# Замените %i на ваше имя пользователя в файле
# Или отредактируйте файл напрямую:
sudo nano /etc/systemd/system/newsbot.service
```

В файле `/etc/systemd/system/newsbot.service` замените все вхождения `%i` на ваше имя пользователя (то, которое вы используете для SSH). Например, если вы залогинены как `ubuntu`, замените:
- `/home/%i/tgbot` → `/home/ubuntu/tgbot`

Или используйте sed для автоматической замены:

```bash
# Замените YOUR_USERNAME на ваше имя пользователя
sudo sed -i 's/%i/YOUR_USERNAME/g' /etc/systemd/system/newsbot.service
```

## Шаг 8: Запуск и управление ботом

```bash
# Перезагружаем systemd для применения изменений
sudo systemctl daemon-reload

# Включаем автозапуск при загрузке системы
sudo systemctl enable newsbot

# Запускаем бота
sudo systemctl start newsbot

# Проверяем статус
sudo systemctl status newsbot

# Просмотр логов
sudo journalctl -u newsbot -f

# Остановка бота
sudo systemctl stop newsbot

# Перезапуск бота
sudo systemctl restart newsbot
```

## Шаг 9: Проверка работы

1. Проверьте логи: `sudo journalctl -u newsbot -f`
2. Отправьте боту команду `/start` в Telegram
3. Проверьте, что бот отвечает
4. Используйте `/check` для проверки отправки сообщений

## Обновление бота

Когда нужно обновить код бота:

```bash
cd ~/tgbot

# Получаем последние изменения
git pull

# Перезапускаем бота
sudo systemctl restart newsbot

# Проверяем логи
sudo journalctl -u newsbot -f
```

## Устранение неполадок

### Бот не запускается

```bash
# Проверьте статус
sudo systemctl status newsbot

# Проверьте логи
sudo journalctl -u newsbot -n 50

# Проверьте, что путь к Python правильный
which python3
/home/YOUR_USERNAME/tgbot/.venv/bin/python --version
```

### Проблемы с правами доступа

```bash
# Убедитесь, что файлы принадлежат вашему пользователю
sudo chown -R YOUR_USERNAME:YOUR_USERNAME ~/tgbot
```

### Проблемы с виртуальным окружением

```bash
cd ~/tgbot
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart newsbot
```

### Проблемы с Pyrogram авторизацией

Если нужно переавторизоваться:

```bash
# Удалите файл сессии
rm ~/tgbot/pyrogram.session*

# Запустите бота вручную для авторизации
cd ~/tgbot
source .venv/bin/activate
python bot.py
```

## Полезные команды

```bash
# Просмотр последних 100 строк логов
sudo journalctl -u newsbot -n 100

# Просмотр логов в реальном времени
sudo journalctl -u newsbot -f

# Просмотр логов за сегодня
sudo journalctl -u newsbot --since today

# Проверка, что бот запущен
sudo systemctl is-active newsbot

# Проверка, что автозапуск включен
sudo systemctl is-enabled newsbot
```

## Безопасность

- Не коммитьте `.env` файл в Git (он уже в `.gitignore`)
- Храните секретные ключи только в `.env` на сервере
- Регулярно обновляйте зависимости: `pip install --upgrade -r requirements.txt`
- Используйте сильные пароли для SSH доступа
- Рассмотрите возможность настройки firewall (ufw)

