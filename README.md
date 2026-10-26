![Zooffer — забота в каждой встрече](docs/assets/banner.svg)

# Zooffer

[![CI](https://github.com/devilnevecry/Zooffer_final/actions/workflows/ci.yml/badge.svg)](https://github.com/devilnevecry/Zooffer_final/actions/workflows/ci.yml)
[![version](https://img.shields.io/github/v/tag/devilnevecry/Zooffer_final?label=version&sort=semver)](https://github.com/devilnevecry/Zooffer_final/tags)
[![licence](https://img.shields.io/badge/licence-proprietary-00539c)](LICENSE)

Zooffer — русскоязычная платформа для поиска животных, размещения объявлений, взаимных совпадений и личной переписки. Один бэкенд на FastAPI обслуживает сайт на Next.js, Telegram-бота и Telegram Mini App.

Приватность обеспечивается на уровне схемы: другие пользователи видят публичное имя, опциональную фамилию или «Владелец» — никогда контакты, внутренние идентификаторы, Telegram ID/username, фотографии или онлайн-статус.

Это локальная сборка. Основной функционал реализован и проверен на PostgreSQL. Внешние интеграции, которым нужны ключи и инфраструктура (живой Telegram, реальные платежи, доставка почты, продакшен-хостинг и объектное хранилище), вынесены в отдельные блокеры — ничего не заявлено как работающее, чего не запускали.

## Возможности

### Подбор и совпадения
- Пять целей объявлений, полнотекстовый поиск, фильтры, ключовая пагинация
- Лента со свайпами и общая дневная квота для сайта, бота и Mini App
- Совпадение создаётся только при взаимном лайке внутри одной транзакции

### Объявления и профили животных
- Мастер создания объявления с возможностью продолжения
- Профили животных
- Конвейер фотографий: проверка контента, лимиты размера, удаление EXIF
- Очередь модерации и обработка жалоб

### Личная переписка
- Диалог открывается только по явному запросу, а не по лайку
- Блокировки, жалобы, настройки уведомлений и тихие часы

### Аккаунты и приватность
- Вход по паролю и через Telegram
- Верификация и сброс почты
- Сессии с HMAC-хэшем токенов, защита CSRF
- MFA для персонала
- Удаление аккаунта и экспорт данных

### Админка
- Модерация, жалобы, пользователи, тикеты поддержки, аудит-лог
- Настройки, заказы на оплату, возвраты, выдача прав
- Каждый эндпоинт требует RBAC и верифицированную сессию MFA

### Биллинг
- Интерфейс `PaymentProvider` с детерминистичным фейковым провайдером для разработки
- Цены на сервере, подписанные вебхуки, идемпотентная обработка событий
- Отмена подписки и доступ до конца периода
- YooKassa и Telegram Stars отключены до появления реальных ключей

| Поиск | Объявление |
|---|---|
| ![Поиск с фильтрами](docs/assets/search.webp) | ![Карточка объявления](docs/assets/listing.webp) |

| Подписка | Админ-платежи | Mini App |
|---|---|---|
| ![Управление подпиской](docs/assets/subscription.webp) | ![Админ-платежи](docs/assets/admin-payments.webp) | ![Telegram Mini App](docs/assets/miniapp.webp) |

## Архитектура

```mermaid
flowchart LR
  subgraph Clients
    W[Next.js website<br/>SSR + app]
    M[Telegram Mini App<br/>/tg routes]
    B[Telegram bot<br/>aiogram 3]
  end
  A[FastAPI API<br/>shared service layer]
  DB[(PostgreSQL 16)]
  R[(Redis 7)]
  FS[(Local media<br/>dev only)]
  T[Telegram Bot API]
  Y[YooKassa<br/>adapter, blocked]
  W --> A
  M --> A
  B --> A
  A --> DB
  A --> R
  A --> FS
  A --> T
  A -.-> Y
```

Бот использует те же доменные сервисы, что и сайт и Mini App, вместо дублирования правил. Сайт и Mini App вызывают HTTP API. Весь авторитетный результат хранится в PostgreSQL; клиенты не хранят важного состояния. Нет fallback на SQLite.

## Стек технологий

| Слой | Технологии |
|---|---|
| Бэкенд | Python 3.12, FastAPI 0.115, SQLAlchemy 2 (async), Alembic, PostgreSQL 16 |
| Кэш и лимиты | Redis 7 (с локальным fallback для одной dev-процесса) |
| Сайт и Mini App | Next.js 16 App Router, React 19, TypeScript, глобальный CSS |
| Бот | aiogram 3, подписанные колбэки, вебхук или long-polling |
| Тесты | pytest + httpx ASGI, отдельная тестовая база PostgreSQL |
| CI | GitHub Actions: ruff, mypy, pytest, tsc, ESLint, сборка, bandit, gitleaks |

## Структура проекта

```text
backend/   FastAPI приложение, SQLAlchemy модели, миграции Alembic, тесты
bot/       aiogram бот, подписанные колбэки, работник уведомлений
web/       Next.js сайт и /tg Mini App
docs/      архитектура, ADR, приватность, платежи, runbook, доказательства
infra/     скрипт инициализации PostgreSQL для локального Compose
scripts/   заполнение демо-данных, локальный CI, операционные утилиты
legacy/    справочные материалы только для чтения, в gitignore, не импортируются
```

## Быстрый старт (Windows, локально)

1. Запустите PostgreSQL и Redis:
   ```powershell
   docker compose -f compose.dev.yaml up -d
   ```

2. Скопируйте `.env.example` в `.env` и задайте локальные секреты. `.env` в gitignore.

3. Установите зависимости и примените миграции:
   ```powershell
   .venv\Scripts\python -m pip install -e "backend[dev]"
   $env:PYTHONPATH='backend'
   .venv\Scripts\python -m alembic -c backend\alembic.ini upgrade head
   ```

4. Заполните демо-данные (по желанию):
   ```powershell
   $env:PYTHONPATH='backend'
   .venv\Scripts\python scripts\seed_dev.py
   ```
   Пароль демо: `ZoofferDemo2026!`. Аккаунты: `anna@example.com`, `mikhail@example.com` и другие.

5. Запустите API:
   ```powershell
   $env:PYTHONPATH='backend'
   .venv\Scripts\python -m uvicorn zooffer.main:app --host 127.0.0.1 --port 8000
   ```

6. Запустите сайт:
   ```powershell
   cd web
   npm install
   npm run dev
   ```
   Откройте <http://localhost:3000>. Mini App — в разделе `/tg`.

7. Бот (по желанию, нужен `TELEGRAM_BOT_TOKEN`):
   ```powershell
   $env:PYTHONPATH='backend;bot'
   $env:BOT_MODE='polling'
   .venv\Scripts\python -m zooffer_bot
   ```

## Статус реализации

| Направление | Статус | Где проверить |
|---|---|---|
| Доменная модель, API, приватность | ✅ Проверено | 74 pytest-теста, включая privacy canaries и IDOR |
| Сайт, личный кабинет, админ UI | ✅ Проверено | typecheck, lint, production-сборка, QA 390/1280 px |
| Экраны Mini App | ⚠️ Реализовано, не проверено вживую | `/tg/*` рендерится локально; нужен токен бота |
| Логика бота и уведомления | ⚠️ Реализовано, не проверено вживую | `test_bot.py` с фейками; нужен B2 |
| Демо-биллинг (фейковый провайдер) | ✅ Проверено | `test_payments.py`; чек-аут → активация → возврат |
| YooKassa | ⚠️ Код есть | нет sandbox-ключей (B4) |
| Telegram Stars | 🔒 Заблокировано | нет бота/merchant (B5) |
| Почта | 🔒 Заблокировано | нет SMTP (B6); локально консольный адаптер |
| Продакшен-хостинг и медиа-хранилище | 🔒 Заблокировано | нет хоста/домена (B7), объектного хранилища (B9) |
| E2e и нагрузочные тесты | ⏳ Не начато | ручная QA; нет нагрузочного теста квоты |

Актуальная таблица — в [docs/REQUIREMENTS_TRACEABILITY.md](docs/REQUIREMENTS_TRACEABILITY.md).

## Безопасность и приватность

- Сессии в HttpOnly-куки, токены с HMAC-SHA256, ротация при смене привилегий, отзыв по устройствам.
- CSRF double-submit и проверка Origin; защита от IDOR на каждом приватном ресурсе.
- Приватные данные в отдельной зашифрованной таблице со слепым индексом; публичные DTO по allowlist; canary-тесты на утечки.
- Валидация загрузок, перекодирование и серверные имена файлов.
- RBAC для персонала и обязательная сессия MFA; аудит-лог админских действий.
- Вебхуки оплат проверяются, защищены от повторов и сверяются по сумме.

Подробнее: [docs/PRIVACY_MODEL.md](docs/PRIVACY_MODEL.md) · [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md) · [docs/SECURITY_REPORT.md](docs/SECURITY_REPORT.md).

## Платежи

Демо-оформление заказа работает только при `PAYMENT_PROVIDER=fake` и окружении `dev`/`test`; интерфейс помечает его как имитацию, денег не перечисляется. Бот и Mini App не предлагают оплату картами — Telegram Stars не подключён. См. [docs/PAYMENTS.md](docs/PAYMENTS.md).

## Документация

Начните с [docs/README.md](docs/README.md). Главное:
- [Архитектура](docs/ARCHITECTURE.md) · [ADR и решения](docs/DECISIONS.md)
- [Модель приватности](docs/PRIVACY_MODEL.md) · [Модель угроз](docs/THREAT_MODEL.md)
- [Платежи](docs/PAYMENTS.md) · [Интеграция с Telegram](docs/TELEGRAM.md)
- [Отчёт безопасности](docs/SECURITY_REPORT.md) · [Отчёт тестирования](docs/TEST_REPORT.md)
- [Runbook](docs/RUNBOOK.md) · [Блокировки](docs/BLOCKERS.md) · [Известные проблемы](docs/KNOWN_ISSUES.md)
- [Вклад в проект](CONTRIBUTING.md) · [Политика безопасности](SECURITY.md) · [История изменений](CHANGELOG.md)

## Лицензия

Проприетарный проект, все права защищены — см. [LICENSE](LICENSE). Юридические шаблоны в [docs/legal](docs/legal) требуют проверки квалифицированным российским юристом. Реквизиты оператора — заглушки, пока владелец не предоставит реальные данные (B8).
