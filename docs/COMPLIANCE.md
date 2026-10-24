# Compliance checklist (Russia)

> This is an engineering checklist, not legal advice. Items marked **REVIEW** require a qualified
> Russian lawyer and the operator's registration details.

## Operator and documents

| Item | Status | Notes |
|---|---|---|
| Legal entity / ИП details (name, ИНН, ОГРН, address) | **BLOCKED** (B8) | Placeholders in `docs/legal`; never fabricated |
| Public offer / terms of use | Template | Requires review before accepting payments |
| Privacy policy (152-ФЗ) | Template | Must name the operator, purposes, legal bases, retention and rights |
| Personal data consent | Implemented | Versioned consent rows at registration and support/partner forms |
| Cookies notice | Template | Session cookie is strictly necessary; analytics must be opt-in if added |
| Contact and support details | Placeholder | Fill before launch |

## Personal data (152-ФЗ)

| Requirement | Implementation | Status |
|---|---|---|
| Lawful purpose and minimal data | Only account, animal, listing and messaging data; no contact details in public listings | Implemented |
| Separate private data | `user_private_data` encrypted; blind index for lookup | Implemented |
| Data localisation | Production must use a Russia-located PostgreSQL host | **BLOCKED** (B7) |
| Subject access / export | `GET /api/v1/account/export` | Implemented |
| Deletion | `DELETE /api/v1/account` with explicit confirmation | Implemented |
| Consent withdrawal | Account deletion and notification preferences | Implemented |
| Retention schedule | Not yet formally approved | **REVIEW** |
| Processor agreements (hosting, SMS/e-mail) | None signed | **BLOCKED** (B6/B7) |
| Cross-border transfer | Avoided by Russia-located hosting; Telegram is a foreign messenger and needs legal analysis | **REVIEW** |
| Security measures | Encryption, RBAC, audit, rate limits, MFA for staff | Implemented (see security report) |
| Breach notification procedure | Draft in `RUNBOOK.md` | **REVIEW** |

## Advertising and partners

| Requirement | Implementation | Status |
|---|---|---|
| Mark advertising / `erid` fields | `PartnerOffer.erid`, `ad_label`; UI shows ad label | Implemented (fields) |
| No invented partners or claims | Zero-partner empty state; seed data only in dev | Implemented |
| Partner disclosure and terms | Offer terms and destination URL displayed | Implemented |
| Advertising registry reporting | Process not established | **BLOCKED** (B8) |

## Payments and consumer protection

| Requirement | Implementation | Status |
|---|---|---|
| Price and terms before payment | Plan cards, period, cancellation and refund summary | Implemented |
| Recurring payment consent | No silent auto-renewal; cancellation path visible | Implemented (design) |
| Receipts / 54-ФЗ online cashier | Not integrated | **BLOCKED** (B4) |
| Refund path | Admin refund revokes entitlement; provider refund call implemented | Fake verified; real provider `BLOCKED` |
| Consistent pricing across web and Telegram | Stars pricing requires a documented conversion policy | **REVIEW** (B5) |
| Card data | Never stored; provider-hosted forms only | Implemented |
| Minors | Age/guardian policy not finalized | **REVIEW** |

## Content and animal welfare

- Prohibited content checks exist in listing validation and moderation.
- The platform does not facilitate the sale of protected species; listings are moderated.
- Adoption/rehoming listings show purpose-aware price labels («В добрые руки», «Переустройство»).
- Welfare and prohibited-sale policy text needs legal/animal-welfare review before launch.

## Telegram

- Bot and Mini App privacy is documented in `docs/TELEGRAM.md`.
- Telegram is a foreign service; the legal basis for processing Telegram identifiers must be reviewed
  and reflected in the privacy policy. **REVIEW**

## Launch gate

Do not accept real payments or publish the public site until:

1. operator details are filled;
2. legal documents are reviewed;
3. Russia-located hosting and backups are in place;
4. YooKassa/Stars sandbox runs and fiscalisation are configured;
5. the breach/incident procedure is approved.
