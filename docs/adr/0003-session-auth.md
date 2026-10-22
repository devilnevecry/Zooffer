# ADR 0003 — Server-side sessions in HttpOnly cookies

Date: 2026-10-22
Status: Accepted

## Context

The product needs one identity across web, Mini App and bot, safe logout/revocation, and protection
against token theft. The master prompt requires hashed session storage, rotation, idle/absolute
timeouts and CSRF protection.

## Decision

- A 256-bit random session token is delivered in an `HttpOnly`, `SameSite=Lax`, `Secure` (production)
  cookie. The production name is `__Host-zooffer_session`; development uses `zooffer_session`
  because `__Host-` requires `Secure` and HTTPS.
- Only `HMAC-SHA256(pepper, token)` is stored in `sessions.token_hash`.
- Login always rotates the session; privilege changes rotate again.
- Idle timeout 14 days of inactivity, absolute timeout 60 days (both configurable).
- CSRF: SameSite=Lax plus double-submit token for state-changing requests, with Origin/Referer
  validation. Tokens are bound to the session row.
- The Mini App and bot exchange validated Telegram data for a normal session; they do not receive a
  long-lived bearer token.

## Consequences

- Immediate revocation is possible; the database is the source of truth.
- Horizontal scaling needs no sticky sessions.
- Cookie-authenticated endpoints must all go through the CSRF dependency; tests enforce this for
  state-changing methods.
