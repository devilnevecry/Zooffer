# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html) with pre-1.0 versions.

## [Unreleased]

### Planned

- Telegram Stars purchase flow inside the bot and Mini App (blocked on a live bot token and merchant
  configuration).
- YooKassa sandbox verification and fiscalisation.
- Playwright end-to-end tests and a quota concurrency load test.

## [0.2.1-repo-presentation] - 2026-10-25

### Added

- Repository presentation: proprietary `LICENSE`, `README.ru.md`, `CONTRIBUTING.md`, `SECURITY.md`,
  `CODEOWNERS`, issue and pull-request templates, Dependabot, CI and release workflows.
- Local CI entry point `scripts/ci.ps1` mirroring the GitHub Actions jobs.
- Design-direction ADR 0010, repository banner and six application screenshots.
- Prettier configuration and a formatting gate for the web app.

### Changed

- README rewritten with a real badge set, Mermaid diagram, screenshots, configuration table and an
  honest per-area status table.
- Documentation corrected to match the code: architecture layout, media storage limits, blockers
  B1/B7 and the new B9, traceability evidence, payments and Telegram policy.
- Backend dependencies upgraded after an audit: FastAPI 0.162.0 (Starlette 1.10.0),
  `cryptography` 50.0.2, `python-multipart` 0.0.32, `aiosmtplib` 5.1.3, pytest 9.1.1 and
  pytest-asyncio 1.4.0.
- `MEDIA_BACKEND` accepts `local` only; unused `aiosqlite`, `itsdangerous` and `boto3` removed.

### Fixed

- Mypy errors in payments, swipes, messaging, admin and listing services.
- Ruff formatting across the backend, scripts and bot.
- Bandit findings documented with reviewed `# nosec` justifications; HIBP SHA-1 marked
  `usedforsecurity=False`.
- Redundant Free-plan card, plan badge overlap, duplicated date punctuation and a stale demo notice
  in subscription UI.

### Security

- `pip-audit` reports no known vulnerabilities after the upgrade; `npm audit` reports 0; gitleaks
  finds no leaks.
- Local CI now fails on formatting drift, SAST findings or typing regressions.

## [0.2.0-payments-admin-qa] - 2026-10-25

### Added

- Payment provider interface with a deterministic fake provider, signed demo webhooks, server-priced
  orders, idempotent processing, refunds, entitlement grants and reconciliation.
- Admin payment list/detail, provider event log, refund form, report queue, user management, audit
  log, settings and staff MFA enforcement.
- Account subscription management with plan changes and cancellation until period end.
- Website checkout for the demo provider; explicit demo labelling and no card-data collection.

### Changed

- Subscription copy no longer claims automatic renewal: each period requires a new payment.
- Free plans are filtered out of purchasable plan lists on the website and in the bot.
- The Mini App subscription screen disables purchase until Telegram Stars exists.
- The bot's `/buy` reports Stars unavailability and never links to card checkout.

### Fixed

- Plan-card badge overlap and duplicated punctuation around the period end date.
- Stale demo notice remaining visible after a successful demo payment.
- Duplicate free-plan card on the subscription page.
- Ruff import order, long-line and typing issues; mypy errors in the shared backend.
- Telegram digital-goods policy violation risk from a card link inside the Mini App.

### Security

- RBAC plus MFA required for every staff endpoint.
- CSRF, Origin, IDOR and upload protections covered by tests.
- Payment webhooks verified, replay-protected and amount-checked.
- Fake provider restricted to `dev` and `test` environments.

### Blocked

- Live Telegram bot and Mini App, real YooKassa and Stars payments, SMTP delivery, production
  hosting and legal review. See `docs/BLOCKERS.md`.

## [0.1.0-bootstrap] - 2026-10-24

### Added

- Repository foundation, configuration, Docker Compose for PostgreSQL and Redis.
- SQLAlchemy models, Alembic migrations and demo seed data.
- Authentication, sessions, CSRF, Telegram login and `initData` validation, MFA.
- Animals, listings, search, discovery feed, swipes, shared quota, matches, messaging, favorites,
  notifications, reports, support and partner offers.
- Next.js website, account area, admin area and `/tg` Mini App screens.
- aiogram bot, signed callbacks, onboarding, notification worker and webhook endpoint.
- Documentation set, ADRs, privacy model, threat model, security and test reports.

[Unreleased]: https://github.com/devilnevecry/Zooffer_final/compare/v0.2.1-repo-presentation...HEAD
[0.2.1-repo-presentation]: https://github.com/devilnevecry/Zooffer_final/compare/v0.2.0-payments-admin-qa...v0.2.1-repo-presentation
[0.2.0-payments-admin-qa]: https://github.com/devilnevecry/Zooffer_final/releases/tag/v0.2.0-payments-admin-qa
[0.1.0-bootstrap]: https://github.com/devilnevecry/Zooffer_final/releases/tag/v0.1.0-bootstrap
