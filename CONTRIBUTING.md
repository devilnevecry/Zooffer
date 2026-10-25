# Contributing to Zooffer

Zooffer is a private, proprietary project. Contributions are accepted only from people with
explicit permission from the repository owner.

## Prerequisites

- Python 3.12
- Node.js 22+ and npm
- Docker Desktop (PostgreSQL 16 and Redis 7 via `compose.dev.yaml`)
- PowerShell 7+ on Windows (the documented commands are PowerShell; bash equivalents work too)

## Local setup

```powershell
docker compose -f compose.dev.yaml up -d
Copy-Item .env.example .env      # then fill development-only secrets
.venv\Scripts\python -m pip install -e "backend[dev]"
$env:PYTHONPATH='backend'
.venv\Scripts\python -m alembic -c backend\alembic.ini upgrade head
.venv\Scripts\python scripts\seed_dev.py
```

Run the API and website in separate terminals:

```powershell
$env:PYTHONPATH='backend'
.venv\Scripts\python -m uvicorn zooffer.main:app --host 127.0.0.1 --port 8000

cd web
npm install
npm run dev
```

Demo accounts use the password `ZoofferDemo2026!`. Demo photos are generated placeholders, not real
animal photography.

## Checks before a pull request

```powershell
.\scripts\ci.ps1
```

The script runs the same gates as CI: ruff lint and format check, mypy on the shared backend, pytest
against PostgreSQL, bandit, Prettier, `tsc`, ESLint and the production Next.js build. Individual
commands are listed in [README.md](README.md#verification).

## Branching and commits

- `main` is always the latest verified state.
- Work on `phase/NN-short-name`; use `feat/...` or `fix/...` inside a phase and merge back into it.
- Do not delete phase branches and never force-push shared branches.
- Commits follow Conventional Commits: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`,
  `ci:`, `perf:`, `security:`. Imperative subject, 72 characters or fewer, body explains why.
- Never commit `.env` files, secrets, uploads, build output, logs or database dumps.

## Code rules

- Russian for user-facing strings; English for code, comments, identifiers and developer docs.
- The brand is always **Zooffer** (Latin letters).
- Privacy is non-negotiable: other users may see only the public first name, optional public surname
  or «Владелец». Never expose contacts, internal UUIDs, Telegram IDs/usernames, photos or online
  status through a public DTO.
- All entitlements, quotas, prices and permissions are derived and enforced on the server.
- No fake functionality: a visible action must call the backend and either work or honestly report a
  blocker. Demo mode must be clearly labelled.
- Do not import from `legacy/`; it is read-only reference material and git-ignored.

## Review checklist

- [ ] The change has a test or a documented manual verification.
- [ ] `scripts/ci.ps1` passes.
- [ ] New strings are Russian and the brand spelling is correct.
- [ ] Public responses use allowlisted DTOs and contain no private data.
- [ ] Migrations are reversible and have a single clear purpose.
- [ ] Docs, `CHANGELOG.md` and status labels are updated.
- [ ] No secret, token or personal data appears in the diff.
