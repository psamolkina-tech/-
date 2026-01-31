# Telegram Video Rewards Mini App

Telegram Mini App для просмотра видео с системой наград и скидок.

## Функционал

### Система звезд ⭐
- **Просмотр видео** - +1 звезда за просмотр 80% видео
- **Подписка на канал** - +1 звезда
- **Приглашение друга** - +1 звезда (реферальная система)

### Награда
- **3 звезды** = скидка **60 000 рублей**

## Структура проекта

```
├── backend/
│   ├── app.py           # FastAPI сервер
│   ├── database.py      # Конфигурация БД
│   ├── models.py        # SQLAlchemy модели
│   └── requirements.txt # Python зависимости
├── frontend/
│   ├── index.html       # Главная страница Mini App
│   ├── css/
│   │   └── style.css    # Стили
│   └── js/
│       └── app.js       # Клиентская логика
├── bot/
│   └── bot.py           # Telegram бот
├── .env.example         # Пример переменных окружения
└── README.md
```

## Установка и запуск

### 1. Создание бота

1. Откройте [@BotFather](https://t.me/BotFather) в Telegram
2. Создайте нового бота: `/newbot`
3. Скопируйте токен бота
4. Включите Mini App: `/newapp` -> выберите бота -> введите URL приложения

### 2. Настройка окружения

```bash
# Клонирование репозитория
git clone <repository-url>
cd telegram-video-rewards

# Копирование конфигурации
cp .env.example .env

# Редактирование .env
nano .env
```

Заполните переменные:
- `BOT_TOKEN` - токен от BotFather
- `CHANNEL_ID` - username канала (например, @mychannel)
- `WEBAPP_URL` - URL где размещено приложение
- `API_URL` - URL API сервера

### 3. Запуск бэкенда

```bash
cd backend

# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate     # Windows

# Установка зависимостей
pip install -r requirements.txt

# Запуск сервера
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### 4. Запуск бота

```bash
cd bot

# Активация окружения (если не активно)
source ../backend/venv/bin/activate

# Запуск бота
python bot.py
```

### 5. Размещение фронтенда

Для локальной разработки можно использовать встроенный сервер:

```bash
cd frontend
python -m http.server 3000
```

Для продакшена рекомендуется использовать:
- nginx
- Cloudflare Pages
- Vercel
- Netlify

## API Endpoints

### Аутентификация
- `POST /api/auth` - Регистрация/авторизация пользователя

### Пользователь
- `GET /api/user/{telegram_id}` - Получить профиль пользователя

### Видео
- `GET /api/videos?telegram_id={id}` - Список видео с прогрессом
- `POST /api/video/progress?telegram_id={id}` - Обновить прогресс просмотра

### Задания
- `POST /api/subscribe/check?telegram_id={id}` - Проверить подписку на канал

### Рефералы
- `GET /api/referral/stats?telegram_id={id}` - Статистика рефералов

### Скидка
- `POST /api/discount/claim?telegram_id={id}` - Получить скидку

## Добавление видео

Видео добавляются через базу данных. Пример SQL:

```sql
INSERT INTO videos (title, description, video_url, thumbnail_url, duration_seconds, reward_stars)
VALUES (
    'Название видео',
    'Описание видео',
    'https://example.com/video.mp4',
    'https://example.com/thumbnail.jpg',
    120,
    1
);
```

Или через Python:

```python
from models import Video
from database import async_session

async def add_video():
    async with async_session() as session:
        video = Video(
            title="Новое видео",
            description="Описание",
            video_url="https://example.com/video.mp4",
            thumbnail_url="https://example.com/thumb.jpg",
            duration_seconds=120,
            reward_stars=1
        )
        session.add(video)
        await session.commit()
```

## Настройка Mini App в BotFather

1. Откройте @BotFather
2. Выберите вашего бота
3. `/mybots` -> выберите бота -> `Bot Settings` -> `Menu Button`
4. Установите URL вашего Mini App

Или через команду `/setmenubutton`:
```
URL: https://your-domain.com
Button text: 🎬 Смотреть видео
```

## Деплой на сервер

### Docker (рекомендуется)

Создайте `docker-compose.yml`:

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./data:/app/data

  bot:
    build: ./bot
    env_file:
      - .env
    depends_on:
      - backend

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./frontend:/usr/share/nginx/html
      - ./nginx.conf:/etc/nginx/nginx.conf
```

### Ручной деплой

1. Установите Python 3.9+
2. Настройте nginx как reverse proxy
3. Используйте systemd для автозапуска сервисов
4. Получите SSL сертификат (Let's Encrypt)

## Безопасность

- Все запросы валидируются через Telegram initData
- Реферальные коды генерируются криптографически
- Награды начисляются только один раз за каждое действие
- Прогресс видео отслеживается на сервере

## Поддержка

По вопросам создавайте Issue в репозитории.

## Лицензия

MIT License
