# ADR 0001 — Local-first repository

Date: 2026-10-22
Status: Accepted (constraint-driven)

## Context

The master prompt requires a private GitHub repository `zooffer` as the first action. On this host
there is no `gh` CLI, no `GH_TOKEN`/`GITHUB_TOKEN`, and no authenticated GitHub credential helper.
Inventing a remote or claiming a push would violate the evidence rules.

## Decision

Initialise the repository locally on `main`, build the complete branch/tag structure locally, and
record the exact remote-creation and push commands. Never print or store credentials. Re-attempt the
remote setup only when the owner supplies authenticated access.

## Consequences

- Phase branches and annotated tags exist locally and can be pushed later unchanged.
- PRs, releases and milestones on GitHub cannot be created yet. This is a `BLOCKED` item in
  `docs/BLOCKERS.md`, not a completed deliverable.
- README badges do not claim a CI run that has not happened on a remote.

## Exact commands once authenticated

```bash
gh auth login
gh repo create zooffer --private --source=. --remote=origin \
  --description "Zooffer — animal discovery and marketplace platform" \
  --push
git push --all origin
git push --tags origin
```
