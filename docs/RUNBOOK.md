# Runbook

Status: local development procedures are verified. Production images, compose files and Caddy
configuration are committed; the first real deploy still needs domain, DNS, VPS and tunnel values
(see `docs/DEPLOY.md`). Never run these commands against production without a backup and a change
window.

## Local development

```powershell
docker compose -f compose.dev.yaml up -d
$env:PYTHONPATH='backend'
.venv\Scripts\python -m alembic -c backend\alembic.ini upgrade head
.venv\Scripts\python -m uvicorn zooffer.main:app --host 127.0.0.1 --port 8000
```

Website:

```powershell
cd web
npm install
npm run dev
```

Health checks:

```powershell
curl http://127.0.0.1:8000/healthz
curl http://127.0.0.1:8000/readyz
```

## Tests

```powershell
$env:PYTHONPATH='backend'
.venv\Scripts\python -m pytest backend\tests -q

$env:PYTHONPATH='backend;bot'
.venv\Scripts\python -m ruff check backend scripts bot

cd web
npm run typecheck
npm run lint
npm run build
```

## Database migrations

Apply:

```powershell
$env:PYTHONPATH='backend'
.venv\Scripts\python -m alembic -c backend\alembic.ini upgrade head
```

Rollback one revision (only with a verified backup):

```powershell
.venv\Scripts\python -m alembic -c backend\alembic.ini downgrade -1
```

Never edit an applied migration; add a new one.

## Backups and restore

Production plan (not yet exercised because no host exists):

1. `pg_dump --format=custom --no-owner --file=zooffer-$(date +%F).dump zooffer`
2. Encrypt the dump (age/GPG) and upload to an off-host bucket in Russia.
3. Keep 7 daily, 4 weekly and 12 monthly copies; test a restore quarterly.
4. Restore drill:
   `createdb zooffer_restore && pg_restore --no-owner --dbname=zooffer_restore dump`
   then run migrations and a smoke test against the restored DB.
5. Media backups follow the same schedule (local volume or S3-compatible bucket).

**Restore has not been performed in this environment; it remains a launch blocker.**

## Deploy

The exact two-host procedure is in `docs/DEPLOY.md` (PC: `infra/compose.prod.pc.yaml`; VPS:
`infra/compose.prod.vps.yaml` + `infra/Caddyfile`).

1. Build immutable images: `docker build -t zooffer/app:latest .` and
   `docker build -t zooffer/web:latest web` (compose can build them itself).
2. Run migrations as a one-shot job before starting new app containers.
3. Start backend and web behind Caddy with TLS; start the bot with `restart: unless-stopped`.
4. Register the Telegram webhook only in `BOT_MODE=webhook`; polling needs no registration.
5. Verify `/api/healthz`, `/api/readyz`, login, a listing, a Stars purchase and bot `/start`.
6. Keep the previous image tag for rollback.

## Rollback

1. Stop new containers.
2. Restore the previous image tag.
3. If the schema changed, restore the pre-deploy database dump (do not blindly downgrade in
   production).
4. Re-run health checks and a smoke test.
5. Record the incident and the rollback reason.

## Incident response

1. **Detect:** alert on 5xx rate, webhook errors, failed logins, payment reconciliation mismatch.
2. **Contain:** revoke sessions (`auth_sessions`), rotate the affected secret, disable the provider
   in config if payments are involved.
3. **Assess:** identify affected users/data from audit logs; preserve logs.
4. **Notify:** follow the approved 152-ФЗ breach procedure and legal advice.
5. **Recover:** patch, test, redeploy, verify reconciliation.
6. **Review:** write a post-mortem with timeline and preventive actions.

## Secret rotation

| Secret | Steps |
|---|---|
| `SESSION_SECRET` | Rotating invalidates all sessions (acceptable); deploy and force re-login |
| `SECRET_PEPPER` | **Danger:** it encrypts private data and signs tokens. Requires a migration/re-encryption plan; do not rotate casually |
| `TELEGRAM_BOT_TOKEN` | Revoke in BotFather, set the new token, restart the bot, re-register the webhook |
| `TELEGRAM_WEBHOOK_SECRET` | Set a new value, restart, call `setWebhook` with the new secret |
| Robokassa passwords | Rotate in the merchant cabinet, update the secret store, restart backend |
| `METRICS_TOKEN` | Generate a new value, update Prometheus scrape config, restart backend |

## Reconciliation and support

- `GET /api/v1/admin/payments-reconcile` shows paid orders vs active subscriptions.
- Investigate `paid_without_subscription` and `subscription_without_payment` before granting or
  revoking anything.
- Refunds require superadmin + MFA and immediately revoke entitlements.
- Support replies create an in-app notification for the ticket owner.

## Known operational gaps

- First production deploy (domain, DNS, TLS, tunnel) has not been executed yet.
- No durable bot update queue (Telegram retries cover the normal case).
- No automated backup job or executed restore drill.
- Telegram Stars receipts are provided by Telegram; no separate fiscalisation integration.
- Legal pages contain `<...>` placeholders for the self-employed operator details.
