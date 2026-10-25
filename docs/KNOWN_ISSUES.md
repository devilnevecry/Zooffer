# Known issues

Updated: 2026-10-24. Severity: Critical / High / Medium / Low.

| ID | Severity | Area | Description | Status |
|---|---|---|---|---|
| K1 | Low | Tooling | `make` is not installed on the Windows development host; PowerShell commands are documented instead | Accepted |
| K2 | Low | Docs | Screenshots/demo GIFs are not committed; visual QA was manual | Open |
| K3 | Medium | Repo | No remote GitHub repository, so branch protection, PR checks and releases are not active | Blocked (B1) |
| K4 | Low | Frontend | Telegram WebApp script loads from telegram.org when the Mini App opens; CSP allowance must be documented | Accepted |
| K5 | Medium | Testing | No high-parallelism concurrency stress test for swipes/quota | Open |
| K6 | Low | Quota | No test at the exact Europe/Moscow midnight boundary | Open (partially covered by date-key logic) |
| K7 | Low | Git | Initial work was committed as a consolidated bootstrap; phase tags start from that commit | Accepted |
| K8 | High | Telegram | Bot/Mini App live behaviour is unverified without a token and HTTPS domain | Blocked (B2/B3) |
| K9 | High | Payments | YooKassa adapter has not run against a sandbox shop; unsigned webhooks need IP allow-listing at the proxy | Blocked (B4) |
| K10 | Medium | Payments | Telegram Stars purchase flow is not implemented; bot and Mini App state that online payment is unavailable and expose no card checkout | Blocked (B5) |
| K11 | Medium | Reliability | Bot update queue is in-process and non-durable; a durable queue is pending | Open |
| K12 | Medium | Security | No ZAP/Bandit/npm audit/dependency CVE scan was run in this environment | Open |
| K13 | Medium | e2e | No Playwright/load tests; browser QA was manual | Open |
| K14 | High | Legal | Legal documents, retention schedule and operator details require qualified review | Blocked (B8) |
| K15 | Low | Payments | Chargebacks, partial refunds and fiscalisation are not implemented | Open |
| K16 | Low | Docs | `README.md` is English-only; a Russian mirror is still required by §15 | Open |
