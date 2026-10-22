# Zooffer implementation plan

Status legend (master prompt §0.3): `VERIFIED` — implemented and proven by a test or documented run;
`IMPLEMENTED-UNVERIFIED` — code exists but is not yet proven; `BLOCKED` — needs an external
credential/service; `NOT STARTED`.

This plan is a living document. Each phase ends with a status report, tests, and a git commit/tag.
The master prompt (`ZOOFFER_MASTER_PROMPT.md`) is the source of truth.

## Working assumptions and environment facts (checked 2026-10-22)

| Item | Fact | Consequence |
|---|---|---|
| Python | 3.12.7, venv at `.venv` | Backend targets 3.12 |
| Node | 24.19, npm 11.17 (no pnpm) | Web uses npm workspaces |
| Docker | Docker 29.4.2; daemon started during this session | PostgreSQL 16 + Redis run locally via `compose.dev.yaml` |
| GitHub CLI | `gh` not installed, no `GH_TOKEN`/`GITHUB_TOKEN` in env | Remote repo creation is `BLOCKED`; local repo, branches, tags and push instructions are produced |
| Make | not installed on this Windows host | `make` targets are committed for CI/Linux; equivalent PowerShell scripts are provided and used for verification |

## Architecture summary

- **Monorepo**: `backend/` (FastAPI + SQLAlchemy 2 + Alembic), `bot/` (aiogram 3, thin; imports
  backend domain services), `web/` (Next.js App Router incl. `/tg` Mini App), `infra/`, `docs/`,
  `tests/e2e`.
- **One canonical identity and database.** The website, Telegram bot and Mini App all call the same
  domain/service layer; no business rules are duplicated in clients.
- **Privacy by construction**: `user_private_data` is a separate table, all public responses use
  reviewed allowlist schemas (`PublicOwnerView`, `PublicAnimalView`, `PublicListingView`, …), opaque
  public IDs, and a canary leak-test suite in CI.
- **Quota and matching are transactional** in PostgreSQL, with unique constraints and row locks.
- **Payments** are behind a `PaymentProvider` interface. The fake provider is fully tested; real
  YooKassa and Telegram Stars are `BLOCKED` until merchant/bot credentials exist.
- **Media**: content-sniffed, re-encoded (EXIF/GPS stripped) to WebP, stored outside the web root via
  a `MediaStorage` interface (local dev / S3-compatible production).

## Phase 1 — Architecture, repository, environment, requirements

Tasks:
1. Local git repository, `main` branch, `.gitignore` excluding `legacy/`.
2. Monorepo scaffold, root docs, license, contribution/security policies, CODEOWNERS, issue/PR
   templates, Dependabot, CI workflows.
3. `compose.dev.yaml` with PostgreSQL 16 + Redis; `.env.example`; fail-fast config.
4. ADRs (identity/sessions, public IDs, database portability, package manager), threat model v1.
5. Requirements traceability table mapping master-prompt sections to modules/tests.
6. Backend/frontend tooling: ruff, mypy, pytest, eslint, tsc, prettier; scripts for Windows.

Acceptance: `git status` clean of legacy files; config loads; lint/type/test commands run; docs
indexed. Remote GitHub repo `BLOCKED` and documented with exact push commands.

## Phase 2 — Database schema and backend foundation

Tasks:
1. SQLAlchemy models + initial Alembic migration for users, identities, sessions, consents, private
   data, profiles, regions/cities/breeds, animals, photos/documents, listings, swipes, favorites,
   matches, blocks, conversations/messages, quotas, plans/subscriptions/payments, partners/offers,
   notifications, reports/moderation/audit, settings.
2. Migration + constraint tests against PostgreSQL 16.
3. Config validation, structured logging with correlation IDs, health/readiness, metrics, uniform
   error envelope.
4. RBAC policy layer skeleton and permission-declaring dependencies.
5. Public DTO allowlists and the privacy-leak test harness with canary strings.
6. `make`/scripts: migrate, seed, run.

Acceptance: migrations apply to empty DB, downgrade works; constraints tested; leak harness fails if
a private field is added to a public schema; health endpoints return expected payloads.

## Phase 3 — Authentication, accounts, linking

Tasks:
1. Argon2id passwords; session cookies (`HttpOnly`, `SameSite=Lax`, `Secure` in production,
   `__Host-` prefix), hashed session tokens, rotation, idle/absolute expiry, device list/revoke.
