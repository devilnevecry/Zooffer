# Telegram: bot and Mini App

Status: bot logic, webhook security, onboarding, wizard, discovery, chats, notifications and Mini App
screens are implemented. Live verification is `BLOCKED` because no `TELEGRAM_BOT_TOKEN` or public
HTTPS domain exists (B2/B3).

## Components

| Component | Location | Notes |
|---|---|---|
| Bot entrypoint | `bot/zooffer_bot/__main__.py` | aiogram 3 dispatcher, polling or webhook |
| Handlers | `bot/zooffer_bot/handlers/` | `/start`, menu, wizard, swipes, chats, settings, support |
| Signed callbacks | `bot/zooffer_bot/callbacks.py` | Versioned, HMAC-signed, ≤64 bytes |
| Notification worker | `bot/zooffer_bot/notifications.py` | Preferences, quiet hours, dedupe, retries |
| Mini App | `web/app/tg/*` | Shared API/types/design with the website |
| Session minting | `backend/zooffer/api/v1/auth.py` | Validated `initData` → HttpOnly session |

## BotFather setup

1. Create a bot and store the token as `TELEGRAM_BOT_TOKEN` (never commit it).
2. Set the username in `TELEGRAM_BOT_USERNAME` (without `@`).
3. Generate a webhook secret and set `TELEGRAM_WEBHOOK_SECRET`.
4. Configure the command list (Russian):

   ```text
   start - Начать
   menu - Главное меню
   help - Помощь
   settings - Настройки
   profile - Профиль
   mylistings - Мои объявления
   addpet - Добавить питомца
   swipe - Подбор
   favorites - Избранное
   chats - Сообщения
   subscription - Подписка
   buy - Купить подписку
   support - Поддержка
   link - Привязать аккаунт
   stop - Отключить уведомления
   ```

5. Set the menu button to the Mini App URL `https://<domain>/tg`.
6. Register the Mini App domain in BotFather and note the short name.
7. Privacy mode: the bot does not need group messages; keep the default privacy mode.
8. Payments: Stars require a real merchant/bot configuration and are `BLOCKED` (B5).

## Webhook

The default mode is webhook. The bot validates the `X-Telegram-Bot-Api-Secret-Token` header,
deduplicates updates, and optionally processes them through a bounded in-process queue.

```powershell
$env:PYTHONPATH='backend;bot'
$env:BOT_MODE='webhook'
$env:TELEGRAM_BOT_TOKEN='...'
$env:TELEGRAM_WEBHOOK_SECRET='...'
$env:BOT_PUBLIC_URL='https://zooffer.example'
$env:BOT_WEBHOOK_PATH='/telegram/webhook'
.venv\Scripts\python -m zooffer_bot
```

Register the webhook (after DNS/TLS are ready):

```powershell
curl "https://api.telegram.org/bot$env:TELEGRAM_BOT_TOKEN/setWebhook" `
  -d "url=$env:BOT_PUBLIC_URL$env:BOT_WEBHOOK_PATH" `
  -d "secret_token=$env:TELEGRAM_WEBHOOK_SECRET" `
  -d "allowed_updates=[\"message\",\"callback_query\",\"pre_checkout_query\"]"
```

For local development use long polling instead:

```powershell
$env:BOT_MODE='polling'
```

The in-process queue (`BOT_UPDATE_QUEUE=queue`) is bounded and not durable. A durable queue and
external worker are documented as pending work; do not claim production-grade delivery.

## Authentication and account linking

- Telegram Login and Mini App `initData` are validated server-side: HMAC, age, replay protection.
- The numeric Telegram ID is the identity key. Usernames are never used as identity or displayed.
- Linking requires an explicit inline «Подтвердить привязку» callback. Link tokens are single-use,
  hashed at rest and kept in FSM state until confirmation.
- Mini App auth mints a normal HttpOnly session; an existing website cookie provides account
  continuity as a fallback.
- Telegram first name is only a suggestion for the public name; it is validated by
  `validate_display_name`. Other users see only the public name or «Владелец».

## Privacy in Telegram

- Notifications and callbacks use the same public views as the website.
- No Telegram username, ID, phone or profile photo is shown to other users.
- Deep links use opaque public UUIDs or single-use tokens.
- The bot never requests a phone contact unless a documented consented purpose exists.
- `listing_*` links use the listing slug for the Mini App route.

## Notification worker

The worker reads DB notifications and delivers Telegram messages according to per-category
preferences, quiet hours, deduplication (`notification_deliveries`) and a maximum attempt count. It
handles blocked/deleted chats by disabling delivery and never retries forever. In-app notifications
also respect the `in_app` preference.

## Mini App screens

`/tg` (discovery), `/tg/search`, `/tg/listing/[slug]`, `/tg/favorites`, `/tg/matches`, `/tg/chats`,
`/tg/listings`, `/tg/listings/new`, `/tg/profile`, `/tg/subscription`, `/tg/partners`, `/tg/support`.
The Mini App uses `MiniAppChrome` with a bottom tab bar. It does not duplicate business logic; it calls
the same backend API.

## Live verification checklist (blocked)

- [ ] `getMe` succeeds and the token is valid.
- [ ] Webhook registration returns `ok: true`; `getWebhookInfo` shows no errors.
- [ ] `/start` onboarding stores consent and creates one canonical account.
- [ ] Deep links `link_*`, `ref_*`, `listing_*`, `utm_*` resolve correctly.
- [ ] Mini App `initData` mints a session and shows the same account as the website.
- [ ] Swipe quota is shared across website, bot and Mini App.
- [ ] Notification respects quiet hours and blocked-bot handling.
- [ ] No private data appears in bot messages or Mini App public views.
