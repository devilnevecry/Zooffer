# ADR 0007 — Privacy data separation and allowlisted DTOs

Date: 2026-10-22
Status: Accepted

## Context

The master prompt requires technical, deny-by-default enforcement of owner privacy, not discipline in
individual handlers. A hidden frontend field or a careful join is not sufficient.

## Decision

- Public profile fields (`public_first_name`, `public_last_name`, city/region) live in `profiles`.
- Phone, email, date of birth, address, precise geo, Telegram username/ID and internal account data
  live in `user_private_data` / `auth_identities` / `credentials`.
- Every public endpoint returns a dedicated Pydantic model. ORM objects are never returned directly.
- A contract test pins the exact field set of each public model; adding a field fails CI until an
  explicit allowlist update is reviewed.
- Canary leak tests insert unique sentinels into every private field and scan all public channels.
- Public queries project only allowlisted columns and never join private tables.

## Consequences

- More DTO boilerplate, deliberately.
- Owner display uses `owner_display_name: str | None`; clients render «Владелец» when null.
- Staff tools that need private data require explicit permissions and produce audit records.
