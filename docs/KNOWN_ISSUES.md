# Known issues

Updated: 2026-10-25. Severity: Critical / High / Medium / Low.

| ID | Severity | Area | Description | Status |
|---|---|---|---|---|
| K1 | Low | Tooling | `make` is not installed on the Windows development host; `scripts/ci.ps1` and PowerShell commands are the documented gate | Accepted |
| K2 | Low | Docs | Static screenshots and a banner are committed; there is no demo GIF or video walkthrough | Open |
| K3 | Medium | Repo | Remote `main` and tags are pushed, but branch protection, PR checks, milestones and release publication could not be configured or observed without a GitHub API token | Blocked (B1) |
| K4 | Low | Frontend | Telegram WebApp script loads from telegram.org when the Mini App opens; CSP allowance must be documented | Accepted |
| K5 | Medium | Testing | No high-parallelism concurrency stress test for swipes/quota | Open |
| K6 | Low | Quota | No test at the exact Europe/Moscow midnight boundary | Open (partially covered by date-key logic) |
| K7 | Low | Git | Initial work was committed as a consolidated bootstrap; phase tags start from that commit | Accepted |
| K8 | High | Telegram | Bot/Mini App live behaviour is unverified without a token and HTTPS domain | Blocked (B2/B3) |
| K9 | High | Payments | YooKassa adapter has not run against a sandbox shop; unsigned webhooks need IP allow-listing at the proxy | Blocked (B4) |
| K10 | Medium | Payments | Telegram Stars purchase flow is not implemented; bot and Mini App state that online payment is unavailable and expose no card checkout | Blocked (B5) |
| K11 | Medium | Reliability | Bot update queue is in-process and non-durable; a durable queue is pending | Open |
| K12 | Medium | Security | Bandit, gitleaks, `pip-audit` and `npm audit` are clean, but no ZAP baseline or container image scan was run | Open (partially mitigated) |
| K13 | Medium | e2e | No Playwright/load tests; browser QA was manual | Open |
| K14 | High | Legal | Legal documents, retention schedule and operator details require qualified review | Blocked (B8) |
| K15 | Low | Payments | Chargebacks, partial refunds and fiscalisation are not implemented | Open |
| K16 | Low | Docs | English `README.md` and Russian `README.ru.md` both exist; translation drift is possible | Accepted |
| K17 | Low | Typing | The bot is excluded from mypy because aiogram's `Message \| InaccessibleMessage` unions need narrowing; the shared backend is clean | Open |
| K18 | Medium | Media | Only local-disk storage exists; S3-compatible storage and signed private-document URLs are not implemented | Blocked (B9) |
