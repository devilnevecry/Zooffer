# Test report

Updated: 2026-10-24. Environment: Windows 11, Python 3.12.7, PostgreSQL 16 in Docker, pytest
`backend/tests`, ruff, Next.js 16 build.

## Command

```powershell
$env:PYTHONPATH='backend'
.venv\Scripts\python -m pytest backend\tests -q
```

## Latest result

```
74 passed in 282.53s (0:04:42)

ruff check backend scripts bot: All checks passed
python -m compileall bot: passed
cd web && npm run typecheck: passed
cd web && npm run lint: passed
cd web && npm run build: passed (54 routes)
```

## Coverage by area

| Area | Tests | What is proven |
|---|---|---|
| Health/readiness | `test_auth.py::test_health`, `test_ready` | App boots against PostgreSQL; readiness checks the DB |
| Registration/login/logout | `test_auth.py` | Session cookie rotation, CSRF, `/me`, consent records, password rules |
| Telegram auth | `test_auth.py` | HMAC validation, stale/replayed `initData`, link token single use |
| Email verification/reset | `test_auth.py` | Token hashing, enumeration-resistant responses, session revocation |
| Encryption at rest | `test_auth.py` | Email is not stored in plaintext; blind index matches |
| Listing lifecycle | `test_listings.py` | Create animal → photo → draft → publish → pause → renew → sold |
| Publication rules | `test_listings.py` | At least one photo required; contact details route to `pending_moderation` |
| Input allow-lists | `test_listings.py` | Mass assignment rejected; sale/adoption price rules enforced |
| IDOR/BOLA | `test_listings.py`, `test_account.py`, `test_messaging.py` | Foreign users cannot mutate or read private resources |
| Upload attacks | `test_listings.py` | Text/SVG/empty files rejected; documents never returned with URL or public key |
| Media path traversal | `test_listings.py` | `documents/` and traversal keys are unreachable through the public media route |
| Discovery feed | `test_discovery.py` | Own and already-swiped listings excluded; guest preview has no quota |
| Swipe idempotency | `test_discovery.py` | Replayed request id is a no-op; conflicting action returns 409 |
| Server-side quota | `test_discovery.py` | Limit is enforced in PostgreSQL; rejected swipe does not increment usage |
| Undo | `test_discovery.py` | Requires entitlement; restores one quota unit; nothing-to-undo after |
| Mutual matching | `test_discovery.py` | Only reciprocal likes create one match and one two-person conversation |
| Skip semantics | `test_discovery.py` | Skips never create matches |
| Favorites | `test_discovery.py` | Idempotent add/remove; owner-scoped lists |
| Messaging | `test_messaging.py` | Conversation participation, ordering, pagination, blocks, reports |
| Notifications | `test_account.py`, `test_admin.py` | Preferences, in-app filtering, moderation/support notifications |
| Privacy canaries | `test_privacy.py` | Public JSON has no contact/account/internal-ID keys or values; owner endpoint is name-only |
| Admin RBAC/MFA | `test_admin.py` | MFA required for staff, role matrix, moderation, audit, settings |
| Reports | `test_reports.py` | User reports for listing/animal/message/user; participation and uniqueness rules |
| Payments | `test_payments.py` | Server pricing, order reuse, demo confirmation, idempotency, bad signature, amount mismatch, ownership, refund, revoke, admin grant, reconcile |
| Bot logic | `bot/tests` | Signed callbacks, onboarding, deep links, webhook validation, notification worker with fakes |

## Known gaps in this report

- No concurrency stress test yet for parallel swipes at high parallelism.
- No browser e2e/Playwright, Mini App, or bot transport tests against a live Telegram API.
- Live Telegram/YooKassa/Stars/email are `BLOCKED`; tests use fakes/fixtures.
- YooKassa adapter has not been run against a sandbox shop.
- Windows timings are slow (~2s connection overhead under Docker); not a correctness signal.

## Manual verification

- `docker compose -f compose.dev.yaml ps` → PostgreSQL and Redis healthy.
- `alembic upgrade head` applies all migrations to the dev database.
- `GET /healthz`, `GET /readyz`, `/api/docs` respond locally.
- Website and Mini App visual QA at 390 px and 1280 px; admin, report modal and MFA settings checked.
- Fake checkout flow creates an order, confirms it, and activates a subscription.
