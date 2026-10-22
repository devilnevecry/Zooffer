# Test report

Updated: 2026-10-22. Environment: Windows 11, Python 3.12.7, PostgreSQL 16 in Docker, pytest
`backend/tests`, ruff.

## Command

```powershell
$env:PYTHONPATH='backend'
.venv\Scripts\python -m pytest backend\tests -q
```

## Latest result

```
37 passed in 113.52s
ruff check backend: All checks passed
ruff format --check backend: clean
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
| IDOR/BOLA | `test_listings.py` | Foreign users cannot mutate listings/animals; public owner returns name only |
| Upload attacks | `test_listings.py` | Text/SVG/empty files rejected; documents never returned with URL or public key |
| Media path traversal | `test_listings.py` | `documents/` and traversal keys are unreachable through the public media route |
| Discovery feed | `test_discovery.py` | Own and already-swiped listings excluded; guest preview has no quota |
| Swipe idempotency | `test_discovery.py` | Replayed request id is a no-op; conflicting action returns 409 |
| Server-side quota | `test_discovery.py` | Limit is enforced in PostgreSQL; rejected swipe does not increment usage |
| Undo | `test_discovery.py` | Requires entitlement; restores one quota unit; nothing-to-undo after |
| Mutual matching | `test_discovery.py` | Only reciprocal likes create one match and one two-person conversation |
| Skip semantics | `test_discovery.py` | Skips never create matches |
| Favorites | `test_discovery.py` | Idempotent add/remove; owner-scoped lists |
| Privacy canaries | `test_privacy.py` | Public JSON has no contact/account/internal-ID keys or values; owner endpoint is name-only |

## Known gaps in this report

- No concurrency stress test yet for parallel swipes (Phase 6 acceptance item remains open).
- No browser e2e/Playwright, Mini App or bot transport tests yet.
- Live Telegram/YooKassa/Stars/email are `BLOCKED`; tests use fakes/fixtures.
- Windows timings are slow (~2s connection overhead under Docker); not a correctness signal.

## Manual verification

- `docker compose -f compose.dev.yaml ps` → PostgreSQL and Redis healthy.
- `alembic upgrade head` applies all migrations to the dev database.
- `GET /healthz`, `GET /readyz`, `GET /api/docs` respond locally.
