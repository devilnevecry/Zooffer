# Blockers

Items that cannot be completed without an external dependency. Status labels follow master prompt §0.3.

| # | Item | Status | Exactly what is missing | Work already done / fallback |
|---|---|---|---|---|
| B1 | GitHub remote presentation, PRs, releases, milestones, remote CI | IMPLEMENTED-UNVERIFIED | `gh` CLI/authenticated API token absent; PRs, milestones, labels and CI runs could not be created or observed | Remote `https://github.com/devilnevecry/Zooffer_final` received `main` and tags on 2026-10-25; workflows, templates, Dependabot and CODEOWNERS committed; local CI passes |
| B2 | Live Telegram bot (webhook) | BLOCKED | `TELEGRAM_BOT_TOKEN` and a public HTTPS domain | Bot logic and webhook endpoint implemented and tested with fakes; see `docs/TELEGRAM.md` |
| B3 | Telegram Login / Mini App live auth | BLOCKED | Real bot token, Mini App short name, domain registration in BotFather | Server-side validation implemented and tested with generated fixtures |
| B4 | YooKassa production payments | BLOCKED | `YOOKASSA_SHOP_ID`, `YOOKASSA_SECRET_KEY`, merchant account and fiscalisation setup | Provider interface + fake provider + state machine tested; adapter isolated |
| B5 | Telegram Stars live payments | BLOCKED | Real bot token, Telegram merchant configuration and current Stars policy verification | Bot and Mini App honestly report online payment unavailable; no invoice flow is claimed |
| B6 | Transactional email (verification, recovery, notifications) | BLOCKED for real delivery | SMTP host/credentials and sender domain | `EmailSender` console adapter in dev; SMTP adapter behind config |
| B7 | Russia-located production hosting, domain, TLS, production compose/Caddy | BLOCKED | VPS/provider account, domain, DNS and TLS | Local Compose and runbook target design exist; no production compose/Caddy artifact is committed and nothing was deployed |
| B8 | Legal entity details (ИП/ООО, ИНН/ОГРН, address) | BLOCKED | Owner-provided registration data | Templates with marked fields; no fabricated details |
| B9 | S3-compatible object storage for media | BLOCKED | Bucket, credentials and public media origin/CDN | `MediaStorage` protocol with a local-disk adapter; uploads sniffed, size-limited and re-encoded; no S3 adapter implemented |
