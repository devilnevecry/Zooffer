# ADR 0010: Visual direction

- Status: accepted
- Date: 2026-10-24
- Phase: 4 (design system)

## Context

The master prompt asks for a character, not a template: friendly, contemporary, confident and a
little playful, with a Princess Blue accent, cool neutral surfaces, editorial photography, selective
Liquid Glass and restrained motion. It also asks for an explicit comparison of 2–3 directions before
building, and forbids the generic AI-template look (gradient orbs, indiscriminate glass, three-box
feature grids, fake statistics).

## Directions considered

1. **Editorial gallery.** Large photography, asymmetric grids, thin rules and generous whitespace;
   the brand colour appears only in punctuation (links, chips, focus rings). Strong for animal
   discovery but risks feeling like a magazine rather than a product, and weak for dense account
   and admin screens.
2. **Soft product UI (chosen).** Cool white and pale blue surfaces, deep Petrol Blue text, Princess
   Blue primary actions, 20–28 px card radii and low-opacity blue-tinted shadows. Photography leads
   public cards; account and admin screens stay calm and legible. Liquid Glass is limited to the
   sticky header, the mobile tab bar, overlay sheets and a few floating controls.
3. **Playful sticker UI.** Saturated pastels, rotated labels and illustrated empty states. Expressive
   but it fights the privacy-first, safety-oriented tone and dates quickly.

## Decision

Direction 2. Concrete tokens live in `web/app/globals.css`:

- Brand ramp: `--brand-50 #eaf3fb` … `--brand-600 #00539c` … `--brand-900 #012a52`.
- Surfaces: white cards on `--surface-2 #eaf0f6`, hairline `--line #dce4ed`, ink `#0b1b2b` /
  `#44566a` / `#7a8ca0`.
- Semantic colours: `--like #ff5d73`, `--skip #5b6b7e`, `--success #1e9e6a`, `--warning #b77900`,
  `--danger #c53b3b`, restrained warm accent `--accent #ffb454`.
- Type: self-hosted **Unbounded** 500/600 for the wordmark and display headings, **Onest**
  400/500/600/700 for body and UI. No CDN fonts.
- Shape: 12 px controls, 20 px cards, 28 px panels, full pills for chips and the tab bar.
- Elevation: only two blue-tinted shadow tokens; borders do most of the separation work.

Liquid Glass is applied selectively with `backdrop-filter: blur() saturate()` plus a brand-tinted
fill and an inner highlight. Opaque fallbacks are provided through `@supports not
(backdrop-filter: blur(1px))`, `prefers-reduced-transparency`, `prefers-contrast: more` and
forced-colors mode. The Mini App re-maps the palette to Telegram theme variables so light and dark
Telegram themes both keep AA contrast.

Motion is CSS-based: entrance reveals, card hover lift, a heart burst on like and a spring-ish tab
indicator. Everything collapses to opacity fades under `prefers-reduced-motion`. Animation touches
only `transform` and `opacity`.

## Consequences

- Public pages are photo-led; account/admin pages are denser but reuse the same tokens.
- The brand is recognisable through the blue ramp and typography rather than gradients.
- Glass is a deliberate accent, never the default container.
- Demo photography is generated placeholder art and is labelled as such; it is not presented as
  real animal photography.

## Evidence

- `web/app/globals.css` tokens, glass fallbacks, dark Telegram theme overrides.
- `web/app/layout.tsx` self-hosted font imports.
- Manual visual QA at 1280 px and 390 px (see `docs/TEST_REPORT.md`).
- Screenshots in `docs/assets/`.
