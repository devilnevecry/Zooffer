# Полный аудит проекта Zooffer

> Аудит выполнен по состоянию на 24.11.2026. Проект расположен в `C:\Users\nu11\Documents\GitHub\Zooffer`, живой экземпляр запущен на `http://localhost:3000/`. Источник кода доступен локально (монорепозиторий), git-репозиторий в рабочей папке отсутствует (`.git` не найден), удалённый репозиторий — `https://github.com/devilnevecry/Zooffer_final`. Аудит охватывает код (backend/bot/web), документацию, CI/CD, безопасность, приватность, платежи, Telegram-интеграции и живой сайт.

## 0. Краткое резюме

**Zooffer** — русскоязычная платформа для поиска животных, размещения объявлений (продажа, вязка, племенное разведение, пристройство), взаимных совпадений (match) и личной переписки. Один бэкенд на FastAPI обслуживает сайт на Next.js, Telegram-бота (aiogram 3) и Telegram Mini App (`/tg`). Ключевая фишка — privacy by design: другие пользователи видят только имя/фамилию или «Владелец», никогда контакты, внутренние ID, Telegram ID/username, фото или онлайн-статус. Доменная модель, API, приватность и сайт проверены (74 pytest, typecheck, lint, production-сборка, 56 маршрутов). Живые внешние интеграции (Telegram, реальные платежи, SMTP, продакшен-хостинг, S3) заблокированы отсутствием ключей/инфраструктуры. Проект проприетарный, лицензия — proprietary.

## 1. Общая информация

- **Название**: Zooffer («забота в каждой встрече»)
- **Репозиторий**: `https://github.com/devilnevecry/Zooffer_final`
- **Локальный путь**: `C:\Users\nu11\Documents\GitHub\Zooffer`
- **Живой сайт**: `http://localhost:3000/` (dev)
- **API**: `http://localhost:8000` (FastAPI)
- **Mini App**: `/tg`
- **Telegram-бот**: `@zooffer_bot` (по умолчанию, настраивается)
- **Telegram-канал**: `@zooffer`
- **Лицензия**: proprietary (все права защищены), см. `LICENSE`
- **Версия web**: 0.1.0 (`web/package.json`)
- **Авторы**: `CODEOWNERS` (проверить), контрибьюторы через PR

## 2. Структура монорепозитория

```
Zooffer/
├── backend/        FastAPI app, SQLAlchemy модели, Alembic-миграции, тесты
├── bot/            aiogram 3 бот, подписанные колбэки, воркер уведомлений
├── web/            Next.js App Router (сайт + /tg Mini App)
├── docs/           архитектура, ADR, приватность, платежи, runbook, отчёты
├── infra/          production compose, Caddyfile, env-примеры, init postgres
├── scripts/        seed_dev/prod, bootstrap_admin, ci.ps1
├── legacy/         справочные материалы (gitignore, не импортируются)
├── .github/        workflows (ci.yml, release.yml), issue/PR templates, dependabot
├── compose.dev.yaml
├── Dockerfile
├── .env.example
├── README.md / README.ru.md
├── CONTRIBUTING.md / SECURITY.md / CHANGELOG.md / LICENSE
```

## 3. Технологический стек

| Слой | Технологии |
|---|---|
| Бэкенд | Python 3.12, FastAPI 0.115→0.162, SQLAlchemy 2 (async), Alembic, PostgreSQL 16 |
| Кэш/лимиты/очередь | Redis 7 (с локальным fallback для одного dev-процесса) |
| Сайт и Mini App | Next.js 16 App Router, React 19, TypeScript, глобальный CSS |
| Бот | aiogram 3, подписанные колбэки, webhook или long-polling |
| Тесты | pytest + httpx ASGI, отдельная тестовая БД PostgreSQL |
| CI | GitHub Actions: ruff, mypy, pytest, tsc, ESLint, build, bandit, gitleaks |
| Шрифты | @fontsource/onest, @fontsource/unbounded |
| Медиа | Pillow (re-encode WebP, strip EXIF/GPS), локальный диск (dev) |
| Безопасность паролей | Argon2id |
| Шифрование | cryptography (encrypted private-data table, HMAC blind index) |
| Наблюдаемость | structured JSON logs (request/correlation IDs), Prometheus metrics, `/healthz`, `/readyz` |
| Прокси (prod) | Caddy (TLS, HSTS, CSP, request limits) — не настроен |
| Контейнеры | non-root, read-only FS где возможно |

