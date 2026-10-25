# Zooffer

Zooffer — русскоязычная платформа для поиска животных, размещения объявлений, взаимных совпадений
и личной переписки. Один бэкенд обслуживает сайт на Next.js, Telegram-бота и Telegram Mini App.

Это локальная сборка: приложение реализовано и протестировано, а внешние интеграции, которым нужны
ключи и доступы (живой Telegram-бот, реальные платежи, SMTP, продакшен-хостинг), перечислены в
[docs/BLOCKERS.md](docs/BLOCKERS.md). Мы не выдаём непроверенное за работающее.

## Стек

| Слой | Технологии |
|---|---|
| Бэкенд | Python 3.12, FastAPI, SQLAlchemy 2 (async), Alembic, PostgreSQL 16 |
| Кэш и очередь | Redis 7 |
| Сайт и Mini App | Next.js 16 App Router, React 19, TypeScript, обычный глобальный CSS |
| Бот | aiogram 3, общие сервисы `zooffer` |
| Тесты | pytest + httpx ASGI, отдельная тестовая база PostgreSQL |

## Быстрый старт (Windows, локально)

1. Запустите PostgreSQL и Redis:

   ```powershell
   docker compose -f compose.dev.yaml up -d
   ```

2. Скопируйте `.env.example` в `.env` и задайте локальные секреты. `.env` не коммитится.

3. Установите зависимости и примените миграции:

   ```powershell
   .venv\Scripts\python -m pip install -e "backend[dev]"
   $env:PYTHONPATH='backend'
   .venv\Scripts\python -m alembic -c backend\alembic.ini upgrade head
   ```

4. Заполните демо-данные (необязательно):

   ```powershell
   $env:PYTHONPATH='backend'
   .venv\Scripts\python scripts\seed_dev.py
   ```

   Пароль демо-аккаунтов: `ZoofferDemo2026!`. Фотографии — сгенерированные заглушки, а не реальная
   съёмка животных.

5. Запустите API и сайт в разных терминалах:

   ```powershell
   $env:PYTHONPATH='backend'
   .venv\Scripts\python -m uvicorn zooffer.main:app --host 127.0.0.1 --port 8000
   ```

   ```powershell
   cd web
   npm install
   npm run dev
   ```

   Сайт: <http://localhost:3000>. Маршруты Mini App — в разделе `/tg`.

## Проверка

```powershell
.\scripts\ci.ps1
```

Скрипт повторяет проверки CI: ruff, mypy, pytest на PostgreSQL, `tsc`, ESLint и production-сборку
Next.js. Подробные результаты и известные ограничения — в [docs/TEST_REPORT.md](docs/TEST_REPORT.md)
и [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md).

## Приватность и безопасность

- Сессии в HttpOnly-cookie, HMAC-хэши токенов, CSRF double-submit и проверка Origin.
- Приватные данные вынесены в отдельную зашифрованную таблицу; публичные DTO — по allowlist.
- Другие пользователи видят только имя, необязательную фамилию или «Владелец». Контакты,
  внутренние идентификаторы, Telegram ID/username, фотографии и онлайн-статус не раскрываются.
- Дневная квота свайпов едина для сайта, бота и Mini App и проверяется на сервере.

Подробнее: [docs/PRIVACY_MODEL.md](docs/PRIVACY_MODEL.md),
[docs/THREAT_MODEL.md](docs/THREAT_MODEL.md), [docs/SECURITY_REPORT.md](docs/SECURITY_REPORT.md).

## Статус

Локально проверено: доменная модель и API, сайт, интерфейс Mini App, логика бота с фейками,
админка и модерация, жалобы, MFA, биллинг с фейковым провайдером. Заблокировано внешними доступами:
живой Telegram, реальные платежи, доставка писем, продакшен-хостинг. Актуальная таблица статусов —
в [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md).

## Лицензия

Проприетарный проект, все права защищены. См. [LICENSE](LICENSE). Юридические шаблоны находятся в
[docs/legal](docs/legal) и требуют проверки квалифицированным юристом.
