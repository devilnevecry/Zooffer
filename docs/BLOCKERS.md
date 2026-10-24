# Blockers

Items that cannot be completed without an external dependency. Status labels follow master prompt §0.3.

| # | Item | Status | Exactly what is missing | Work already done / fallback |
|---|---|---|---|---|
| B1 | Private GitHub repository `zooffer`, PRs, releases, remote CI | BLOCKED | `gh` CLI and any authenticated GitHub token/credential are absent on this host | Local git repo, `main` + phase branches, tags, CI workflows, exact push commands in ADR 0001 |
| B2 | Live Telegram bot (webhook) | BLOCKED | `TELEGRAM_BOT_TOKEN` and a public HTTPS domain | Bot logic and webhook endpoint implemented and tested with fakes; see `docs/TELEGRAM.md` |
| B3 | Telegram Login / Mini App live auth | BLOCKED | Real bot token, Mini App short name, domain registration in BotFather | Server-side validation implemented and tested with generated fixtures |
| B4 | YooKassa production payments | BLOCKED | `YOOKASSA_SHOP_ID`, `YOOKASSA_SECRET_KEY`, merchant account and fiscalisation setup | Provider interface + fake provider + state machine tested; adapter isolated |
| B5 | Telegram Stars live payments | BLOCKED | Real bot token, Telegram merchant configuration and current Stars policy verification | Bot and Mini App honestly report online payment unavailable; no invoice flow is claimed |
| B6 | Transactional email (verification, recovery, notifications) | BLOCKED for real delivery | SMTP host/credentials and sender domain | `EmailSender` console adapter in dev; SMTP adapter behind config |
| B7 | Russia-located production hosting, domain, TLS | BLOCKED | VPS/provider account and domain | Production compose, Caddy config and runbook prepared; not deployed |
| B8 | Legal entity details (ИП/ООО, ИНН/ОГРН, address) | BLOCKED | Owner-provided registration data | Templates with marked fields; no fabricated details |