2. Registration, login, logout, CSRF (double-submit + Origin), login throttling.
3. Telegram Login payload validation (HMAC + freshness + replay) and Mini App `initData` validation.
4. One-time hashed Telegram link tokens, bot confirmation flow, atomic binding, merge guard.
5. Email verification/recovery behind an `EmailSender` interface (console dev / SMTP prod).
6. Staff MFA (TOTP) skeleton with enforcement, first-admin CLI bootstrap.
7. Tests: auth flows, fixation/rotation, enumeration, rate limits, forged/stale Telegram data.

Acceptance: full web auth flow tested over HTTP; Telegram validation forged/stale tests pass; RBAC
tests reject ordinary users from admin routes.

## Phase 4 — Website design and responsive interface

Tasks:
1. Time-boxed exploration of 2–3 design directions; record the chosen direction in `docs/DECISIONS.md`.
2. Design tokens, self-hosted Cyrillic fonts (Fontsource/Next local), wordmark SVGs, icons.
3. UI components, mobile floating tab bar, desktop header, selective Liquid Glass with fallbacks,
   reduced-motion and contrast checks.
4. Homepage with all seven required sections, real API data, required motion, empty states.
5. Auth/onboarding screens, account shell, loading/empty/error/offline states.
6. Accessibility and Lighthouse checks; screenshots at 320/390/768/1280/1536.

Acceptance: homepage renders from the real API; responsive screenshots captured; keyboard and
reduced-motion paths verified; contrast results documented.

## Phase 5 — Animals, listings, search, filters, SEO

Tasks:
1. Animal CRUD, listing wizard (server-autosaved drafts), ownership enforcement.
2. Upload pipeline (MIME sniffing, size/dimension limits, re-encode, EXIF strip, WebP variants).
3. Listing state machine + moderation submission; create/edit/pause/renew/archive.
4. Search: PostgreSQL FTS (Russian) + filters, keyset pagination, URL-shareable filters.
5. Public listing/category/breed/city SEO pages, sitemap, robots, JSON-LD, OG image.
6. Tests: validation, IDOR, upload attacks (polyglot/SVG/oversize), FTS, pagination.

Acceptance: a user can create an animal and publish a listing with photos through the wizard; the
listing appears in search and on a server-rendered page; all public output is leak-tested.

## Phase 6 — Swipes, favorites, matching, quotas

Tasks:
1. Swipes (like/skip), idempotency key, undo entitlement, favorites.
2. Mutual matching transaction with species/sex compatibility and blocks.
3. Daily quota: atomic conditional UPDATE in the same transaction, Europe/Moscow reset,
   entitlement increases, cross-channel counter.
4. Discovery ranking + keyset pagination excluding own/swiped/blocked/unpublished.
5. Tests: concurrency (N parallel swipes), unique matches, no one-sided match, timezone boundary,
   undo restore, entitlement change.

Acceptance: concurrency tests prove quota and match invariants; web and bot paths share the counter.

## Phase 7 — Messaging and notifications

Tasks:
1. Conversations (`match`/`inquiry`), inquiry rate limits, blocks/mute/report, message pagination.
2. Realtime SSE with polling fallback; read receipts preference; no presence/typing indicators.
3. Anti-spam heuristics; voluntary contact exchange with explicit confirmation.
4. Notification preferences + fan-out pipeline (in-app, Telegram, email behind interfaces),
   dedupe/batching/quiet hours.
5. Tests: access control, ordering/pagination, contact-exchange privacy, anti-spam limits.

## Phase 8 — Subscriptions and payments

Plans/entitlements, orders with server-computed prices, fake provider tests, YooKassa and Telegram
Stars integrations behind interfaces (BLOCKED without credentials), webhook signature/replay/
idempotency tests, admin grant/refund, `docs/PAYMENTS.md`.

## Phase 9 — Telegram bot

aiogram 3 webhook with secret header, update dedupe, Redis FSM with TTL, all §8.3 commands, compact
listing wizard, inline discovery using shared services, notifications, rate limits, flood control,
Mini App menu button, tests with a fake Telegram API transport. `TELEGRAM_BOT_TOKEN` is BLOCKED for
live verification; logic is verified with fakes.

## Phase 10 — Telegram Mini App

`/tg/*` screens in the same Next.js app, validated `initData` session minting, WebApp SDK integration,
theme/viewport/safe-area handling, Stars purchase entry, graceful version degradation, device QA.
Requires a real bot for end-to-end verification → `BLOCKED` at integration stage; unit tests cover
validation and session minting.

