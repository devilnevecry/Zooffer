# Requirements traceability

Status labels follow master prompt §0.3: `VERIFIED`, `IMPLEMENTED-UNVERIFIED`, `BLOCKED`,
`NOT STARTED`. Evidence is a test, command output, or a documented run.

## Section-by-section

| Prompt section | Status | Implementation | Evidence / gap |
|---|---|---|---|
| §0 Operating rules | `VERIFIED` | Master prompt studied; `legacy/` ignored, never imported; no fake claims in code | `.gitignore`, this traceability table, blockers list |
| §1 Vision, purposes, matching | `VERIFIED` | Five purposes in `ListingPurpose`; mutual-only match transaction | `test_listings.py`, `test_discovery.py` |
| §2 Lessons learned | `VERIFIED` | No legacy reuse; PostgreSQL invariants; real DTOs | Repository audit, ADR 0002/0005 |
| §3 Architecture | `VERIFIED` | Modular monolith: FastAPI services shared by web/bot/Mini App | `docs/ARCHITECTURE.md` |
| §3.1 Git workflow / private repo | `BLOCKED` (B1) | Local `main`, tags, CI files, exact push commands | No `gh`/GitHub token; see `docs/BLOCKERS.md` |
| §4 Design direction | `VERIFIED` (local) | Princess Blue palette, Unbounded/Onest, editorial cards, selective glass, mobile tab bar | Visual QA at 390/1280; `app/globals.css`, `docs/adr/0010-design-direction.md` |
| §4.7 Homepage sections | `VERIFIED` | All required sections render from API with empty states | `web/app/(site)/page.tsx`; local run |
| §4.8 Motion | `VERIFIED` | CSS entrance/reveal motion plus reduced-motion override | `globals.css`; manual QA |
| §4.10 Responsive | `VERIFIED` | Mobile-first layouts; no horizontal overflow on account/admin grids | 390/1280 QA |
| §4.11 Page inventory | `VERIFIED` | Public, auth, account, admin, legal, support, partners, `/tg/*` | `next build` route table (56 routes) |
| §4.11.1 Listing wizard | `VERIFIED` | Server-autosaved draft wizard on web and Mini App | `test_listings.py`, manual QA |
| §5 Data model | `VERIFIED` | ~56 tables, 3 Alembic migrations | `alembic upgrade head`; `pytest` schema tests |
| §6.1 Discovery/search/filters | `VERIFIED` | Feed, FTS, filters, keyset pagination, URL state | `test_listings.py`, `test_discovery.py` |
| §6.2 Swipes/undo/favorites | `VERIFIED` | Idempotent swipes, entitlement-gated undo, favorites | `test_discovery.py` |
| §6.3 Matching/messaging | `VERIFIED` | Mutual match, one conversation, paginated messages, blocks/reports | `test_messaging.py`, `test_discovery.py` |
| §6.4 Accounts/animals | `VERIFIED` | Password auth, animal CRUD, photo pipeline | `test_auth.py`, `test_listings.py` |
| §6.5 Moderation/reporting | `VERIFIED` | Auto-checks, admin queue, user reports API + UI | `test_admin.py`, `test_reports.py` |
| §6.6 Support | `VERIFIED` | Ticket API, staff reply, user notification | `test_account.py`, `test_admin.py` |
| §6A Privacy model | `VERIFIED` | Encrypted private table, blind index, allowlist DTOs, «Владелец» | `test_privacy.py`, `test_listings.py`, `docs/PRIVACY_MODEL.md` |
| §7 Shared swipe quota | `VERIFIED` | Atomic quota keyed to Europe/Moscow date; all channels use same service | `test_discovery.py`; bot uses `swipe_service` |
| §8.1 Identity/linking | `IMPLEMENTED-UNVERIFIED` (live) | One canonical user; explicit link confirmation; single-use hashed tokens | `test_auth.py`; live bot `BLOCKED` (B2/B3) |
| §8.2 Telegram validation | `VERIFIED` (fakes) | HMAC, freshness, replay protection for Login and `initData` | `test_auth.py` with generated fixtures |
| §8.3 Bot commands/flows | `IMPLEMENTED-UNVERIFIED` | All listed commands, wizard, swipes, chats, settings, honest payment unavailable | `bot/tests`; live bot `BLOCKED` (B2) |
| §8.3 Notifications | `VERIFIED` (worker) | Preference/quiet-hour/dedupe worker with blocked-bot handling | `bot/tests`; live delivery `BLOCKED` (B2) |
| §8.4 Mini App | `IMPLEMENTED-UNVERIFIED` (live) | `/tg/*` screens, `initData` session, WebApp SDK, same API/design | `next build`, local QA; live `BLOCKED` (B3) |
| §8.5 Bot production operation | `IMPLEMENTED-UNVERIFIED` | Webhook secret/dedupe/queue, health, docs | No public HTTPS host (B2/B7) |
| §9.1 Plans/entitlements | `VERIFIED` | DB plans, server-derived entitlements, placeholder-price flag | `test_payments.py`, `test_account.py` |
| §9.2 Providers | `IMPLEMENTED-UNVERIFIED` / `BLOCKED` | Fake provider verified; YooKassa adapter written but not sandbox-run; Stars unavailable. Bot and Mini App expose no card checkout for the digital subscription (Telegram policy) | B4/B5; `docs/PAYMENTS.md` |
| §9.3 Payment engineering | `VERIFIED` (fake) | Server pricing, verified webhook path, replay/idempotency, refund/revoke, admin grant/reconcile | `test_payments.py` (5 tests); real provider `BLOCKED` |
| §10 Partner program | `VERIFIED` | Offers, public page, click tracking, inquiry, ad-label fields, zero-partner empty state | `test_account.py`, manual QA |
| §11 SEO/growth | `VERIFIED` | SSR pages, metadata, sitemap, robots, JSON-LD, OG, canonicals | `next build`; route inspection |
| §12 Security | `VERIFIED` (documented scope) | Sessions/CSRF/IDOR/upload/webhooks/MFA/RBAC | `docs/SECURITY_REPORT.md`; residual risks listed |
| §13 Russian legal | `BLOCKED` (B8) / templates | Consent, offer, privacy, ad marking fields | Legal review required; `docs/COMPLIANCE.md` |
| §14 Phased execution | `VERIFIED` (local) | Phases 1–13 implemented in slices; 14–15 partial/blocked | `docs/IMPLEMENTATION_PLAN.md` |
| §15 Deliverables | `PARTIAL` | Runnable system, tests, docs; remote repo/hosting/live integrations blocked | Final report below |