## 4. Архитектура

- **Модульный монолит**: один FastAPI-бэкенд, общая доменная/сервисная прослойка. Бот импортирует те же сервисы, а не дублирует правила. Сайт и Mini App вызывают HTTP API.
- **Весь авторитетный результат — в PostgreSQL**; клиенты не хранят важного состояния. Нет fallback на SQLite.
- **Слои бэкенда**: API (Pydantic v2 валидация, permissions, явные response-схемы; ORM-объекты не сериализуются) → Services (транзакции, инварианты) → Repositories/queries (доступ к данным). Публичные read-пути проецируются в DTO из allowlisted-колонок, никогда не join `user_private_data`.
- **Идентичность**: одна `users`-строка — каноническая. `auth_identities` маппит провайдеров (`password`, `telegram`) на пользователя; Telegram использует numeric user ID, никогда username. Сессии — случайные 256-бит токены в HttpOnly-cookie; хранится только HMAC-SHA256-хэш. Idle/absolute expiry, ротация при логине и смене привилегий, отзыв по устройствам. CSRF — SameSite=Lax + double-submit token + Origin validation.
- **Приватность**: приватные поля только в `user_private_data`/`credentials`/`auth_identities`/`payment_*`/`documents`. Каждый публичный ответ — явная Pydantic-модель с allowlisted-полями, контракт-тест. Публичные идентификаторы — opaque UUID + транслитерированные slug. Canary-сьют сажает уникальные сантинелы в приватные поля и сканирует API, HTML, RSC-пейлоады, метаданные, sitemap, сообщения бота и уведомления. `owner_display_name` — единственное поле идентичности владельца в публичных DTO (имя + опциональная фамилия, или `null` → «Владелец»).
- **Квоты и matching**: `daily_quota_usage` keyed by `(user_id, quota_date)` (локальная дата Europe/Moscow). Swipe в одной транзакции: `INSERT ... ON CONFLICT DO UPDATE ... WHERE used_count < limit RETURNING used_count` + unique `(user_id, target_type, target_id)` swipe constraint + idempotency key. Matching в той же транзакции, каноническая упорядоченная пара животных, unique index — параллельные лайки не создают дублей/пропусков. Откат (undo) требует entitlement, восстанавливает 1 юнит квоты.
- **Медиа**: `MediaStorage` protocol с локальным адаптером (dev/test). Загрузки sniff'ятся по контенту, лимиты размера/пикселей, re-encode Pillow (strip EXIF/GPS, удаление embedded payload), запись под серверными ключами. S3-адаптер и signed URL для приватных документов **не реализованы** (блокер B9).
- **Наблюдаемость**: structured JSON logs с request/correlation IDs и PII-минимизацией, Prometheus-метрики на защищённом эндпоинте, `/healthz`, `/readyz`. Продакшен — за Caddy (TLS, HSTS, CSP, лимиты) — не настроен (B7). Контейнеры non-root, read-only FS где возможно.

## 5. Функциональные модули

### 5.1. Подбор и совпадения (discovery/matching)
- 5 целей объявлений (продажа, вязка, племенное разведение, пристройство, +?), полнотекстовый поиск, фильтры, keyset-пагинация.
- Лента со свайпами, общая дневная квота для сайта/бота/Mini App (20 по умолчанию).
- Совпадение создаётся только при взаимном лайке в одной транзакции.
- Избранное (idempotent add/remove, owner-scoped), undo (требует entitlement).

### 5.2. Объявления и профили животных
- Мастер создания объявления с возможностью продолжения (draft → publish).
- Профили животных (animal-manager).
- Конвейер фото: проверка контента, лимиты размера, удаление EXIF.
- Очередь модерации, обработка жалоб.
- Публикация требует ≥1 фото; контактные данные ведут в `pending_moderation`.

### 5.3. Личная переписка (messaging)
- Диалог открывается только по явному запросу, а не по лайку.
- Блокировки, жалобы, настройки уведомлений, тихие часы.
- Участие в беседе, порядок, пагинация, уникальность жалоб на сообщение.

