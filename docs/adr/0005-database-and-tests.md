# ADR 0005 — PostgreSQL for development, production and tests

Date: 2026-10-22
Status: Accepted

## Context

The core invariants (atomic quota consumption, concurrent matching, FTS with Russian configuration,
row locks) are PostgreSQL-specific. SQLite would silently accept weaker semantics and hide races.

## Decision

Use PostgreSQL 16 everywhere, including integration tests, via Docker Compose. Unit tests that do not
touch the database remain plain pytest. Tests fail with a clear message if the test database is not
reachable; they do not skip silently.

`TEST_DATABASE_URL` points at a dedicated database. A session-scoped fixture creates the schema from
Alembic migrations and truncates tables between tests.

## Consequences

- CI needs a PostgreSQL service container.
- Local contributors run `docker compose -f compose.dev.yaml up -d db redis`.
- JSONB/FTS features are available without fallback code paths.
