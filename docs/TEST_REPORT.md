# Test report

Updated: 2026-10-25. Environment: Windows 11, Python 3.12.7, PostgreSQL 16 in Docker, pytest
`backend/tests`, ruff, bandit, Next.js 16 build.

## Command

```powershell
.\scripts\ci.ps1
```

The script mirrors the GitHub Actions pipeline. Individual commands are listed in
[CONTRIBUTING.md](../CONTRIBUTING.md#checks-before-a-pull-request).

## Latest result

```
[1] Ruff lint                 PASS
[2] Ruff format check         PASS (111 files formatted)
[3] Mypy (shared backend)     PASS (71 files)
[4] Bandit (SAST)             PASS (exit 0)
[5] pytest (PostgreSQL)       PASS - 74 passed in 287.2s
[6] Web type check            PASS
[7] Web lint                  PASS
[8] Web format check          PASS
[9] Web production build      PASS (56 routes)

pip-audit: no known vulnerabilities
npm audit --audit-level=high: 0 vulnerabilities
gitleaks v8.24.0 (Docker): no leaks found
```

`gitleaks` is not installed as a native binary on this host, so it was run through its official
container image; the local script skips it with an explicit message, while CI always runs it.

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
| Bot logic | `test_bot.py` | Signed callbacks, onboarding, deep links, webhook validation, notification worker with fakes |

## Known gaps in this report

- No concurrency stress test yet for parallel swipes at high parallelism.
- No browser e2e/Playwright, Mini App, or bot transport tests against a live Telegram API.
- Live Telegram/YooKassa/Stars/email are `BLOCKED`; tests use fakes/fixtures.
- YooKassa adapter has not been run against a sandbox shop.
- Bot modules are not covered by mypy because aiogram's `Message | InaccessibleMessage` unions need
  narrowing work; the shared backend is type-checked.
- `pip-audit` runs as an advisory CI job (`continue-on-error`) so a newly disclosed CVE cannot block
  an unrelated pull request silently; review its output on each dependency change.
- Windows timings are slow (~2s connection overhead under Docker); not a correctness signal.

## Manual verification

- `docker compose -f compose.dev.yaml ps` → PostgreSQL and Redis healthy.
- `alembic upgrade head` applies all migrations to the dev database.
- `GET /healthz`, `GET /readyz`, `/api/docs` respond locally.
- Website and Mini App visual QA at 390 px and 1280 px (mobile layout checked through a 390 px
  iframe because the browser harness cannot emulate a device viewport); no horizontal page overflow.
- Fake checkout: create order → checkout page → demo confirm → subscription activated; a replay is
  idempotent. The demo notice disappears after payment and the success state renders.
- Admin payment list and detail show the order, provider ID, event log and refund form; report modal
  and MFA settings at `/account/settings#mfa` render and work.
- The Mini App subscription screen disables purchase buttons until Telegram Stars exists; `/buy` in
  the bot never offers a card link for a digital subscription.
