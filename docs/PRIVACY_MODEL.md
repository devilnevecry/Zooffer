# Privacy model

Status: implemented and covered by privacy-canary tests (`backend/tests/test_privacy.py`) and IDOR
tests. This document describes what other users may see and how the code enforces it.

## Core rule

A user's public identity is limited to:

- first name;
- optional surname;
- or the neutral label «Владелец» when no public name is available.

Everything else is private: e-mail, phone, messengers, Telegram numeric ID, Telegram username,
internal UUIDs, session data, exact address, online status, photo of the person, documents and
moderation history.

## Data separation

| Data | Storage | Exposure |
|---|---|---|
| Login e-mail | `user_private_data.email_encrypted` + `email_blind_index` | Never in public DTOs; admin view under RBAC |
| Phone / messengers | encrypted private fields | Never public; explicit contact exchange only |
| Password hash | `credentials` | Never exposed |
| Telegram numeric ID | `auth_identities` / `telegram_chats` | Never exposed; used for bot delivery only |
| Telegram username | not used as identity | Not persisted for display |
| Public name | `profiles.first_name`, `profiles.last_name` | Allowlisted public DTO |
| Animals and listings | public tables | Public DTOs after moderation |
| Documents | private media key | No public URL; allow-listed away from `/media` |
| Sessions, MFA, audit | internal tables | Owner/admin scopes only |

Private values are encrypted with a key derived from `SECRET_PEPPER`; lookups use a deterministic
HMAC blind index rather than the plaintext. Internal numeric keys never leave the database; every
public resource uses an opaque UUID `public_id`, and listings additionally use transliterated slugs.

## Enforcement points

1. **Allowlist schemas.** Public endpoints return explicit Pydantic models (`PublicOwnerView`,
   `PublicAnimalView`, `PublicListingView`, matching DTOs). There is no `model_dump()` of ORM objects
   on public routes.
2. **Owner-only routes.** Animals, listings, favorites, conversations, notifications, reports and
   billing are scoped by the authenticated user. Foreign opaque IDs return `404`, not `403`, to avoid
   resource enumeration.
3. **Contacts only by mutual action.** A conversation exists only after a mutual like or an explicit
   inquiry. Contact details are not attached to listings; the wizard rejects contact data and routes
   suspicious listings to manual moderation.
4. **No presence.** There is no online/last-seen field in public responses and no typing indicator.
5. **Owner display name.** `display_name(profile)` returns the configured public name or
   «Владелец». Telegram first name is only a suggestion during onboarding and is validated before it
   becomes the public name.
6. **Admin views.** Staff see more data only behind role checks and MFA; every privileged action is
   written to `audit_log`.

## Canary tests

`test_privacy.py` plants unique canary values in private fields and asserts that public JSON contains
neither the keys nor the values. The suite covers listing detail, search, owner endpoints, matches and
notification payloads. New public fields must update the allowlist and keep the canary suite green.

## Data subject rights

- **Export:** `GET /api/v1/account/export` returns the user's own data as JSON.
- **Deletion:** `DELETE /api/v1/account` requires the exact confirmation word `УДАЛИТЬ`, revokes
  sessions and anonymises/deletes owned content according to retention rules.
- **Correction:** profile, animal and listing endpoints let the owner update their own data.
- **Consent:** registration stores versioned terms/privacy consents with timestamps.

Retention, legal bases and operator details still need qualified Russian legal review; see
[COMPLIANCE.md](COMPLIANCE.md).