### 5.4. Аккаунты и приватность
- Вход по паролю и через Telegram (Login Widget, Mini App initData).
- Верификация и сброс почты (токены хэшируются, enumeration-resistant ответы, отзыв сессий).
- Сессии с HMAC-хэшем токенов, защита CSRF.
- MFA (TOTP) для персонала.
- Удаление аккаунта и экспорт данных (`GET /api/v1/account/export`, `DELETE /api/v1/account`).
- Настройки приватности, уведомлений.

### 5.5. Админка
- Модерация, жалобы, пользователи, тикеты поддержки, аудит-лог.
- Настройки, заказы на оплату, возвраты, выдача прав.
- Каждый эндпоинт требует RBAC и верифицированную MFA-сессию.
- Ручная выдача entitlement (audited), сверка платежей.

### 5.6. Биллинг (payments)
- Интерфейс `PaymentProvider` с детерминистичным фейковым провайдером (dev/test).
- Провайдеры: fake (dev/test), YooKassa (adapter, blocked B4), Telegram Stars (blocked B5), Robokassa (adapter), Crypto wallet (additional path, B10).
- Серверные цены (kopecks), подписанные вебхуки, идемпотентная обработка событий.
- Отмена подписки, доступ до конца периода.
- Upgrade/downgrade с пересчётом неиспользованного времени.
- Нет silent auto-renewal — новый платёж на каждый период.
- Демо-флоу: create order → checkout → demo-confirm → активация; replay idempotent.
- Планы с `is_placeholder_price`; продакшен отклоняет placeholder-цены.

### 5.7. Telegram-интеграция
- Бот (aiogram 3) + Mini App (`/tg` маршруты).
- Подписанные колбэки, webhook или long-polling.
- Воркер уведомлений (in-process, non-durable).
- Onboarding, deep links, валидация webhook.
- Mini App: discovery, listings, listing, favorites, matches, chats, chat, profile, partners, search, support, subscription.
- Telegram Stars: invoice flow, pre-checkout validation, idempotent activation, refund (blocked B5).
- Telegram Login Widget на сайте.

### 5.8. Медиа и загрузки
- Sniff по контенту, лимиты размера/пикселей, re-encode WebP, strip EXIF/GPS.
- SVG/text/empty/oversized отклоняются.
- Приватные документы не роутятся через `/media`; path traversal заблокирован.
- Только локальный диск (B9).

### 5.9. Админ/модерация/жалобы
- Жалобы на listing/animal/message/user; правила участия и уникальности.
- Rate limits на сообщения/жалобы/тикеты поддержки.
- Аудит-лог админских действий.

### 5.10. Уведомления
- In-app фильтрация по предпочтениям, тихие часы.
- Push через Telegram (бот).
- Модерационные/поддержочные уведомления.

### 5.11. Партнёры (реклама)
- `PartnerOffer.erid`, `ad_label`; UI показывает метку рекламы.
- Поля для маркировки по 38-ФЗ (erid).
- Zero-partner empty state.

### 5.12. Юридические документы
- Шаблоны в `docs/legal/` (rules, terms, privacy, personal-data, requisites, offer).
- Реквизиты оператора — заглушки (B8).

## 6. API (маршруты)

Полный список эндпоинтов — в `docs/PAYMENTS.md` и `backend/zooffer/api/v1/`. Основные группы:
- `/api/v1/auth` — register/login/logout/telegram/email-verify/reset/consent
- `/api/v1/account` — me, settings, animals, listings, favorites, matches, chats, notifications, export, delete
- `/api/v1/listings`, `/api/v1/animals` — CRUD объявлений и животных
- `/api/v1/discovery` — feed, swipe, undo, favorites
- `/api/v1/messaging` — conversations, messages, blocks, reports
- `/api/v1/media` — upload, serve
- `/api/v1/reports` — user reports
- `/api/v1/notifications` — prefs, list
- `/api/v1/billing` — plans, subscription, orders, demo-confirm, webhooks, cancel
- `/api/v1/admin/*` — moderation, users, reports, support, settings, payments, audit, entitlements
- `/api/v1/public/plans`
- System: `/healthz`, `/readyz`, `/metrics` (protected), `/api/docs`

