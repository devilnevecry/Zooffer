# Remaining Work Plan

## Scope
Backend feature coverage is largely complete (Phases 0–3 + partial 4). Remaining work is mostly frontend integration, infrastructure, and cross-cutting concerns.

## Remaining tasks (prioritized)

### 1. Frontend integration (high priority)
- Pages/routes for new modules: lost pets, pet-friendly places, services, organizations, Q&A, events, stories, channels, market, video feed.
- API client wiring and auth/CSRF handling.
- Reuse design tokens/components; add skeletons and empty states.

### 2. Market completion
- Checkout/payment integration decision (escrow vs lead-gen). Currently orders created without payment.
- Product image upload via S3 (media prefix `market/`).
- Shop/product moderation queue in admin.

### 3. Video (Phase 4)
- Transcoding pipeline (ffmpeg) or rely on client-side; HLS generation.
- Upload flow (presigned S3 URLs) and status transitions `processing -> published`.
- Feed pagination and view/like dedup.

### 4. Co-owners & breeds API
- Co-owner invite/accept endpoints (model exists).
- Breed management admin endpoints and seed data loading in production.

### 5. Scaling & observability
- Redis-backed caching for dictionaries and public lists.
- Structured metrics dashboards and alerting.
- CI/CD pipeline (lint, typecheck, tests, migration check).

### 6. Design upgrade
- Component library: modals, drawers, toasts, skeletons, empty states.
- Dark/light theme polish and accessibility (contrast, focus).

### 7. Global strategy
- i18n (ru/en), multi-region cities, multi-currency, partner program, trust & safety tooling.

## Validation
- Add smoke tests for market/video flows.
- Run full backend suite after each module.
- Web build/typecheck/lint.

## Out of scope for now
- Full video transcoding without ffmpeg.
- Multi-region billing/legal.

## Next recommended step
Start with frontend integration for the highest-value modules (lost pets, services, market) to make backend features usable.
PY