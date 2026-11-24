# Production deployment

Two hosts, one public domain:

```text
Internet
  │  https://<DOMAIN>
  ▼
VPS — Caddy (TLS) + Next.js website (container "web")
  │      /api/*, /media/*  ──▶ tunnel ──▶ PC:8000 (FastAPI)
  │      /telegram/*       ──▶ tunnel ──▶ PC:8081 (bot, only in webhook mode)
  │      everything else   ──▶ web:3000
  ▼
Home PC (Windows 11 + Docker Desktop)
  backend, bot (polling by default), PostgreSQL, Redis, media volume
```

The bot defaults to **polling**, which works behind NAT/CGNAT and needs no inbound
port. The website always reaches the API through the tunnel, so the PC never has to
accept connections from the open internet.

## What you need

1. A domain, for example `zooffer.ru`, with access to DNS.
2. A VPS with Docker and ports 80/443 open.
3. The Windows 11 PC with Docker Desktop.
4. A bot from [@BotFather](https://t.me/BotFather): token and username.
5. A tunnel between VPS and PC. [Tailscale](https://tailscale.com/) is the simplest:
   install it on both machines and use the PC's `100.x.y.z` address from the VPS.

## 1. DNS

Create an `A` record:

```text
<DOMAIN>  A  <VPS_PUBLIC_IP>
```

Wait until `ping <DOMAIN>` resolves to the VPS.

## 2. Start the PC stack

```powershell
cd C:\path\to\Zooffer

Copy-Item infra\prod.env.example infra\.env
notepad infra\.env          # fill every <PLACEHOLDER>
```

Generate the three secrets (run three times):

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Required values in `infra/.env`:

- `APP_BASE_URL`, `API_BASE_URL`, `PUBLIC_API_URL`, `MEDIA_PUBLIC_BASE_URL` →
  `https://<DOMAIN>`
- `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, `SESSION_SECRET`, `SECRET_PEPPER`,
  `METRICS_TOKEN`
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME`, `TELEGRAM_WEBHOOK_SECRET`,
  `TELEGRAM_ADMIN_CHAT_ID`
- `PAYMENT_PROVIDER=telegram_stars`, `TELEGRAM_STARS_ENABLED=true`

Build and start:

```powershell
docker compose -f infra\compose.prod.pc.yaml up -d --build
```

Apply the database schema and reference data:

```powershell
docker compose -f infra\compose.prod.pc.yaml run --rm backend alembic upgrade head
docker compose -f infra\compose.prod.pc.yaml run --rm backend python scripts/seed_prod.py
```

Create the first administrator. First open the bot, send `/start` and accept the
terms, then:

```powershell
docker compose -f infra\compose.prod.pc.yaml run --rm `
  -e ADMIN_BOOTSTRAP_TOKEN=<LONG_RANDOM_SECRET> `
  backend python scripts/bootstrap_admin.py --telegram-id <YOUR_TELEGRAM_ID>
```

After that, remove `ADMIN_BOOTSTRAP_TOKEN` from the environment.

Check the API locally:

```powershell
curl http://localhost:8000/api/healthz
curl http://localhost:8000/api/readyz
```

Both must answer `{"status":"ok"...}`.

### Tunnel address

In the Tailscale admin console find the PC's address, e.g. `100.101.102.103`.
From the VPS:

```bash
curl http://100.101.102.103:8000/api/healthz
```

If this works, the VPS can reach the backend.

> The PC stack publishes port `8000` so the VPS can reach the API through the
> tunnel. Restrict that port with the Windows firewall to the Tailscale/WireGuard
> interface, and never forward it on the home router.

## 3. Start the VPS stack

```bash
cd /opt/Zooffer          # clone/copy the repository here
cp infra/vps.env.example infra/.env
nano infra/.env          # fill every <PLACEHOLDER>
```

In `infra/.env` on the VPS:

- `ZOOFER_DOMAIN=<DOMAIN>`
- `ZOOFER_EMAIL=<your e-mail for Let's Encrypt>`
- `ZOOFER_BACKEND_UPSTREAM=http://100.101.102.103:8000` (PC tunnel address)
- `ZOOFER_BOT_UPSTREAM=http://100.101.102.103:8081` (only used in webhook mode)
- `NEXT_PUBLIC_TELEGRAM_BOT_USERNAME`, `NEXT_PUBLIC_TELEGRAM_BOT_URL`,
  `NEXT_PUBLIC_TELEGRAM_MINI_APP_URL=https://<DOMAIN>/tg`

Build and start:

```bash
docker compose -f infra/compose.prod.vps.yaml up -d --build
```

Caddy obtains a TLS certificate automatically. Check:

```bash
curl https://<DOMAIN>/api/healthz
curl -I https://<DOMAIN>/
```

## 4. BotFather settings

1. `/setdomain` → choose the bot → `<DOMAIN>` (needed by the site's Login Widget).
2. `/setmenubutton` → choose the bot → URL `https://<DOMAIN>/tg` (Mini App).
3. Optional: `/setdescription`, `/setabouttext`, `/setuserpic`.

Mini App short name: `/newapp` → choose the bot → title `Zooffer` → short name
`zooffer` → URL `https://<DOMAIN>/tg`.

## 5. Verify Telegram Stars

1. Open the bot, send `/start`, accept the terms.
2. Send `/buy`, choose a paid plan.
3. Telegram must show an invoice in **Stars** (XTR), not a card form.
4. Pay the smallest plan once.
5. The bot must answer “Оплата получена”, and `/subscription` shows the active plan.
6. The admin panel must show the payment with a `telegram_payment_charge_id`.

If the invoice does not appear, check `docker compose logs backend bot` for
`telegram` errors and confirm `PAYMENT_PROVIDER=telegram_stars`.

## 6. Legal placeholders

Before public launch, replace the `<...>` fields in the legal pages
(`web/app/(site)/legal/[document]/page.tsx`): ФИО, ИНН, region, address, contact
e-mail/Telegram. The rest of the text is ready to use.

## Updating

```powershell
# PC
git pull
docker compose -f infra\compose.prod.pc.yaml up -d --build
docker compose -f infra\compose.prod.pc.yaml run --rm backend alembic upgrade head
```

```bash
# VPS
git pull
docker compose -f infra/compose.prod.vps.yaml up -d --build
```

## Backups

Database (PC):

```powershell
docker compose -f infra\compose.prod.pc.yaml exec db `
  pg_dump -U zooffer -d zooffer > "zooffer-$(Get-Date -Format yyyy-MM-dd).sql"
```

Media is in the Docker volume `zooffer-prod-pc_media`. Back it up with:

```powershell
docker run --rm -v zooffer-prod-pc_media:/data -v ${PWD}:/backup alpine `
  tar czf /backup/media.tar.gz -C /data .
```

Keep at least 7 daily database dumps and one weekly media archive off the PC.

## Troubleshooting

| Symptom | Check |
|---|---|
| Caddy serves 502 on `/api` | Tunnel address wrong or PC backend down; `curl http://<PC_IP>:8000/api/healthz` from the VPS |
| Website loads but login widget absent | `NEXT_PUBLIC_TELEGRAM_BOT_USERNAME` was empty **during the VPS build**; rebuild web |
| Login widget says “Bot domain invalid” | BotFather `/setdomain` is not set to `<DOMAIN>` |
| Mini App opens blank | `NEXT_PUBLIC_TELEGRAM_MINI_APP_URL` and `/tg` URL in BotFather |
| Invoice not created | Backend logs; `TELEGRAM_BOT_TOKEN` and `TELEGRAM_STARS_ENABLED=true` |
| `Invalid production configuration` at startup | One of the required secrets is missing/short; the message lists each field |
| Bot silent | `docker compose logs bot`; polling mode requires outbound internet only |

## Health endpoints

- `https://<DOMAIN>/api/healthz`
- `https://<DOMAIN>/api/readyz`
- `https://<DOMAIN>/api/metrics` with `Authorization: Bearer $METRICS_TOKEN`
- `https://<DOMAIN>/telegram/webhook/healthz` (webhook mode only)