## Phase 11 — Administration and moderation

Admin shell under RBAC + MFA, moderation queue, reports, users/listings, subscriptions, partners,
content, audit log, settings (N, plans, flags), MFA-enforced access, tests for the full role/resource
matrix.

## Phase 12 — Partners, SEO and growth

Partners/offers/banners, server-side click redirect with first-party attribution, partner inquiry,
empty-state-first public section, referral/UTM attribution, sitemaps/canonical/noindex rules, legal
ad marking fields.

## Phase 13 — Security, privacy, legal sweep

OWASP ASVS L2-oriented review, injection corpora, IDOR matrix, CSRF/rate-limit/upload/webhook tests,
ZAP baseline against local, dependency and secret scans, `docs/SECURITY_REPORT.md`, full cross-channel
canary suite, legal document templates and `docs/COMPLIANCE.md`.

## Phase 14 — Integration, e2e, performance

Playwright scenarios across web and `/tg`, cross-channel identity/quota/entitlement scenario, load
tests with k6/Locust, Lighthouse budgets, axe accessibility audit, results in `docs/TEST_REPORT.md`.

## Phase 15 — Deployment and operations

Production compose (Russia-located host), Caddy/TLS and headers, webhook registration script,
monitoring/alerts, encrypted backups with an executed restore drill, runbooks, rollback, final
repository audit from a fresh clone.

## Current status (2026-10-22)

| Phase | Status | Evidence / notes |
|---|---|---|
| 1. Architecture, repository, environment | `VERIFIED` (local) | Git repo, docs/ADRs, config fail-fast, Docker PostgreSQL 16 + Redis healthy; remote GitHub `BLOCKED` (B1) |
| 2. Schema and backend foundation | `VERIFIED` | 3 Alembic migrations applied; health/readiness, structured logs, error envelope, metrics, media storage |
| 3. Auth, accounts, linking | `VERIFIED` (password/web) / `IMPLEMENTED-UNVERIFIED` (live Telegram) | `backend/tests/test_auth.py`; Telegram/Mini App fixtures; live bot `BLOCKED` (B2/B3) |
| 4. Animal profiles, listings, search | `VERIFIED` | `backend/tests/test_listings.py`; CRUD, photo pipeline, publish/pause/renew/archive/sold, FTS + filters, privacy DTOs |
| 5. Media pipeline | `VERIFIED` | Re-encode/WebP/EXIF strip, upload attacks tested; private documents allow-listed away from public media route |
| 6. Swipes, favorites, matching, quotas | `VERIFIED` | `backend/tests/test_discovery.py`; atomic quota, idempotency, mutual likes only, undo entitlement, favorites |
| 7. Messaging and notifications | `NOT STARTED` (models exist) | Next slice |
| 8. Subscriptions and payments | `NOT STARTED` (models + interfaces exist) | Fake provider boundary prepared |
| 9. Telegram bot | `NOT STARTED` | Requires service layer reuse |
| 10. Mini App | `NOT STARTED` | Depends on web |
| 11. Administration/moderation | `NOT STARTED` | Automated moderation pre-checks exist |
| 12. Partners/SEO/growth | `NOT STARTED` | Models and public partner schema exist |
| 13. Security/privacy/legal sweep | `PARTIAL` | Privacy canary suite and upload/IDOR/CSRF tests started |
| 14. Integration/e2e/performance | `NOT STARTED` | |
| 15. Deployment/operations | `NOT STARTED` | Infra scaffold only; hosting `BLOCKED` (B7) |

## Dependencies and risks

| Risk | Impact | Mitigation |
|---|---|---|
| No GitHub credentials / `gh` | Cannot create private remote, PRs, releases | Local branches/tags + exact push commands; blocker recorded |
| No Telegram bot token | Live bot/Mini App cannot be verified | Provider interfaces + fake transport tests; blocker recorded |
| No YooKassa/Stars merchant credentials | Real payments cannot be verified | Fake provider fully tested; adapters isolated and marked BLOCKED |
| Docker/PostgreSQL availability | Integration tests cannot run | Postgres 16 container; tests fail loudly rather than silently skip |
| Single-session scope vs 15 phases | Incomplete product | Build vertical slices in phase order; keep every completed slice tested and documented |
| Legal specifics unknown (operator form) | Compliance gaps | Templates with marked fields; `Needs qualified Russian legal review` statuses |
| Timezone/quota races | Over/under-charging | Conditional UPDATE + unique constraints + concurrency tests |
