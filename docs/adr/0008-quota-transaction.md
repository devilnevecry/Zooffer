# ADR 0008 — Atomic conditional quota update

Date: 2026-10-22
Status: Accepted

## Context

The daily swipe quota must be enforced in the same transaction as the swipe write, across web, bot and
Mini App, and must survive concurrency and retries.

## Decision

Use a single `INSERT … ON CONFLICT … DO UPDATE … WHERE used_count < limit RETURNING` statement on
`daily_quota_usage` inside the swipe transaction. A unique constraint on
`(user_id, target_type, target_id)` makes swipes idempotent. A client-supplied request ID (unique per
user) makes retries safe. Undo deletes the swipe and decrements the counter only if the swipe
consumed quota and no match was created from it.

`quota_date` is computed as `date(now() at time zone 'Europe/Moscow')`.

## Consequences

- No read-modify-write race and no overspend.
- The quota row is a hot spot for a single user; the row lock is short and acceptable.
- The client receives `remaining`, `limit`, and `resets_at` in the swipe response and never computes
  entitlement locally.
