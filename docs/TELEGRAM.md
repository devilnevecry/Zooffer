# Telegram: bot and Mini App

Status: bot logic, webhook security, onboarding, wizard, discovery, chats, notifications, Mini App
screens and Telegram Stars payments are implemented. Live verification needs the real bot token and
a public HTTPS domain (see `docs/DEPLOY.md`).

## Components

| Component | Location | Notes |
|---|---|---|
| Bot entrypoint | `bot/zooffer_bot/__main__.py` | aiogram 3 dispatcher, polling or webhook |
| Handlers | `bot/zooffer_bot/handlers/` | `/start`, menu, wizard, swipes, chats, settings, support, payments |
| Signed callbacks | `bot/zooffer_bot/callbacks.py` | Versioned, HMAC-signed, ≤64 bytes |
| Notification worker | `bot/zooffer_bot/notifications.py` | Preferences, quiet hours, dedupe, retries |
| Mini App | `web/app/tg/*` | Shared API/types/design with the website |
| Session minting | `backend/zooffer/api/v1/auth.py` | Validated `initData` → HttpOnly session |
| Stars payments | `backend/zooffer/services/billing_service.py`, `bot/zooffer_bot/handlers/payments.py` | Invoice, pre-checkout validation, idempotent activation |
| HTML widgets | `bot/zooffer_bot/widgets.py`, `bot/zooffer_bot/handlers/widgets.py` | Bot API 10.4: subscription card and TON wallet payment card, `widget_query` answers |
| Purchase flow | `bot/zooffer_bot/handlers/menu.py`, `bot/zooffer_bot/keyboards.py` | Plan → payment method (Stars / crypto / TON wallet widget); screens are edited, not stacked |

## BotFather setup

1. Create a bot and store the token as `TELEGRAM_BOT_TOKEN` (never commit it).
2. Set the username in `TELEGRAM_BOT_USERNAME` (without `@`).
3. `/setdomain` → choose the bot → the public domain (needed by the website Login Widget).
4. Generate a webhook secret and set `TELEGRAM_WEBHOOK_SECRET` (even in polling mode the backend
   validation requires it when `ENABLE_TELEGRAM=true`).
5. Configure the command list (Russian):

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
   widget - Виджет подписки
   support - Поддержка
   link - Привязать аккаунт
   stop - Отключить уведомления
   ```

6. `/setmenubutton` → URL `https://<domain>/tg` (Mini App).
7. `/newapp` → title `Zooffer`, short name `zooffer`, URL `https://<domain>/tg`.
8. Payments: Telegram Stars works out of the box with the bot token. The invoice uses currency
   `XTR`, `provider_token=""`, and the amount stored in `plans.stars_amount`.
9. For local development, `cloudflared tunnel --url http://web:3000` provides a temporary HTTPS
   hostname. Copy that hostname into `WEB_APP_URL`, `APP_BASE_URL` and `/setdomain`; quick-tunnel
   hostnames change when the tunnel container is recreated.

## Interactive widgets (Bot API 10.4)

- `/widget` or the subscription screen's «📊 Виджет подписки» button sends a native HTML widget
  with live state. The «🔄 Обновить» button produces a `widget_query`, the bot refreshes
  `chat_data` and answers the query.
- «👛 Кошельком Telegram (виджет)» in the payment-method screen sends a payment widget. On tap the
  widget asks the bot for a fresh TON transaction (`request(data, {wallet: true})`), the built-in
  wallet sends it, and the bot records the transaction hash in the order metadata. An operator still
  confirms the payment before activation.
- Requires aiogram ≥ 3.34 (`aiogram==3.34.0` pinned in both pyprojects). Widgets work in private
  chats in production; forwarding/groups remain test-server only.
- **Current status:** the Bot API rejects `sendWidget` for this bot with
  `INPUT_MEDIA_WIDGET_NOT_ALLOWED` (feature is being rolled out by Telegram). The widget buttons
  are therefore hidden in the UI; handlers stay in the code for when access is granted. The
  Mini App at `/tg` is the working rich UI.

## Transport: polling vs webhook

Polling (default in `infra/compose.prod.pc.yaml`) works behind NAT/CGNAT and needs no inbound port:

```powershell
$env:PYTHONPATH='backend;bot'
$env:BOT_MODE='polling'
$env:TELEGRAM_BOT_TOKEN='...'
.venv\Scripts\python -m zooffer_bot
```

Webhook mode additionally requires a public HTTPS URL reachable from Telegram:

```powershell
$env:BOT_MODE='webhook'
$env:TELEGRAM_WEBHOOK_URL='https://<domain>/telegram/webhook'
$env:TELEGRAM_WEBHOOK_SECRET='...'
```

The bot registers the webhook itself on start. The endpoint validates the
`X-Telegram-Bot-Api-Secret-Token` header, deduplicates `update_id`, and can pass updates through a
bounded in-process queue (`BOT_UPDATE_QUEUE=queue`). The queue is not durable; that is tracked in
`docs/KNOWN_ISSUES.md`.

## Authentication and account linking

- Telegram Login and Mini App `initData` are validated server-side: HMAC, age, replay protection.
- The numeric Telegram ID is the identity key. Usernames are never used as identity or displayed.
- Linking requires an explicit inline «Подтвердить привязку» callback. Link tokens are single-use,
  hashed at rest and kept in FSM state until confirmation.
- Mini App auth mints a normal HttpOnly session; an existing website cookie provides account
  continuity as a fallback.
- Telegram first name is only a suggestion for the public name; it is validated by
  `validate_display_name`. Other users see only the public name or «Владелец».
- `/buy` creates a real Telegram Stars invoice. Digital goods inside Telegram must use Stars; no
  external card link is offered inside Telegram.
- `/buy` fails closed when the plan still has `is_placeholder_price=true` or `stars_amount` is unset.

## Telegram Stars lifecycle

1. User sends `/buy`, chooses a plan, or opens the Mini App subscription page.
2. Backend `prepare_stars_order` creates/reuses a `PaymentOrder` with `currency="XTR"` and
   `amount_kopecks=stars_amount`.
3. Bot calls `send_invoice` (bot) or the backend calls `createInvoiceLink` (Mini App).
4. Telegram sends `pre_checkout_query`; the bot validates currency, payload and amount.
5. Telegram sends `successful_payment`; `confirm_stars_payment` activates the subscription once,
   keyed by `telegram_payment_charge_id`.
6. Refund is an explicit admin action and calls `refundStarPayment`; the refund id is stored in the
   payment metadata.

## Privacy in Telegram

- Notifications and callbacks use the same public views as the website.
- No Telegram username, ID, phone or profile photo is shown to other users.
- Deep links use opaque public UUIDs or single-use tokens.
- The bot never requests a phone contact.
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
the same backend API. The subscription page opens the Stars invoice with `openInvoice`.

## Live verification checklist

- [ ] `getMe` succeeds and the token is valid.
- [ ] Webhook registration returns `ok: true`; `getWebhookInfo` shows no errors (webhook mode).
- [ ] `/start` onboarding stores consent and creates one canonical account.
- [ ] Deep links `link_*`, `ref_*`, `listing_*`, `utm_*` resolve correctly.
- [ ] Mini App `initData` mints a session and shows the same account as the website.
- [ ] Website Login Widget signs in the same account.
- [ ] Swipe quota is shared across website, bot and Mini App.
- [ ] `/buy` shows a Stars invoice; payment activates the plan once.
- [ ] Notification respects quiet hours and blocked-bot handling.
- [ ] No private data appears in bot messages or Mini App public views.
