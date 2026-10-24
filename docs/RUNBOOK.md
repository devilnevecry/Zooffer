# Runbook

Status: local development procedures are verified. Production deployment, TLS, DNS and backups are
`BLOCKED` until hosting and credentials exist (B7). Never run these commands against production
without a backup and a change window.

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

## Deploy (target design)

1. Build immutable images for backend, web and bot.
2. Run migrations as a one-shot job before starting new app containers.
3. Start backend and web behind Caddy/Nginx with TLS; start the bot with `restart: unless-stopped`.
4. Register the Telegram webhook with the production secret.
5. Verify `/healthz`, `/readyz`, login, a listing, a test payment in sandbox, and bot `/start`.
6. Keep the previous image tag for rollback.

No production compose/Caddy files are currently committed as verified deployment artifacts; do not
claim a deployment.

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
| YooKassa keys | Rotate in the merchant cabinet, update the secret store, restart backend |
| SMTP credentials | Rotate at the provider, update the secret store, send a test e-mail |

## Reconciliation and support

- `GET /api/v1/admin/payments-reconcile` shows paid orders vs active subscriptions.
- Investigate `paid_without_subscription` and `subscription_without_payment` before granting or
  revoking anything.
- Refunds require superadmin + MFA and immediately revoke entitlements.
- Support replies create an in-app notification for the ticket owner.

## Known operational gaps

- No production host, DNS, TLS or monitoring.
- No durable bot update queue.
- No automated backup job or executed restore drill.
- No fiscalisation/receipt integration.
- Legal and retention procedures await review.
