# Security report

Updated: 2026-10-25. Scope: local repository and locally running services. No production deployment
exists, so this is not a production penetration test.

## Automated checks actually run

| Check | Command | Result |
|---|---|---|
| Backend tests | `pytest backend\tests -q` | **74 passed** |
| Python lint/security rules | `ruff check backend scripts bot` | All checks passed |
| Python byte-compile (bot) | `compileall bot` | Passed |
| Web typecheck | `npm run typecheck` | Passed |
| Web lint | `npm run lint` | Passed |
| Web production build | `npm run build` | Passed, 56 routes |

Not run in this environment: ZAP baseline, Bandit, `npm audit`, dependency CVE scan, Playwright e2e,
load tests. These remain open items; see `docs/KNOWN_ISSUES.md`.

## Implemented controls (with evidence)

### Authentication and sessions

- Argon2id password hashing; password policy and login throttling.
- HttpOnly cookie sessions; tokens stored HMAC-hashed; idle and absolute expiry; rotation.
- CSRF double-submit token plus Origin checks on every mutating request.
- TOTP MFA for staff; admin dependencies require **both** `user.mfa_enabled` and
  `session.mfa_verified_at`.
- Replay protection for Telegram Login and Mini App `initData`; single-use link tokens.
- Tests: `test_auth.py`, `test_admin.py` (MFA setup, login, replay, disable).

### Authorization and isolation

- Every user-scoped query filters by the authenticated owner.
- Foreign resources return `404` to reduce enumeration.
- Admin routes declare a permission via `permission_required(...)`; roles are checked centrally.
- Tests: IDOR cases in `test_listings.py`, `test_account.py`, `test_messaging.py`, `test_payments.py`.

### Input, uploads and media

- Pydantic models with `extra="forbid"` on sensitive payloads.
- Images are content-sniffed, pixel/size limited, re-encoded to WebP; EXIF/GPS stripped.
- SVG, text, empty and oversized files are rejected.
- Private documents are not routable through `/media`; path traversal keys are blocked.
- Tests: `test_listings.py`.

### Privacy

- Separate encrypted private-data table with HMAC blind index.
- Public DTO allowlists and a canary test suite.
- No contact details, internal IDs, Telegram IDs/usernames, photos or presence in public responses.
- Tests: `test_privacy.py`.

### Quota and consistency

- Atomic PostgreSQL quota update keyed to Europe/Moscow date; the same service is used by all
  channels.
- Swipe idempotency keys; unique mutual-match constraint.
- Tests: `test_discovery.py`.

### Messaging and abuse

- Conversation participation checks; blocks; report rate limits; support ticket limits.
- Message reports are unique per message/reporter and require participation.
- Tests: `test_messaging.py`, `test_reports.py`, `test_account.py`.

### Payments

- Server-computed prices; no client amounts.
- Fake webhooks are HMAC-signed with the server pepper.
- Event dedupe by `(provider, provider_event_id)`; amount/currency checks; order ownership.
- YooKassa notifications are treated as triggers and re-fetched from the provider API before state
  changes.
- Refund/revoke disables entitlements immediately; admin actions are audited.
- Tests: `test_payments.py` (5 tests, including bad signature, mismatch, duplicate, ownership,
  refund, grant, reconcile).

## Findings and residual risks

| ID | Severity | Finding | Status |
|---|---|---|---|
| R1 | High | Live Telegram and payment integrations are unverified; webhook delivery, Stars invoices and YooKassa sandbox behaviour are unproven | `BLOCKED` (B2–B5) |
| R2 | High | YooKassa notifications are unsigned; reverse-proxy IP allow-listing and egress controls are not configured | Open; code re-fetches payments |
| R3 | Medium | No automated dependency/vulnerability scan or ZAP baseline was run | Open |
| R4 | Medium | No load/concurrency stress test for quota or webhooks | Open |
| R5 | Medium | In-process bot update queue is not durable; crashes can drop updates | Accepted for local; durable queue pending |
| R6 | Medium | Legal documents and retention schedule are templates | `BLOCKED` (B8) |
| R7 | Low | Demo seed data uses generated placeholder photos; never present as real animals | Accepted and labelled |
| R8 | Low | Demo payments are enabled in dev/test only and clearly labelled | Accepted |
| R9 | Low | `npm audit`/Bandit were not available in the offline toolchain | Open |

## Production hardening checklist

- [ ] Strong `SESSION_SECRET` and `SECRET_PEPPER` (≥32 chars, not dev defaults).
- [ ] `COOKIE_SECURE=true`, HTTPS everywhere, HSTS and security headers at the proxy.
- [ ] Reverse-proxy IP allow-list for YooKassa notifications.
- [ ] Rotate bot token, webhook secret and payment keys; store in a secret manager.
- [ ] Enable dependency scanning and container image scanning in CI.
- [ ] Configure alerting for webhook failures, 5xx rate and auth throttling.
- [ ] Run ZAP baseline and a fresh-clone acceptance test before launch.
- [ ] Complete legal review and data-retention approval.
