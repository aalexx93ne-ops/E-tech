# E-Tech Store

Django-магазин электроники с каталогом, корзиной, заказами и личным кабинетом.

## Стек

- Python 3.10+
- Django 4.2
- django-allauth (email + Google OAuth)
- django-jazzmin (admin UI)
- HTMX (динамический UI без JS-фреймворков)
- SQLite (дев) / PostgreSQL (прод)

## Быстрый старт

### 1. Клонировать репозиторий

```bash
git clone https://github.com/aalexx93ne-ops/E-tech.git
cd E-tech
```

### 2. Создать и активировать виртуальное окружение

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate
```

### 3. Установить зависимости

```bash
pip install -r requirements.txt
```

### 4. Настроить переменные окружения

```bash
cp .env.example .env
```

Открыть `.env` и заполнить:

| Переменная | Описание |
|---|---|
| `SECRET_KEY` | Секретный ключ Django (обязательно) |
| `DEBUG` | `True` для разработки, `False` для продакшена |
| `ALLOWED_HOSTS` | Через запятую: `localhost,127.0.0.1` |
| `GOOGLE_CLIENT_ID` | ID приложения Google OAuth (опционально) |
| `GOOGLE_CLIENT_SECRET` | Секрет Google OAuth (опционально) |
| `EMAIL_BACKEND` | Бэкенд для email (дефолт: console) |

Сгенерировать `SECRET_KEY`:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 5. Применить миграции

```bash
python manage.py migrate
```

### 6. Создать суперпользователя

```bash
python manage.py createsuperuser
```

### 7. Запустить сервер разработки

```bash
python manage.py runserver
```

Магазин: http://127.0.0.1:8000
Админка: http://127.0.0.1:8000/admin

## Структура приложений

```
index/    — каталог товаров, категории, бренды, теги, фильтры
cart/     — корзина (сессионная для гостей, БД для авторизованных)
orders/   — оформление и история заказов
users/    — профиль пользователя, личный кабинет
appx/     — настройки проекта (settings.py, urls.py)
```

## Запуск тестов

```bash
python manage.py test cart orders
```

## Наполнение тестовыми данными

```bash
python generate_products.py
```

## Продакшен

Перед деплоем убедиться:

- `DEBUG=False` в `.env`
- `ALLOWED_HOSTS` содержит домен сайта
- `SECRET_KEY` — уникальный случайный ключ
- `EMAIL_BACKEND` настроен на SMTP
- Настроен веб-сервер (nginx + gunicorn)
- Выполнено `python manage.py collectstatic`
