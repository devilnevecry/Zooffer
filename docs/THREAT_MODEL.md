# Threat model

Version: 1.0 (2026-10-22, Phase 1). Updated each phase.
Guidance referenced: OWASP ASVS 5.0 (target Level 2), OWASP API Security Top 10 (2023), OWASP Cheat
Sheet Series. This document is a living risk model, not a claim of security.

## Assets

1. Account identity and session tokens (web, bot, Mini App).
2. Private owner data: phone, email, date of birth, address, precise geo, Telegram username/ID.
3. Private documents (pedigree papers may contain names/addresses).
4. Conversations and message contents.
5. Payment/subscription records and provider events.
6. Animal/listing data and uploaded media.
7. Staff credentials and audit logs.
8. Availability and integrity of quotas, matching and entitlements.

## Actors

- Anonymous visitor, registered user, paying subscriber, animal owner, conversation participant.
- Malicious user: scraper, spammer, stalker, fraudster, payment abuser.
- Moderator, administrator, superadmin (insider risk).
- External services: Telegram, YooKassa, SMTP, object storage.
- Automated bots/scanners.

## Trust boundaries

Browser ⇄ Caddy ⇄ FastAPI; bot process ⇄ Bot API; Mini App WebView ⇄ API; API ⇄ PostgreSQL/Redis;
API ⇄ object storage; API ⇄ payment provider; staff browser ⇄ admin router; worker ⇄ DB/Telegram.

## STRIDE-style threats and mitigations

| # | Threat | Category | Mitigation | Verification |
|---|---|---|---|---|
| T1 | Private owner data leaks through public API/HTML/metadata/bot | Information disclosure | Separate private table, allowlisted DTOs, no joins, canary leak suite, opaque IDs | `test_privacy_leak*`, schema contract tests |
| T2 | Session theft / fixation | Spoofing | HttpOnly/Secure/SameSite cookie, hashed tokens, rotation on login, idle/absolute expiry, revocation | auth/session tests |
| T3 | Credential stuffing / brute force | Spoofing | Argon2id, per-account/IP/global throttling, generic errors, breached-password hook | rate-limit/auth tests |
| T4 | IDOR/BOLA on animals, listings, conversations, documents | Elevation/Info | Central policy layer + object ownership checks, unguessable IDs, role matrix tests | authorization/IDOR suite |
| T5 | Quota bypass by multi-device/channel or concurrency | Tampering | Canonical counter, atomic conditional UPDATE, same transaction as swipe, unique swipe | concurrency and cross-channel tests |
| T6 | Forged/duplicate match creation | Tampering | Reciprocal-like transaction, canonical pair unique index, block/species/sex checks | matching property tests |
| T7 | Payment forgery/replay | Tampering | Server-computed price, verified provider event, unique `provider_event_id`, transactional entitlement | payment tests |
| T8 | Malicious uploads (polyglot, SVG/script, EXIF GPS, oversize) | Tampering/Info | Content sniffing, re-encode via Pillow, size/dimension limits, generated names, separate origin, private docs signed URLs | upload attack tests |
| T9 | Stored/reflected/DOM XSS | Tampering | React escaping, no unsanitised HTML, CSP with nonces, validation, output encoding | injection corpus, ZAP |
| T10 | CSRF on cookie-auth mutations | Tampering | SameSite=Lax, double-submit token, Origin check, tests for every mutating route class | CSRF tests |
| T11 | SQL injection / mass assignment / open redirect / SSRF | Tampering | ORM parameterisation, allowlisted sort keys, explicit input models, offer-ID redirects, no user-controlled fetches | injection corpus |
| T12 | Spam, scams and contact harvesting in messaging | Abuse | New-account throttle, per-minute/day caps, link/phone heuristics, blocks/reports, no auto contact disclosure | anti-spam tests |
| T13 | Telegram webhook forgery/replay | Spoofing | Secret header verification, `update_id` dedupe, idempotent handlers, fast ACK + queue | bot webhook tests |
| T14 | Forged/stale Mini App `initData` | Spoofing | Server-side HMAC validation, `auth_date` freshness, replay cache, never trust `initDataUnsafe` | initData tests |
| T15 | Insider/staff abuse | Elevation/Info | RBAC least privilege, MFA for staff, re-auth for sensitive actions, append-only audit log | role matrix, audit tests |
| T16 | Enumeration/scraping of listings | Info | Opaque IDs, pagination caps, rate limits, bot controls, no private fields in search index | API abuse tests |
| T17 | Denial of service via expensive queries/uploads | DoS | Query length/complexity caps, body limits, timeouts, per-IP/user limits, pagination caps | abuse tests, load tests |
| T18 | Secrets in repository or client bundle | Info | `.env` ignored, gitleaks pre-commit/CI, secret manager in prod, fail-fast config | gitleaks, bundle scan |
| T19 | Backup loss / ransomware | Availability | Encrypted off-site backups (Russia-localised), restore drills, least-privilege DB roles | restore runbook record |
| T20 | Illegal/prohibited listings (species, cruelty, commercial abuse of adoption) | Compliance | Prohibited-list policy, declarations, moderation queue, reporting taxonomy, takedown | moderation tests + policy docs |
| T21 | Legal non-compliance (152-ФЗ localisation, consent, advertising marking) | Compliance | Compliance checklist, consent versions, RU hosting, ad labels, legal review flags | `COMPLIANCE.md` review |

## Residual risks accepted for now

- No third-party penetration test has been performed.
- Telegram and payment integrations are verified with fakes until credentials exist.
- Moderation is partly manual; automated heuristics are advisory.
- Legal documents are templates requiring qualified Russian legal review.
