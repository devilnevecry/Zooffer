# Zooffer

Zooffer is a Russian-language platform for finding animals, publishing listings, mutual matching and
private messaging. The same backend serves a Next.js website, a Telegram bot and a Telegram Mini App.

This repository is a local-first build: the application is implemented and tested, while external
integrations that need credentials (GitHub, a live Telegram bot, real payments, SMTP, production
hosting) are documented as blockers in [docs/BLOCKERS.md](docs/BLOCKERS.md).

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2 (async), Alembic, PostgreSQL 16 |
| Cache / queue | Redis 7 |
| Web + Mini App | Next.js 16 App Router, React 19, TypeScript, plain global CSS |
| Bot | aiogram 3, shared `zooffer` services |
| Tests | pytest + httpx ASGI transport, PostgreSQL test database |

## Repository layout

```text
backend/        FastAPI app, SQLAlchemy models, Alembic migrations, tests
bot/            aiogram bot, signed callbacks, notification worker, tests
web/            Next.js website and /tg Mini App
docs/           architecture, decisions, privacy, payments, runbook, evidence
infra/          PostgreSQL init scripts (dev)
scripts/        seed script for demo data
legacy/         read-only legacy material, never imported
```

## Quick start (Windows, local)

1. Start PostgreSQL and Redis:

   ```powershell
   docker compose -f compose.dev.yaml up -d
   ```

2. Copy `.env.example` to `.env` and set development secrets. Never commit `.env`.

3. Install backend dependencies and migrate:

   ```powershell
   .venv\Scripts\python -m pip install -e backend
   $env:PYTHONPATH='backend'
   .venv\Scripts\python -m alembic -c backend\alembic.ini upgrade head
   ```

4. Seed demo data (optional):

   ```powershell
   $env:PYTHONPATH='backend'
   .venv\Scripts\python scripts\seed_dev.py
   ```

   Demo password: `ZoofferDemo2026!`. Accounts: `anna@example.com`, `mikhail@example.com`,
   `elena@example.com`, `dmitry@example.com`, `olga@example.com`. Demo photos are generated
   placeholders, not real animal photography.

5. Run the backend:

   ```powershell
   $env:PYTHONPATH='backend'
   .venv\Scripts\python -m uvicorn zooffer.main:app --host 127.0.0.1 --port 8000
   ```

6. Run the website:

   ```powershell
   cd web
   npm install
   npm run dev
   ```

   Open <http://localhost:3000>. The Mini App routes are under `/tg`.

7. Run the bot locally (optional, requires `TELEGRAM_BOT_TOKEN`):

   ```powershell
   $env:PYTHONPATH='backend;bot'
   $env:BOT_MODE='polling'
   .venv\Scripts\python -m zooffer_bot
   ```

## Verification

```powershell
$env:PYTHONPATH='backend'
.venv\Scripts\python -m pytest backend\tests -q

$env:PYTHONPATH='backend;bot'
.venv\Scripts\python -m ruff check backend scripts bot

cd web
npm run typecheck
npm run lint
npm run build
```

The current evidence and known gaps are recorded in [docs/TEST_REPORT.md](docs/TEST_REPORT.md) and
[docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md).

## Payments

`PAYMENT_PROVIDER=fake` works only when `ENVIRONMENT` is `dev` or `test`. Every demo order is labelled
as simulated in the API and UI; no card data is collected and no money moves. Real YooKassa and
Telegram Stars payments require merchant credentials and remain `BLOCKED`. See
[docs/PAYMENTS.md](docs/PAYMENTS.md).

## Security and privacy

- HttpOnly cookie sessions, HMAC-hashed session tokens, CSRF double-submit and Origin checks.
- Separate encrypted private-data table with HMAC blind index; public DTO allowlists.
- Other users see only a first name, optional surname or «Владелец». Contacts, internal IDs, Telegram
  IDs/usernames, photos and online status are never exposed.
- Server-enforced shared swipe quota across web, bot and Mini App.
- Details: [docs/PRIVACY_MODEL.md](docs/PRIVACY_MODEL.md), [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md),
  [docs/SECURITY_REPORT.md](docs/SECURITY_REPORT.md).

## Status

Implemented and verified locally: backend domain and APIs, website, Mini App UI, bot logic with
fakes, admin/moderation, reports, MFA, fake-provider billing. Blocked on external credentials: live
Telegram, real payments, SMTP delivery, production hosting and GitHub remote. The authoritative
status table is in [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md).

## License and legal

No public license has been chosen yet. Legal document templates are in [docs/legal](docs/legal) and
are marked as requiring qualified Russian legal review. Operator details are placeholders until the
owner provides them.
