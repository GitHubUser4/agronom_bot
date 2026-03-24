# 🌶 Pepper Agronomist Bot

Telegram-бот на базе ИИ (Google Gemini), который помогает садоводам оценить шансы на получение урожая конкретного сорта перца в их регионе. 

## ✨ Основные функции
- **База знаний о сортах:** Описание, острота (SHU) и сроки созревания.
- **Умный расчет успеха:** Оценка вероятности урожая (1-10) с учетом города и условий (теплица, грунт, подоконник).
- **Защита от спама:** Ограничение длины ввода и фильтрация нецелевых запросов.
- **Бизнес-логирование:** Запись всех поисковых запросов в JSON для аналитики популярности сортов.

___ 

## 🚀 Быстрый старт на VPS (Ubuntu/Linux)

### 1. Подготовка окружения
```bash
# Обновляем пакеты и ставим python-venv
sudo apt update && sudo apt install python3-pip python3-venv -y

# Клонируем проект (или переносим файлы)
mkdir pepper_bot && cd pepper_bot
python3 -m venv venv
source venv/bin/activate

# Устанавливаем зависимости
pip install -r requirements.txt
```

### 2. Настройка переменных окружения

Создайте файл .env в корневой папке:
```ini
BOT_TOKEN=ваш_токен_от_BotFather
GEMINI_API_KEY=ваш_ключ_от_Google_AI_Studio
```

### 3. Запуск через systemd (Автозапуск 24/7)

Чтобы бот работал постоянно, создадим сервисный файл:
```bash
sudo nano /etc/systemd/system/pepper_bot.service
```
Вставьте следующее (замените ИМЯ_ПОЛЬЗОВАТЕЛЯ и ПУТЬ_К_БОТУ):
```ini
[Unit]
Description=Pepper Agronomist Telegram Bot
After=network.target

[Service]
User=ИМЯ_ПОЛЬЗОВАТЕЛЯ
Group=www-data
WorkingDirectory=/home/ИМЯ_ПОЛЬЗОВАТЕЛЯ/pepper_bot
EnvironmentFile=/home/ИМЯ_ПОЛЬЗОВАТЕЛЯ/pepper_bot/.env
ExecStart=/home/ИМЯ_ПОЛЬЗОВАТЕЛЯ/pepper_bot/venv/bin/python3 agronom_bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Запустите сервис:

```bash
sudo systemctl daemon-reload
sudo systemctl enable pepper_bot
sudo systemctl start pepper_bot
```
___
## 📊 Аналитика
Бот ведет два типа логов:

user_queries.json: Структурированные данные о запросах (что ищут люди).

bot_errors.log: Технические ошибки для отладки.
