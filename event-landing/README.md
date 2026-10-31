# Лендинг — «Сила партнерства для бизнеса»

Закрытое мероприятие Т-Банка для партнеров · 2 декабря · Svoy Яуза.

Премиальный лендинг с рабочей регистрационной формой, хранением данных в SQLite,
выгрузкой гостей в CSV/Excel и JSON-эндпоинтом для интеграции с CRM.

Стек: **Python 3.9 + Flask + SQLite + openpyxl** · чистый HTML/CSS/JS (без шаблонных фреймворков).

---

## Запуск

```bash
cd landing
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```

Открыть:
- Лендинг — http://127.0.0.1:8000
- Админ-панель (список гостей) — http://127.0.0.1:8000/admin
  логин `admin` / пароль `admin123`
- Политика конфиденциальности — http://127.0.0.1:8000/privacy

## Структура

```
landing/
├── app.py                 # Flask-приложение: страницы, API, экспорт, админка
├── db.py                  # SQLite-слой (параметризованные запросы)
├── requirements.txt
├── data/registrations.db  # база данных (создается автоматически)
├── templates/
│   ├── index.html         # лендинг
│   ├── admin.html         # список гостей
│   └── privacy.html       # политика конфиденциальности
└── static/
    ├── css/style.css      # премиальный дизайн (Т-Банк · Т-Бизнес)
    ├── js/main.js         # валидация формы, анимации, отправка
    └── img/kv.png         # ключевой визуал (KV) в шапке
```

## Возможности

- **Форма регистрации**: имя, фамилия, компания, должность, телефон, e-mail,
  комментарии, обязательное согласие на обработку ПДн + ссылка на политику.
  Клиентская и серверная валидация (телефон, e-mail, обязательные поля),
  защита от повторной отправки, экран подтверждения после успеха.
- **База данных**: SQLite, параметризованные запросы (без SQL-инъекций).
- **Выгрузка**: `/admin/export.csv` и `/admin/export.xlsx` (с форматированием).
- **CRM-интеграция**: `GET /api/registrations` возвращает JSON списка гостей
  (защищен админ-доступом).
- **Безопасность**: серверная валидация, ограничение частоты запросов
  (rate limit по IP), администратор через HTTP Basic, PII не логируется,
  CSRF-легкая защита (SameSite + уникальный SECRET_KEY).

## Ключевой визуал (KV) в шапке

В hero-секции справа выводится KV-изображение `static/img/kv.png`
(ваш файл, 1920×1080). Чтобы заменить его на другой, положите новый файл
как `landing/static/img/kv.png` (или поменяйте путь в `templates/index.html`).

## Настройка для продакшна

Задайте переменные окружения перед запуском:

```bash
export SECRET_KEY="<длинная случайная строка>"
export ADMIN_USER="admin"
export ADMIN_PASSWORD="<надежный пароль>"
export EVENT_DB_PATH="/путь/к/registrations.db"
```

- **Безопасность ПДн**: данные хранятся в открытом виде (нужны для выгрузки/CRM).
  В продакшне ограничьте доступ к файлу БД и файловой системе; при требовании
  политики — шифруйте поля на уровне приложения.
- **Публикация**: запустите через WSGI-сервер (gunicorn/uwsgi) за HTTPS-прокси.
  Для высоких нагрузок замените `_attempts` (rate limit в памяти) на Redis.
- **CRM**: `/api/registrations` готов к подключению; добавьте токен авторизации
  и маппинг полей под целевую систему.

## Деплой на хостинг

В проекте готовы файлы для production: `Dockerfile`, `Procfile`, `.env.example`,
`gunicorn` в `requirements.txt`. База — SQLite (файл `EVENT_DB_PATH`), поэтому на
хостинге обязательно примонтируйте персистентный **volume** к `/data`, иначе
регистрации будут теряться при каждом перезапуске.

**Вариант A — Docker (Render, Railway, Fly.io, любой VPS с docker):**
```bash
docker build -t event-landing .
docker run -p 8000:8000 \
  -e SECRET_KEY="$(openssl rand -hex 32)" \
  -e ADMIN_PASSWORD="$(openssl rand -hex 16)" \
  -v event_data:/data \
  event-landing
```

**Вариант B — PaaS по `Procfile` (Render / Railway / Fly.io):**
- выберите Python-рантайм, команда уже в `Procfile`;
- задайте env: `SECRET_KEY`, `ADMIN_USER`, `ADMIN_PASSWORD`;
- подключите персистентный диск и укажите `EVENT_DB_PATH` на нём (например `/data/registrations.db`).

**Вариант C — VPS (gunicorn + nginx):**
```bash
.venv/bin/pip install -r requirements.txt
EVENT_DB_PATH=/var/lib/event/registrations.db \
SECRET_KEY=... ADMIN_PASSWORD=... \
.venv/bin/gunicorn --bind 127.0.0.1:8000 --workers 2 app:app
```
и прокинуть 8000 через nginx с HTTPS (certbot).

После деплоя:
- Лендинг — `/` ; админка — `/admin` (логин/пароль из env).
- Выгрузка гостей — `/admin/export.csv` и `/admin/export.xlsx`.
- CRM JSON — `/api/registrations` (требует admin-auth).

## Дизайн

Светлая премиальная тема в фирменной палитре суббренда Т-Бизнес:
кремовый фон `#FFF9ED` (Pantone 7604 C), темный текст `#333333`
(Pantone Black 6 C), фирменный бежевый `#E4D7C1` и теплый оранжевый акцент
`#E8913B`. Крупная редакционная типографика (Inter), минималистичные анимации
появления при прокрутке, полная адаптивность (десктоп / планшет / мобильные).
Вдохновлено событийным лендингом summer.t-bankbusiness.ru.