## 7. База данных (модели)

Модели в `backend/zooffer/db/models/`: user, animal, listing, discovery, messaging, billing, quota, partner, geo, system. Ключевые таблицы: `users`, `auth_identities`, `user_private_data`, `credentials`, `animals`, `listings`, `listing_photos`, `swipes`, `daily_quota_usage`, `matches`, `conversations`, `messages`, `notifications`, `plans`, `subscriptions`, `orders`, `payment_events`, `reports`, `audit_log`, `support_tickets`, `partner_offers`, `consents`, `geo`.

## 8. Веб-приложение (Next.js)

- **Маршруты (56)**: главная, discovery, search, catalog/[purpose], listing/[slug], account/* (animals, listings, favorites, matches, chats, notifications, settings, subscription, checkout), admin/* (moderation, users, reports, support, settings, payments, audit), legal/*, login, register, forgot/reset-password, verify-email, partners, support, tg/* (Mini App).
- **Компоненты**: ~70 (site-header/footer, tab-bar, auth, listing-card/wizard/manager/gallery, discovery-deck, chat-panel, checkout, notification-center, settings-panel, search-*, admin/*, miniapp/* и др.).
- **Output**: standalone (Docker).
- **Rewrites**: `/api/:path*` и `/media/:path*` → backend.
- **Fonts**: Onest, Unbounded (fontsource).
- **SEO**: sitemap.ts, robots.ts, opengraph-image.tsx.

## 9. Бот (aiogram 3)

- Структура: `bot/zooffer_bot/` с handlers (start, menu, discovery, listings, favorites, chats, payments, support, widgets, fallback, common), keyboards, states (FSM), services, middlewares, notifications, polling, webhook, dispatcher, config, texts, callbacks.
- Режимы: polling (dev) / webhook (prod).
- Throttling: per-user 25/10s, global 200/10s.
- FSM TTL 3600s.
- Воркер уведомлений: batch 20, interval 15s, max age 24h.
- Исключён из mypy (aiogram union narrowing).

## 10. CI/CD

- **GitHub Actions**: `.github/workflows/ci.yml`, `release.yml`.
- **Локальный гейт**: `scripts/ci.ps1` (PowerShell).
- **Проверки**: ruff lint+format, mypy (71 файлов), bandit (SAST), pytest (74, PostgreSQL), tsc, eslint, prettier, next build (56 routes), pip-audit, npm audit, gitleaks (Docker).
- **Dependabot**: `.github/dependabot.yml`.
- **Templates**: issue (bug/feature/security), PR template, CODEOWNERS.
- **B1**: remote presentation/PRs/releases/milestones не настроены (нет gh CLI/token); локально CI проходит, remote получил main+tags 2026-10-25.

## 11. Безопасность (Security Report)

- **Автотесты**: 74 pytest passed; ruff, mypy, bandit, eslint, tsc, prettier, build — PASS; pip-audit/npm audit — 0 vulnerabilities; gitleaks — no leaks.
- **Контроли**: Argon2id, HttpOnly cookie sessions, HMAC-hashed tokens, idle/absolute expiry, rotation, CSRF double-submit + Origin, TOTP MFA для staff (требуется `user.mfa_enabled` AND `session.mfa_verified_at`), replay protection Telegram Login/initData, single-use link tokens.
- **Авторизация**: фильтрация по владельцу, foreign → 404, RBAC через `permission_required(...)`.
- **Инпут/загрузки**: Pydantic `extra="forbid"`, content-sniff, pixel/size limits, re-encode WebP, EXIF strip, SVG/text/empty/oversized отклоняются, приватные документы не роутятся через `/media`, path traversal заблокирован.
- **Приватность**: отдельная зашифрованная таблица + HMAC blind index, public DTO allowlists, canary-сьют.
- **Квоты**: атомарный PostgreSQL update, swipe idempotency, unique match constraint.
- **Сообщения/абьюз**: участие в беседе, блоки, rate limits, уникальность жалоб.
- **Платежи**: серверные цены, HMAC-signed fake webhooks, dedup по `(provider, provider_event_id)`, amount/currency checks, ownership, YooKassa re-fetch, refund/revoke, admin audit.
- **Остаточные риски**: live Telegram/payment unverified (R1), unsigned YooKassa notifications + IP allow-list (R2), нет load/concurrency/ZAP/container scan (R3/R4), in-process non-durable bot queue (R5), legal templates (R6), aiogram typing не enforced mypy (R9).
- **Hardening checklist**: strong secrets, COOKIE_SECURE, HTTPS/HSTS/CSP, IP allow-list, secret rotation, container scanning, alerting, ZAP baseline, legal review.

## 12. Приватность (Privacy Model)

- Публичные DTO по allowlist; `owner_display_name` — имя + опц. фамилия или «Владелец».
- Приватные данные в отдельной зашифрованной таблице со слепым индексом.
- Canary-сьют: сантинелы в приватных полях, сканирование API/HTML/RSC/sitemap/bot/notifications.
- Оpaque UUID + транслитерированные slug в URL.
- Экспорт и удаление аккаунта, согласие версионируется.
- Геолокация: только город/район (ячейка ~1 км), без точных координат в подборе.
- Медиа: EXIF/GPS strip, серверные ключи.

## 13. Блокеры (B1–B10)

| # | Пункт | Статус | Чего не хватает |
|---|---|---|---|
| B1 | GitHub remote presentation/PRs/releases/milestones/CI | IMPLEMENTED-UNVERIFIED | gh CLI/token |
| B2 | Live Telegram bot | READY-FOR-CONFIG | реальный токен |
| B3 | Telegram Login/Mini App live auth | READY-FOR-CONFIG | токен, short name, /setdomain |
| B4 | YooKassa production | OPTIONAL/BLOCKED | shop id, secret key, merchant, fiscalisation |
| B5 | Telegram Stars live | IMPLEMENTED-UNVERIFIED | токен + первая покупка/возврат |
| B6 | Transactional email | NOT USED at launch | SMTP; email-auth отключён в prod |
| B7 | Production hosting/domain/TLS/Caddy | IMPLEMENTED-UNVERIFIED | VPS, домен, DNS, tunnel, TLS |
| B8 | Operator details | PLACEHOLDERS READY | ФИО, ИНН, адрес, email (владелец) |
| B9 | S3-compatible object storage | BLOCKED | bucket, creds, public origin/CDN |
| B10 | Crypto wallet (Walt) live | IMPLEMENTED-UNVERIFIED | адрес кошелька/актив, первый перевод |

## 14. Известные проблемы (K1–K18)

Ключевые: K8 (High, bot/Mini App live unverified), K9 (High, YooKassa sandbox), K10 (Medium, Stars not implemented — бот/Mini App не предлагают карты), K14 (High, legal docs review), K18 (Medium, только local storage), K3 (Medium, branch protection), K5 (Medium, нет concurrency stress), K11 (Medium, non-durable bot queue), K12 (Medium, нет ZAP/container scan), K13 (Medium, нет Playwright e2e). Остальные Low (tooling, docs, typing).

## 15. Compliance (РФ)

- 152-ФЗ: lawful purpose/minimal data, separate private data (encrypted + blind index), data localisation (Russia-located PG — blocked B7), subject access/export, deletion, consent withdrawal, retention schedule (REVIEW), processor agreements (blocked), cross-border transfer (Telegram — REVIEW), security measures (implemented), breach notification (draft).
- Реклама: erid/ad_label fields implemented; reporting process blocked (B8).
- Платежи: цена/условия до оплаты, no auto-charge (каждый период — новый платёж), receipts/54-ФЗ (blocked B4), refund path, consistent pricing (REVIEW), card data never stored, minors policy (REVIEW).
- Контент/благополучие животных: prohibited content checks, purpose-aware price labels («В добрые руки», «Переустройство»), welfare policy needs review.
- Telegram: foreign service, legal basis for processing TG identifiers — REVIEW.

## 16. Тестирование

- **74 pytest** (auth, listings, discovery, messaging, privacy, admin, reports, payments, bot logic) — все PASS.
- Покрытие: health/readiness, register/login/logout, Telegram auth, email verify/reset, encryption at rest, listing lifecycle, publication rules, input allow-lists, IDOR/BOLA, upload attacks, media path traversal, discovery feed, swipe idempotency, server-side quota, undo, mutual matching, skip semantics, favorites, messaging, notifications, privacy canaries, admin RBAC/MFA, reports, payments (bad sig, mismatch, duplicate, ownership, refund, grant, reconcile), bot logic (signed callbacks, onboarding, deep links, webhook validation, notification worker).
- **Пробелы**: нет concurrency stress, нет Playwright e2e, нет Mini App/bot transport tests против live Telegram API, нет load tests квоты, нет ZAP/container scan.
- **Ручная QA**: docker compose ps healthy, alembic upgrade head, /healthz /readyz /api/docs, visual QA 390/1280 px, fake checkout end-to-end, admin payments UI, MFA settings, Mini App subscription screen.

## 17. Документация

Индекс: `docs/README.md`. Основное:
- ARCHITECTURE.md, DECISIONS.md (ADR), PRIVACY_MODEL.md, THREAT_MODEL.md
- PAYMENTS.md, TELEGRAM.md, COMPLIANCE.md
- SECURITY_REPORT.md, TEST_REPORT.md, REQUIREMENTS_TRACEABILITY.md
- RUNBOOK.md, BLOCKERS.md, KNOWN_ISSUES.md, IMPLEMENTATION_PLAN.md
- legal/ (шаблоны), adr/
- CONTRIBUTING.md, SECURITY.md, CHANGELOG.md, LICENSE

## 18. Живой сайт (localhost:3000)

Проверенные страницы: `/` (главная), `/discovery` (подбор). Сайт рендерится корректно, отображает пустую витрину (нет seed-данных в prod-БД?), гостевой просмотр с квотой. Навигация: Подбор, Поиск, Партнёрам, Помощь. Футер: документы (privacy, terms, personal-data, requisites, rules, offer), ссылки на TG-бот/канал. Страницы: legal/*, account/*, admin/*, catalog/[purpose], search, support, partners, verify-email, forgot/reset-password, register, login.

## 19. Наблюдения, риски и замечания

1. **Сильная инженерная культура**: privacy by design с canary-тестами, RBAC+MFA, атомарные квоты, идемпотентные платежи, версионированные согласия, security report, threat model, runbook, compliance checklist.
2. **Все внешние интеграции заблокированы** (Telegram, YooKassa, Stars, SMTP, хостинг, S3) — проект локальный, не production-ready для медиа/платежей/бота.
3. **Медиа только на локальном диске** (B9) — не масштабируется, нет signed URL для приватных документов.
4. **Юридические шаблоны** требуют проверки юристом, реквизиты — заглушки (B8).
5. **Нет e2e/Playwright/load tests** — ручная QA.
6. **In-process bot queue** non-durable (K11) — риск потери обновлений.
7. **Telegram — иностранный сервис** — нужен юридический анализ обработки TG-идентификаторов (COMPLIANCE).
8. **Нет авто-продления подписки** (by design) — ручной платёж на каждый период.
9. **Crypto-платежи** (Walt) добавлены как дополнительный путь — B10.
10. **Демо-данные** используют сгенерированные фото-заглушки, чётко помечены.
11. **Privacy-first UX**: контакты/ID/фото/онлайн-статус не раскрываются — сильное конкурентное преимущество.
12. **Согласованность цен**: Stars-ценообразование требует документированной политики конверсии (REVIEW).

## 20. Что не удалось проверить

- Бэкенд в runtime (запущен ли API на 8000 — не проверялось; только web на 3000).
- Реальные Telegram-бот, платежи, email, продакшен-хостинг, S3.
- Playwright e2e, load/concurrency tests, ZAP baseline, container image scan.
- Личный кабинет/админка под авторизацией (требуют логин).
- БД-схема в runtime (миграции применены — по TEST_REPORT).

---

**Итог**: Zooffer — инженерно зрелый проект с сильным фокусом на приватность, безопасность и качество кода (74 теста, строгие гейты, threat model, privacy canaries). Архитектура — модульный монолит FastAPI + Next.js 16 + aiogram 3 с общей сервисной прослойкой. Основные возможности реализованы и проверены локально; продакшен-готовность блокирована внешними зависимостями (Telegram, платежи, хостинг, S3, юридические реквизиты). Для финального аудита продакшен-версии необходимы: доступ к репозиторию/CI, настроенные интеграции, юридический review, e2e/load тесты.
