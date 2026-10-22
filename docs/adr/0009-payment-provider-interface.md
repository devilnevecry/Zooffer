# ADR 0009 — Payment provider interface with a tested fake

Date: 2026-10-22
Status: Accepted

## Context

Real YooKassa and Telegram Stars credentials are not available. The master prompt requires working
payment engineering, verified webhooks and idempotency, while forbidding claims that unverified
payments are operational.

## Decision

Define a `PaymentProvider` protocol:
`create_payment(order) -> PaymentIntent`, `verify_webhook(headers, body) -> VerifiedEvent`,
`fetch_payment(provider_payment_id) -> ProviderState`, `refund(...)`.

- `FakePaymentProvider` is used in dev/tests and exercises the full order → webhook → entitlement flow.
- `YooKassaProvider` and `TelegramStarsProvider` implement the protocol behind configuration flags and
  are marked BLOCKED until credentials exist.
- Entitlements activate only after a verified provider event or server-side re-fetch.
- `payment_events.provider_event_id` is unique for idempotency; raw payloads are stored for audit.

## Consequences

- The state machine, idempotency, replay rejection and entitlement logic are testable now.
- Production readiness for payments remains explicitly BLOCKED (see `docs/BLOCKERS.md`).
