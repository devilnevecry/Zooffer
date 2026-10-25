# Security policy

## Supported versions

Only the latest commit on `main` is supported. There are no production deployments yet, so no
version is currently operated for real users.

## Reporting a vulnerability

Use GitHub's **private vulnerability reporting** on this repository (Security → Report a
vulnerability). If that is unavailable, contact the repository owner directly through GitHub; do not
open a public issue.

Do not include real user data, tokens, passwords or production secrets in a report. Use redacted
reproductions and the demo dataset.

Please include:

- affected endpoint, page or bot flow;
- reproduction steps and the expected/actual result;
- impact assessment (privacy, account takeover, payment, denial of service);
- the commit or tag where you observed it.

There is no bug-bounty programme and no fabricated security email address. Reports are handled on a
best-effort basis by the maintainer.

## Scope

In scope: authentication and sessions, CSRF, IDOR, private-data exposure, upload handling, swipe
quota enforcement, payment webhook handling, admin permissions and MFA, bot callback signing,
Mini App `initData` validation.

Out of scope: findings that require a compromised device, social engineering, physical access, or
third-party services that the project does not control. Denial-of-service testing against a running
deployment is not permitted without written approval.

## Handling expectations

- Acknowledgement within 5 working days when a maintainer is available.
- A fix is prepared privately; a security advisory and release notes are published after the fix.
- Secrets that leak into history are rotated and the history is rewritten before pushing; see
  `docs/RUNBOOK.md`.
