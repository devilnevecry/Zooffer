# ADR 0004 — Opaque public identifiers

Date: 2026-10-22
Status: Accepted

## Context

The privacy model forbids exposing internal IDs, Telegram IDs and usernames in URLs, payloads, deep
links, callbacks and analytics. Sequential IDs also enable enumeration.

## Decision

- Internal primary keys are UUIDv4 (database `uuid`).
- Public owner identity is a separate opaque `public_id` UUID.
- Listings and animals expose a `public_id` UUID plus a human-readable slug
  (`/listings/<slug>-<shortid>`); lookup uses the full opaque identifier, not a sequence.
- Bot callback data uses short opaque tokens referencing server-side state, never raw internal IDs.
- Telegram numeric IDs live only in `auth_identities` / private tables and are never serialised into
  public DTOs.

## Consequences

- URLs are stable and shareable without leaking identity.
- Slug changes need 301 handling; old slugs are stored in a redirect table when implemented.
- Debugging requires an internal-id lookup tool; that is staff-only and audited.
