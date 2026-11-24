# Blockers

Items that cannot be completed without an external dependency. Status labels follow master prompt §0.3.

| # | Item | Status | Exactly what is missing | Work already done / fallback |
|---|---|---|---|---|
| B1 | GitHub remote presentation, PRs, releases, milestones, remote CI | IMPLEMENTED-UNVERIFIED | `gh` CLI/authenticated API token absent; PRs, milestones, labels and CI runs could not be created or observed | Remote `https://github.com/devilnevecry/Zooffer_final` received `main` and tags on 2026-10-25; workflows, templates, Dependabot and CODEOWNERS committed; local CI passes |
| B2 | Live Telegram bot | READY-FOR-CONFIG | Deploy with the real `TELEGRAM_BOT_TOKEN`; webhook mode additionally needs a public HTTPS tunnel | Bot supports polling (works behind NAT/CGNAT) and webhook; `infra/compose.prod.pc.yaml` defaults to polling |
| B3 | Telegram Login / Mini App live auth | READY-FOR-CONFIG | Real bot token, Mini App short name and `/setdomain` in BotFather | Server-side validation implemented and covered by tests; website uses the Login Widget |
| B4 | YooKassa production payments | OPTIONAL / BLOCKED | `YOOKASSA_SHOP_ID`, `YOOKASSA_SECRET_KEY`, merchant account and fiscalisation | Not part of the launch; Telegram Stars is the primary provider |
| B5 | Telegram Stars live payments | IMPLEMENTED-UNVERIFIED | Real bot token and first live purchase/refund | Bot and Mini App invoice flow implemented and covered by unit tests; live verification is the remaining step |
| B6 | Transactional email | NOT USED at launch | SMTP host/credentials and sender domain | Email/password auth is disabled in production; Telegram covers auth and notifications |
| B7 | Production hosting, domain, TLS, production compose/Caddy | IMPLEMENTED-UNVERIFIED | VPS account, domain, DNS, tunnel address and TLS | `infra/compose.prod.vps.yaml`, `infra/compose.prod.pc.yaml`, `infra/Caddyfile`, `docs/DEPLOY.md` committed |
| B8 | Operator details | PLACEHOLDERS READY | Owner fills self-employed ФИО, ИНН, address, contact e-mail | Legal pages contain marked `<...>` fields; no fabricated details |
| B9 | S3-compatible object storage for media | BLOCKED | Bucket, credentials and public media origin/CDN | `MediaStorage` protocol with a local-disk adapter; uploads sniffed, size-limited and re-encoded; no S3 adapter implemented |