## Final acceptance gaps

1. **GitHub remote/PRs/releases** — `BLOCKED` (B1): no `gh` or token. Local branches, tags and push
   commands exist.
2. **Live Telegram bot and Mini App** — `BLOCKED` (B2/B3): no bot token or public HTTPS domain.
   Logic and validation are implemented and fake-tested.
3. **Real payments** — `BLOCKED` (B4/B5): no YooKassa merchant credentials or Telegram Stars setup.
   Fake provider is fully exercised; YooKassa requires a sandbox run.
4. **Real e-mail delivery** — `BLOCKED` (B6): no SMTP credentials; console adapter used locally.
5. **Production hosting/domain/TLS** — `BLOCKED` (B7): no infrastructure or DNS.
6. **Legal entity details** — `BLOCKED` (B8): templates contain marked placeholders and require
   qualified Russian legal review.
7. **Browser e2e/Playwright and load tests** — `NOT STARTED`; local visual QA was manual. The
   backend suite and build checks are the current automated evidence.

## Residual risks

- Live Telegram behaviour (webhook delivery, media upload, Stars invoices) is unproven without a bot.
- YooKassa's unsigned notifications require IP allow-listing at the reverse proxy in production; the
  code re-fetches payments, but the network control is not configured.
- Payment provider edge cases (chargebacks, partial refunds, fiscalisation) are not implemented.
- No load/concurrency stress test for quota at high parallelism.
- Legal texts are templates, not reviewed by a lawyer.
