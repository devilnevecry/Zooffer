# ADR 0002 — Modular monolith with a shared service layer

Date: 2026-10-22
Status: Accepted

## Context

Zooffer has three clients (website, bot, Mini App) and invariants that must hold across channels:
daily quotas, mutual matching, entitlement checks and payments. The master prompt forbids duplicated
business rules and requires one canonical database.

## Decision

One FastAPI backend structured as a modular monolith (`api`, `services`, `db`, `schemas`). The bot
imports the same services and repositories. The web and Mini App consume the same HTTP API. A
separate worker process handles scheduled/background jobs against the same database.

## Consequences

- Quota and matching transactions are straightforward and testable.
- The bot is a thin adapter; its tests can exercise real services with a fake Telegram transport.
- Scaling is vertical/process-level first; modules are separated by clear boundaries so extraction is
  possible later without rewriting domain logic.
