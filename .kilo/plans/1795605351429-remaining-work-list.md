# Remaining Work List

## Backend (mostly done)
- Add automated tests for market, video, channels, organizations, events, stories, QA beyond privacy canaries.
- Co-owner invite/accept endpoints and breed admin endpoints (models exist; services/API missing).
- Market: payment/escrow decision, product image upload via S3 (`market/` prefix), moderation queue.
- Video: upload flow (presigned S3 URLs), processing -> published transitions, feed pagination, view/like dedup.
- Scaling/observability: Redis cache for dictionaries/public lists, metrics dashboards/alerting, CI pipeline.

## Frontend (high priority)
- Routes/pages for lost pets, pet-friendly places, services, organizations, Q&A, events, stories, channels, market, video feed.
- API client wiring and auth/CSRF handling for new modules.
- Reuse design tokens/components; add skeletons and empty states.

## Design/UX
- Component library: modals, drawers, toasts, skeletons, empty states.
- Dark/light theme polish and accessibility (contrast, focus).

## Global strategy
- i18n (ru/en), multi-region cities, multi-currency, partner program, trust & safety tooling.

## Validation
- Smoke tests for market/video flows.
- Full backend suite after each module.
- Web typecheck/lint/build.

## Out of scope for now
- Full video transcoding without ffmpeg.
- Multi-region billing/legal.
