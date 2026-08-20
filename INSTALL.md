# Полное руководство по установке и настройке TelegramWarden

Этот документ содержит исчерпывающую пошаговую инструкцию по установке, подробному заполнению файла конфигурации `.env`, настройке Telegram WebApp и рекомендациям по оптимальной эксплуатации для разработчиков и ИИ-агентов.

---

## Содержание

1. [Системные требования](#1-системные-требования)
2. [Подготовка внешних сервисов и ключей](#2-подготовка-внешних-сервисов-и-ключей)
3. [Полная настройка файла переменных окружения (.env)](#3-полная-настройка-файла-переменных-окружения-env)
4. [Развертывание через Docker Compose (Рекомендуемый способ)](#4-развертывание-через-docker-compose-рекомендуемый-способ)
5. [Локальная установка без Docker (Python 3.12)](#5-локальная-установка-без-docker-python-312)
6. [Настройка Telegram Mini App в @BotFather](#6-настройка-telegram-mini-app-в-botfather)
7. [Рекомендации по лучшей практике (Best Practices)](#7-рекомендации-по-лучшей-практике-best-practices)
8. [Чеклист валидации и решения частых проблем](#8-чеклист-валидации-и-решения-частых-проблем)

---

## 1. Системные требования

- **Операционная система**: Linux (Ubuntu 22.04+, Debian 12+, Rocky Linux) или Windows 10/11 (PowerShell / WSL2) или macOS
- **Оперативная память (RAM)**: от 1.5 ГБ (локальная ONNX модель занимает ~150 МБ RAM)
- **Дисковое пространство**: от 2 ГБ свободного места
- **Docker и Docker Compose**: Docker 24.0+ и Compose V2
- **Либо для ручной сборки**: Python 3.12+, PostgreSQL 16+, Redis 7+

---

## 2. Подготовка внешних сервисов и ключей

Перед запуском проекта необходимо получить:

1. **Telegram Bot Token**:
   - Откройте официального бота [@BotFather](https://t.me/BotFather) в Telegram.
   - Отправьте команду `/newbot` и следуйте инструкциям.
   - Скопируйте полученный токен (формат: `123456789:ABCDefghIJKlmnoPQRstuvWXYZ`).
   - Отправьте команду `/setprivacy` -> выберите созданного бота -> выберите `Disable` (чтобы бот мог читать сообщения в группах для анализа).

2. **Ваш Telegram User ID (для прав Супер-администратора)**:
   - Узнайте свой числовой ID через бота [@userinfobot](https://t.me/userinfobot) (например, `8667615215`).

3. **API-ключ нейросети (LLM)**:
   - **Основной провайдер (NVIDIA NIM / DeepSeek / OpenAI)**:
     - Для NVIDIA NIM: зарегистрируйтесь на [build.nvidia.com](https://build.nvidia.com), создайте API ключ `nvapi-...`.
     - Для DeepSeek: получите ключ на [platform.deepseek.com](https://platform.deepseek.com).
   - **Резервный провайдер (Groq / OpenRouter / Gemini)**:
     - Groq (бесплатно и очень быстро): [console.groq.com](https://console.groq.com).

4. **Публичный HTTPS URL (для WebApp панели)**:
   - Для локальной разработки: используйте Cloudflare Tunnel (`cloudflared tunnel --url http://localhost:2009`) или Ngrok.
   - Для продакшена: ваш домен с SSL (например, `https://warden.yourdomain.com/app`).

---

## 3. Полная настройка файла переменных окружения (.env)

Создайте файл `.env` в корне проекта на основе шаблона:

```bash
# На Linux / macOS:
cp .env.example .env

# На Windows (PowerShell):
Copy-Item .env.example .env
```

### Подробное описание каждого параметра в `.env`:

```env
# ==========================================
# 1. TELEGRAM BOT CREDENTIALS
# ==========================================

# Токен вашего бота от @BotFather (Обязательно)
BOT_TOKEN=123456789:ABCDefghIJKlmnoPQRstuvWXYZ_example

# Юзернейм бота без символа @ (Обязательно)
BOT_USERNAME=MyWardenBot

# Telegram ID супер-администраторов через запятую.
# Пользователи с этими ID получают полный доступ ко всем настройкам,
# Data Explorer в WebApp и иммунитет от санкций.
SUPERADMIN_IDS=8667615215,123456789


# ==========================================
# 2. LLM AI ENGINE (АНАЛИЗ ТЕКСТА)
# ==========================================

# Основной провайдер нейросети (NVIDIA NIM / DeepSeek / OpenAI)
DEEPSEEK_API_KEY=nvapi-your-nvidia-nim-or-deepseek-key
DEEPSEEK_BASE_URL=https://integrate.api.nvidia.com/v1
DEEPSEEK_MODEL=meta/llama-3.1-70b-instruct

# Резервный провайдер на случай таймаутов или сбоев основного API
FALLBACK_AI_ENABLED=true
FALLBACK_API_KEY=gsk_your_groq_api_key_here
FALLBACK_BASE_URL=https://api.groq.com/openai/v1
FALLBACK_MODEL=llama-3.3-70b-versatile


# ==========================================
# 3. FASTAPI BACKEND & WEBAPP DASHBOARD
# ==========================================

# Хост и порт для веб-сервера
API_HOST=0.0.0.0
API_PORT=2009

# Случайная 32-байтная секретная строка для подписи сессий
SECRET_KEY=e8f9a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1

# Публичный HTTPS адрес WebApp для Telegram Menu Button и инлайн-кнопок
# ВНИМАНИЕ: Telegram требует ТОЛЬКО https://
WEBAPP_URL=https://your-domain.com/app

# Токен постоянного Cloudflare Tunnel (Опционально, для бесплатного постоянного HTTPS)
# Если используете локальный временный туннель, оставьте пустым
CLOUDFLARE_TUNNEL_TOKEN=



# ==========================================
# 4. DATABASE & REDIS (ДЛЯ DOCKER ОСТАВИТЬ ПО УМОЛЧАНИЮ)
# ==========================================

POSTGRES_USER=warden_user
POSTGRES_PASSWORD=warden_secure_password
POSTGRES_DB=warden_db
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0


# ==========================================
# 5. СРОКИ ХРАНЕНИЯ ДАННЫХ И ЛОГИРОВАНИЕ
# ==========================================

# Срок действия предупреждений по умолчанию (в днях, 1-90)
WARN_EXPIRATION_DAYS=14

# Срок хранения аудит-логов нарушений в базе данных (в днях)
LOGS_RETENTION_DAYS=30

# Уровень логирования в консоль (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO
```

---

## 4. Развертывание через Docker Compose (Рекомендуемый способ)

Docker Compose автоматически поднимет изолированную базу данных PostgreSQL 16, Redis 7 и контейнер `warden_app` с горячим монтированием кода и автоматической инициализацией таблиц.

### На Linux / macOS:
```bash
# 1. Запуск сборки и старта контейнеров в фоновом режиме
docker compose up -d --build

# 2. Проверка состояния сервисов
docker compose ps

# 3. Просмотр живых логов бота
docker compose logs -f warden_app
```

### На Windows (PowerShell):
```powershell
# 1. Запуск сборки и старта контейнеров
docker compose up -d --build

# 2. Проверка состояния
docker compose ps

# 3. Просмотр логов
docker compose logs -f warden_app
```

### Остановка и перезапуск:
```bash
# Перезапуск приложения
docker compose restart warden_app

# Полная остановка стека
docker compose down
```

---

## 5. Локальная установка без Docker (Python 3.12)

Если вы разрабатываете проект локально и хотите запускать код напрямую в интерпретаторе:

### На Linux / macOS:
```bash
# 1. Создание виртуального окружения
python3.12 -m venv .venv
source .venv/bin/activate

# 2. Установка зависимостей
pip install --upgrade pip
pip install -r requirements.txt

# 3. Запуск Postgres и Redis (в Docker)
docker compose up -d postgres redis

# 4. В .env установите:
# POSTGRES_HOST=localhost
# REDIS_HOST=localhost

# 5. Запуск тестов для проверки окружения
pytest tests/ -v

# 6. Запуск единого сервиса
python -m bot.main
```

### На Windows (PowerShell):
```powershell
# 1. Создание виртуального окружения
python -m venv .venv
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\.venv\Scripts\Activate.ps1

# 2. Установка зависимостей
python -m pip install --upgrade pip
pip install -r requirements.txt

# 3. Запуск Postgres и Redis
docker compose up -d postgres redis

# 4. В .env установите POSTGRES_HOST=localhost и REDIS_HOST=localhost

# 5. Запуск тестов
pytest tests/ -v

# 6. Запуск единого сервиса
python -m bot.main
```

---

## 6. Бесплатный HTTPS через Cloudflare Tunnel для WebApp

Telegram требует, чтобы Mini App открывался строго по безопасному протоколу `https://`. Для этого есть два бесплатных способа:

### Вариант А. Быстрый временный туннель (Без регистрации)
Если вы тестируете проект локально, скачайте официальную бесплатную утилиту `cloudflared`:
- **Linux**: `curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared && chmod +x /usr/local/bin/cloudflared`
- **Windows (winget)**: `winget install --id Cloudflare.cloudflared`

Запустите туннель на порт 2009:
```bash
cloudflared tunnel --url http://127.0.0.1:2009
```
В терминале появится ссылка вида `https://xxxx-xxxx-xxxx.trycloudflare.com`. Скопируйте ее и укажите в `.env` как `WEBAPP_URL=https://xxxx-xxxx-xxxx.trycloudflare.com/app`.

### Вариант Б. Постоянный бесплатный Cloudflare Tunnel в Docker
1. Зарегистрируйтесь на [dash.cloudflare.com](https://dash.cloudflare.com) (бесплатно).
2. Перейдите в **Zero Trust** -> **Networks** -> **Tunnels** -> **Create a tunnel**.
3. Выберите тип Docker и скопируйте предоставленный токен туннеля.
4. Вставьте токен в `.env`:
```env
CLOUDFLARE_TUNNEL_TOKEN=eyJhIjoiYmNkZWY...
```
5. В интерфейсе Cloudflare направьте публичный субдомен (например, `warden.yourdomain.com`) на сервис `http://warden_app:2009`.
6. Запустите стек с профилем туннеля:
```bash
docker compose --profile tunnel up -d
```
Туннель будет работать постоянно и автоматически перезапускаться при сбоях.

---

## 7. Настройка Telegram Mini App в @BotFather


1. Перейдите в [@BotFather](https://t.me/BotFather).
2. Отправьте `/mybots` -> выберите вашего бота.
3. Перейдите в **Bot Settings** -> **Menu Button** -> **Configure menu button**.
4. Отправьте URL вашей веб-панели: `https://your-domain.com/app`
5. Введите название кнопки: `Панель управления`
6. Теперь у всех пользователей и администраторов в левом нижнем углу диалога с ботом появится кнопка вызова Mini App.

---

## 7. Рекомендации по лучшей практике (Best Practices)

1. **Добавление бота в группу**:
   - Добавьте бота в ваш чат и назначьте его **Администратором**.
   - Выдайте боту права:
     - Удаление сообщений (Delete Messages)
     - Блокировка пользователей (Ban/Restrict Users)
     - Закрепление сообщений (Pin Messages)
     - Пригласительные ссылки (Invite Users via Link)
2. **Первоначальная настройка чата**:
   - В чате отправьте команду `/settings` или откройте бота в ЛС `/start`.
   - В разделе «Фильтры» выберите желаемый режим принятия решений (по умолчанию «По шкале риска» со строгими реакциями на Скам и Спам).
   - Настройте режим жалоб `/report`: «Админам» (отправка карточек с кнопками в группу/журнал) или «Нейросеть» (мгновенная автоматическая блокировка).
3. **Экономия токенов**:
   - Благодаря встроенному эвристическому пре-фильтру `RiskScorer` сообщения постоянных участников с высоким траст-фактором не тратят токены LLM.
   - Все медиафайлы (фото, видео, стикеры) проверяются локальной ONNX моделью на CPU со стоимостью **0 токенов**.

---

## 8. Чеклист валидации и решения частых проблем

| Проблема | Причина | Решение |
| :--- | :--- | :--- |
| `HTTP 502 / Bad Gateway` в Mini App | Не запущен локальный сервер или упал туннель | Проверьте `docker compose ps` и убедитесь, что туннель проксирует на порт 2009. |
| Черный экран в WebApp | Проблемы с внешними CDN | В проекте все библиотеки локализованы в `webapp/vendor/`. Выполните жесткую перезагрузку (Clear Cache в Telegram). |
| Бот не удаляет спам | Нет прав администратора в группе | Проверьте список админов супергруппы и выдайте право "Delete Messages". |
| Ошибка `ONNX model not found` | Веса модели не успели загрузиться | При первом запуске модуль автоматически скачивает `open-nsfw.onnx` (23 МБ) с HuggingFace. Проверьте интернет-соединение. |
| Тесты не проходят | Не установлены dev-зависимости | Выполните `pip install -r requirements.txt` и запустите `pytest tests/ -v`. Все 49 тестов должны быть зелеными (`passed`). |
