# Production deployment

Status: the artifacts committed in this repository target a two-host topology:
**VPS (public TLS)** runs Caddy + the Next.js web app; the **home PC** runs the
FastAPI API, Telegram bot, PostgreSQL and Redis.

This topology keeps the full backend on the user's own hardware while the domain
stays with a small public VPS, so there is no extra paid server to operate.

## Topology

```text
Internet
  |
  |  Caddy (TLS) on VPS  https://zooffer.ru
  |     /api/*      -> PC:8000
  |     /media/*    -> PC:8000
  |     /telegram/* -> PC:8081
  |     /*          -> VPS:3000 (Next standalone)
  |
  v
Home PC (Windows 11 + Docker Desktop)
  zooffer-prod-pc: db, redis, backend (:8000), bot polling (:8081)
  media stored on local volume
```

- Website and Mini App are served from the VPS domain.
- The API, media and bot endpoints are reached through a private tunnel (Tailscale
  or WireGuard) or Cloudflare Tunnel to the PC. Caddy must resolve the tunnel address.
- Telegram updates reach the bot either via `BOT_MODE=webhook` (then set
  `TELEGRAM_WEBHOOK_URL=https://zooffer.ru/telegram/webhook`) or via polling from
  the PC.

## One-time setup

1. Build images:

   ```bash
   docker build -t zooffer/backend backend
   docker build -t zooffer/web web
   ```

2. Copy `infra/prod.env.example` to the backend environment (compose project
   `zooffer-prod-pc`) and fill: `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, `SESSION_SECRET`,
   `SECRET_PEPPER`, `METRICS_TOKEN`, `TELEGRAM_*`.

3. Copy `infra/vps.env.example` to a file with mode `0600` and fill
   `ZOOFER_DOMAIN`, backend upstreams, Telegram bot values and secrets.

4. Prepare VPS:

   ```bash
   apt-get update && apt-get install -y docker.io caddy
   # or use docker compose with the caddy image
   mkdir -p /var/lib/caddy
   cp infra/Caddyfile /etc/caddy/Caddyfile
   ```

5. Public DNS: `A @ <VPS_IP>` for `zooffer.ru`, point `t.me` bot username at the
   Telegram server (BotFather), and set a public bot webhook or keep polling.

6. Migrate:

   ```bash
   docker compose -f infra/compose.prod.pc.yaml run --rm backend alembic upgrade head
   docker compose -f infra/compose.prod.pc.yaml run --rm backend python scripts/seed_prod.py
   docker compose -f infra/compose.prod.pc.yaml run --rm backend python scripts/bootstrap_admin.py --telegram-id <ID>
   ```

7. Backup (PC):

   ```bash
   docker compose -f infra/compose.prod.pc.yaml exec db pg_dump -U zooffer -d zooffer > backup_$(date +%F).sql
   docker run --rm -v zooffer_prod_pc_pgdata:/data zooffer/backend tar czf /data/media.tar.gz -C /data/media . 2>/dev/null || true
   ```

## Health checks

- API: `https://zooffer.ru/api/healthz`, `https://zooffer.ru/api/readyz`, `https://zooffer.ru/api/metrics` (Bearer token).
- Bot webhook: `https://zooffer.ru/telegram/webhook/healthz` (if webhook mode).

## Security baseline (Caddy)

The committed `infra/Caddyfile` sets HSTS, `nosniff`, `X-Frame-Options: DENY`,
zstd/gzip. Telegram WebApp scripts are loaded from `https://telegram.org`, so the
VPS must not force a restrictive CSP beyond the proxy defaults until the bot widget
is configured on the domain.

## Operational runbook

See `docs/RUNBOOK.md`. Backup schedule, log rotation, alerts and tests are still
tracked in `docs/BLOCKERS.md` (B7 remains open until the first production deploy).
