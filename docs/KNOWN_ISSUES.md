# Known issues

Updated at the end of every phase. Severity: Critical / High / Medium / Low.

| ID | Severity | Area | Description | Status |
|---|---|---|---|---|
| K1 | Low | Tooling | `make` is not installed on the Windows development host; PowerShell scripts mirror the targets | Accepted; CI uses `make` |
| K2 | Low | Docs | Screenshots and demo GIFs are produced after the UI phase | Open |
| K3 | Medium | Repo | No remote GitHub repository, so branch protection, PR checks and releases are not active | Blocked (B1) |
| K4 | Low | Frontend | Telegram WebApp script is loaded from telegram.org when the Mini App is opened; CSP allowance documented | Accepted |
| K5 | Medium | Testing | Parallel-swipe concurrency stress test is not written yet; ordering was fixed after an FK issue found in tests, but the race itself needs a dedicated property test | Open (Phase 6) |
| K6 | Low | Quota | Quota reset test at the exact Europe/Moscow midnight boundary is still to be added | Open (Phase 6) |
| K7 | Low | Git | Initial work was committed as a consolidated bootstrap because the session started before the repo had any commit; phase branches/tags begin from that commit | Accepted |
