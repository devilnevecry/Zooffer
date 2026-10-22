# Architecture decision records (index)

Short ADRs live in `docs/adr/`. Each records context, decision, consequences and status.

| ADR | Decision |
|---|---|
| [0001](adr/0001-local-first-repository.md) | Local-first repository because GitHub CLI/token are unavailable |
| [0002](adr/0002-modular-monolith.md) | Modular monolith with shared service layer, not microservices |
| [0003](adr/0003-session-auth.md) | Server-side sessions in HttpOnly cookies with hashed tokens |
| [0004](adr/0004-opaque-public-ids.md) | UUID public IDs plus transliterated slugs; never internal/sequential IDs |
| [0005](adr/0005-database-and-tests.md) | PostgreSQL 16 for dev/prod/tests; no SQLite emulation of invariants |
| [0006](adr/0006-npm-workspaces.md) | npm instead of pnpm on this host; lockfile committed |
| [0007](adr/0007-privacy-data-separation.md) | Separate private-data table and allowlisted DTOs |
| [0008](adr/0008-quota-transaction.md) | Conditional atomic UPDATE for daily quota |
| [0009](adr/0009-payment-provider-interface.md) | Provider interface with tested fake; YooKassa/Stars adapters behind it |
| [0010](adr/0010-design-direction.md) | Chosen visual direction (Phase 4) |

## Other significant decisions

- **2026-10-22 — Windows development, Linux deployment.** `make` targets are canonical for CI/Linux;
  PowerShell scripts under `scripts/` reproduce them on this host. Deployment uses Docker on Linux
  so case-sensitivity and permissions are tested in the target environment.
- **2026-10-22 — Money as integer kopecks.** Currency is always stored explicitly (`RUB`). Prices in
  Telegram Stars are stored as integer Stars in a separate field where relevant.
- **2026-10-22 — Timezone.** Quota dates use `Europe/Moscow`; all timestamps are stored in UTC.
- **2026-10-22 — Telegram identity.** Numeric Telegram user ID is the only identity key; usernames
  are never persisted as identity and never displayed to other users.
- **2026-10-22 — No legacy reuse.** `legacy/` is git-ignored; no code, secret, ID or asset is copied.
