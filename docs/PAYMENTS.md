# Payments

Status: fake provider `VERIFIED` end-to-end; YooKassa adapter `IMPLEMENTED-UNVERIFIED`; Telegram
Stars `BLOCKED`; production payments `BLOCKED` until merchant credentials and fiscalisation exist.

## Architecture

```text
client ──POST /billing/orders──▶ billing_service.create_order
                                      │ server-priced plan
                                      ▼
                               PaymentProvider.create_payment
                                      │
             ┌────────────────────────┴────────────────────────┐
             ▼                                                 ▼
   FakePaymentProvider (dev/test)                    YooKassaProvider (live)
   signed local webhook                               redirect + unsigned notification
             │                                                 │
             └──────────────▶ POST /billing/webhooks/{provider} ◀┘
                                      │
                          verify signature / re-fetch
                                      ▼
                        idempotent PaymentEvent insert
                                      ▼
                     order state + subscription + notification
```

## Plan and order rules

- Plans live in the `plans` table; prices are integer kopecks and are **never** accepted from a
  client. `is_placeholder_price` marks pre-launch prices.
- An order is reused for 15 minutes when the same user requests the same plan and a payable order
  with a confirmation URL exists. This prevents duplicate orders from double clicks.
- Orders expire after 30 minutes (`expires_at`).
- A free plan cannot be purchased; production rejects placeholder prices.
- The fake provider is selectable only when `ENVIRONMENT` is `dev` or `test`.

## State machine

| From | Event | To | Side effect |
|---|---|---|---|
| created/pending | pending notification | pending | — |
| created/pending | verified success | paid | `paid_at`, subscription activate/extend, audit, notification |
| created/pending | cancel/fail | canceled/failed | — |
| paid | refund | refunded | refund row, entitlement revoked immediately, notification |
| any | duplicate `provider_event_id` | unchanged | returns `duplicate` |

Order statuses: `created`, `pending`, `paid`, `failed`, `canceled`, `refunded`.
Subscription statuses: `pending`, `active`, `past_due`, `canceled`, `expired`.

## Subscription timing

- First purchase: period starts now and ends `now + period_days`.
- Renewal or plan change while active: the new period is appended to
  `max(now, current_period_end)`, so paid days are preserved.
- Plan change applies immediately; there is no monetary proration.
- Cancellation sets `cancel_at_period_end` and keeps access until the paid period ends.
- Refund/revoke sets `current_period_end = now` and disables entitlements immediately.
- There is no silent auto-renewal. A new payment is required for each period.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/public/plans` | Active plans with placeholder flag |
| GET | `/api/v1/billing/subscription` | Current state, entitlements, quota, demo flag |
| POST | `/api/v1/billing/cancel` | Disable renewal at period end |
| GET | `/api/v1/billing/orders` | Own orders |
| POST | `/api/v1/billing/orders` | Server-priced order or reused payable order |
| GET | `/api/v1/billing/orders/{id}` | Own order only (foreign → 404) |
| POST | `/api/v1/billing/orders/{id}/demo-confirm` | Dev/test only; goes through the signed webhook path |
| POST | `/api/v1/billing/webhooks/{provider}` | Provider callback, rate-limited, 256 KiB cap |
| GET | `/api/v1/admin/payments` | Admin order list |
| GET | `/api/v1/admin/payments/{id}` | Order + provider events |
| POST | `/api/v1/admin/payments/{id}/refund` | Superadmin refund + revoke |
| GET | `/api/v1/admin/payments-reconcile` | Paid orders vs active subscriptions |
| POST | `/api/v1/admin/users/{public_id}/entitlements` | Audited manual grant |
| DELETE | `/api/v1/admin/users/{public_id}/entitlements/{code}` | Remove manual grant |

## Fake/demo flow

1. `POST /billing/orders` creates an order with `provider=fake`, status `pending`, and a
   confirmation URL to `/account/subscription/checkout?order=…`.
2. The checkout page clearly states that this is a simulated payment and that no money moves.
3. `POST /billing/orders/{id}/demo-confirm` creates an HMAC-SHA256-signed webhook with
   `SECRET_PEPPER` and feeds it through the same verification, idempotency and activation code as a
   real provider.
4. Tests cover success, duplicate, bad signature, amount mismatch, currency mismatch, ownership,
   refund, revoke, admin grant and reconcile.

The demo endpoint is hidden when the provider is not `fake` and returns 404, so it cannot be used in
production.

## YooKassa adapter

Implemented against the documented v3 HTTP API:

- `POST /payments` with `Idempotence-Key`, redirect confirmation, server-computed amount.
- `GET /payments/{id}` re-fetch on every notification.
- `POST /refunds` with idempotency.
- Basic-auth with shop ID and secret key.

Important caveats:

- YooKassa notifications are **not signed**. The billing service treats them only as a trigger and
  re-fetches the payment before changing state. The reverse proxy must additionally allow-list
  YooKassa IP ranges in production.
- The adapter has not been run against a real sandbox shop because no credentials exist (B4).
- Receipts/54-ФЗ fiscalisation, recurring consent and refund notification templates are not
  implemented.
- `YOOKASSA_RETURN_URL` must point to the public checkout/return URL.

## Telegram Stars

Digital goods inside Telegram must use Stars (`XTR`) under current Telegram rules. The bot honestly
reports that online payment is unavailable when no provider is configured; it does not fabricate a
successful purchase. Stars invoices, `pre_checkout_query`, `successful_payment` and refunds require a
real bot token and merchant setup (B5).

## Admin controls

- View orders and raw provider events, including signature status and errors.
- Refund a paid order (superadmin only). Entitlement is revoked immediately.
- Manually grant an entitlement with an optional expiry; every action is audited.
- Reconcile report: paid orders, active subscriptions, paid-without-subscription,
  subscription-without-payment, refunded total.

## Operational notes

- Webhook requests are rate-limited per IP and capped at 256 KiB.
- Payment events are deduplicated by `(provider, provider_event_id)` with a unique constraint.
- Provider errors are logged without card data or secrets.
- Configure a dead-letter/alerting path for repeated webhook failures before launch.
