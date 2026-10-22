# ADR 0006 — npm workspaces instead of pnpm

Date: 2026-10-22
Status: Accepted

## Context

`pnpm` is not installed on the development host; npm 11.17 is. The master prompt does not mandate a
package manager, only pinned dependencies and committed lockfiles.

## Decision

Use npm workspaces. Commit `package-lock.json`. Pin runtime dependencies exactly; use `npm ci` in CI.

## Consequences

- Reproducible installs on CI and this host.
- Slightly slower installs and larger `node_modules` than pnpm; acceptable for the monorepo size.
