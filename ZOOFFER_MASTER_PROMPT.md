# ZOOFFER — MASTER IMPLEMENTATION PROMPT

You are an autonomous senior full-stack engineer, security engineer and product designer. Your job is to **build Zooffer from scratch as a real, working, production-oriented product** — website, backend, database, Telegram bot and Telegram Mini App — in verified phases, with real code, real tests and honest reporting.

This document is the single source of truth. It is self-contained. Do not ask me to supply other prompts. Where a decision is not specified, make the most defensible one, record it in `docs/DECISIONS.md` (short ADR format), and continue.

---

## 0. OPERATING RULES (READ FIRST)

1. **Build, don't describe.** Never stop after a plan, mockup, frontend shell, schema diagram or progress report. Keep producing code, tests and fixes until the whole project is complete or an external dependency genuinely blocks you.
2. **From scratch, with a legacy folder as a read-only reference.** Build a clean implementation in a new repository. Earlier attempts may exist in the workspace (typically `legacy/Zooffer/`, a larger FastAPI + aiogram prototype, and possibly `Zooffer2/`, a small bot + Flask prototype). Rules:
   - They are *product-intent references only*. Never build on them, never continue them, never copy the old design, and never include the legacy folders in the new repository (keep them outside the repo or git-ignored).
   - You **may read `legacy/Zooffer/` for ideas** on isolated technical pieces — e.g. peppered HMAC hashing of secret keys, upload validation, keyset pagination, service/repository layering, test layout, CI setup, Alembic usage. Re-implement each piece in the new architecture, adapt it to this specification, and cover it with new tests. Do not paste code unreviewed: the old code was never proven to work end to end and has known flaws (§2).
   - `Zooffer2/` is not a source of reusable code.
   - Never reuse any secret found in legacy files (assume every legacy token is compromised and must be rotated), never read `.env` values into logs or docs, and never use any legacy hard-coded IDs.
3. **Evidence over claims.** A feature counts as done only if it is implemented *and* covered by a passing test or a documented manual verification. A pretty React component, a button with local state, or a success page does not prove authentication, payments, a shared database or a Telegram integration exists. Every report must label each feature with exactly one status:
   - `VERIFIED` — implemented and a test/run proves it (cite the test or command);
   - `IMPLEMENTED-UNVERIFIED` — code exists, not yet proven (say why);
   - `BLOCKED` — needs an external credential/service (name it exactly);
   - `NOT STARTED`.
4. **No fake functionality.** Every visible primary action must really perform its advertised function against the backend. No mock data in production paths, no random matches, no client-side-only quotas, no simulated payments marked as real.
5. **Credentials and external services.** Never invent credentials, never send real messages to real users, never make real payments in tests, never claim a deployment that did not happen. If a credential is missing (Telegram bot token, YooKassa keys, domain, SMTP, VPS), implement the integration boundary behind an interface, test it with provider sandboxes/fakes, record the exact missing item in `docs/BLOCKERS.md`, and continue with independent work.
6. **Verify current facts.** Telegram Bot API / Mini App docs, Telegram Stars rules, YooKassa docs, OWASP guidance and Russian legislation change. Before implementing each of those areas, consult the current official source (web search/fetch if available) and cite it in the relevant doc with the date checked. Do not rely on memory.
7. **Incremental checkpoints.** Work in the phases in §14. After each phase: code + tests pass, linters pass, docs updated, the phase pushed to its own branch and tagged as a version (§3.1), short status report. Then continue immediately to the next phase.
8. **Fix what you find.** If a test or scanner reveals a bug or vulnerability, fix it in the same phase or log it with severity in `docs/KNOWN_ISSUES.md`.
9. **Language.** All user-facing text is natural Russian. Code, identifiers, comments, commit messages and docs for developers are in English. The brand is written exactly **Zooffer** (Latin letters) everywhere.
10. **Creative freedom in design, strictness in engineering.** §4 describes a design *direction and character*, not a template. You are expected to create something better than any earlier concept, not to reproduce it. Conversely, privacy (§6A) and security (§12) are non-negotiable architecture requirements, present from Phase 1, not a final checklist.
11. **Scope honesty.** This document was written without access to the earlier React concept's source, the reference images, or a rendered view of the reference website. Do not assume details of them beyond what is written here; if such files exist in the workspace, inspect them yourself.

---

## 1. PRODUCT VISION

**Zooffer** is a Russian-first animal discovery and marketplace platform for Russia. It combines:

- Tinder-style discovery (swipe cards) of animals;
- likes, skips, undo, favorites, **mutual** matches and persistent messaging;
- animal profiles and classified listings;
- sale of animals **with** pedigree and **without** pedigree;
- ordinary mating (no pedigree required);
- pedigree-oriented breeding;
- adoption and rehoming;
- account creation and ongoing account/animal management;
- a free configurable daily swipe allowance and paid subscriptions;
- partner offers and promo discounts (pet food, retail, vet, grooming, services);
- search, filters, SEO and organic growth;
- **three interfaces on one product**: website, Telegram bot, Telegram Mini App — one identity, one backend, one database;
- **strict owner privacy**: other users see an owner only by first name and optional surname (§6A).

The initial market is Russia: Russian language, rubles (₽), Russian payment/legal context, Yandex-friendly SEO, hosting that supports Russian personal-data localization.

### 1.1 Listing purposes (enum `listing_purpose`)

| Code | Russian label | Notes |
|---|---|---|
| `sale` | Продажа | Price in ₽; pedigree optional (attribute). |
| `mating` | Вязка | Ordinary mating; no pedigree needed; optional fee or "по договорённости". |
| `breeding_pedigree` | Племенная вязка | Pedigree documents expected; show pedigree badge only when documents are attached. |
| `adoption` | Отдам в добрые руки | Free; no price field; moderation stricter on commercial abuse. |
| `rehoming` | Пристройство | Free or symbolic fee; owner circumstances note. |

**Pedigree is an attribute of the animal** (`has_pedigree`, `pedigree_registry` such as РКФ/FCI/WCF/other, `pedigree_number`, optional uploaded document), **never a prerequisite** for publishing a listing. A "Родословная" badge appears only when the owner declares it; a stronger "Документы загружены" label appears when a document is attached; Zooffer must **not** claim it verified authenticity unless a real verification process exists.

### 1.2 Matching semantics (important — implement exactly)

- **Mating / pedigree breeding** (animal ↔ animal): a **match** exists only when owner A liked owner B's animal *and* owner B liked owner A's animal, with species compatibility, opposite sex (where applicable) and non-blocked status. One-sided likes **never** create a match. Matches are never random or seeded. Matching is created inside a database transaction guarded by unique constraints so concurrent likes cannot double-create or miss a match.
- **Sale / adoption / rehoming** (person → listing): a like means "interested / saved". It does **not** auto-open a chat. A conversation opens when the interested user presses **«Написать владельцу»** (an *inquiry*, rate-limited, subject to the owner's block list), and the owner may reply, mute or block. This is explicitly not a "match" and must not be labelled one.
- Conversations are persistent, server-stored and shared across website, bot and Mini App.
- Neither a like, a match, an inquiry nor a profile view ever discloses contact details. Contacts can only be shared voluntarily by a user inside a conversation (§6A.4).

---

## 2. LESSONS LEARNED FROM PRIOR ATTEMPTS (do not repeat)

Two earlier attempts existed. Use these as warnings:

- A first prototype was a minimal Telegram bot + Flask page. Flaws: the web page exposed a **bot-token-bearing file URL** to the browser; login keys stored in plaintext with no expiry; a conversation handler crashed because a callback update was treated as a message; a SQLAlchemy `DetachedInstanceError` from using ORM objects after session close; `debug=True`; an empty template.
- A second, much larger attempt (FastAPI + aiogram + Postgres + Redis + Celery) had decent layering, but also: a placeholder instead of a real JS library; a template file with a typo extension; Sentry in dependencies but never initialised; a **hard-coded default admin Telegram ID** in config; documentation that disagreed with pinned dependency versions; committed `.env` files; large dead files (`bot_full_code.txt`, backup dirs, caches) in the repo; Tailwind via CDN in production; and a **generic purple-gradient look with blanket glassmorphism on every surface**, which contradicts the intended brand (selective, original Liquid Glass per §4.5.2 is welcome; indiscriminate glass is not).
- The first prototype's web page also displayed a user's phone number, date of birth and description to anyone holding a login link — exactly the kind of leak §6A forbids.
- Previous React concept work produced attractive screens with **no real auth, payments, shared database or Telegram app behind them**.

Therefore: no secrets in git, no default admin identities, no placeholder assets, no CDN-only runtime dependencies, no dead files, docs generated/checked against reality, and real end-to-end flows.

---

## 3. ARCHITECTURE (DEFAULTS — deviate only with a written ADR)

- **Backend:** Python 3.12+, FastAPI (async), SQLAlchemy 2.x + Alembic, PostgreSQL 16, Redis (rate limits, short-lived state, pub/sub), a task queue/worker (Celery or Arq) for notifications, expirations, image processing and scheduled jobs. Pydantic v2 for all request/response validation. OpenAPI schema is the contract.
- **Frontend:** TypeScript + Next.js (App Router) with server-side rendering for public/indexable pages (SEO) and client components for interactive areas. One design-system package shared by the website and the Mini App (Mini App lives under `/tg/*` routes optimised for Telegram's WebView). Tailwind with design tokens from §4 (compiled, not CDN). Animation library of your choice (e.g. Motion/GSAP) with strict performance budgets.
- **Telegram bot:** aiogram 3.x, **webhook** delivery in production (long polling allowed only in local dev), FSM state stored in Redis with TTL, persistent data in PostgreSQL.
- **Realtime messaging:** WebSocket or SSE with a polling fallback; persistence in PostgreSQL is the source of truth.
- **Media:** object storage abstraction (S3-compatible, e.g. MinIO or a Russian provider) with local-disk adapter for dev; image processing pipeline (re-encode, strip EXIF/GPS, generate sizes/WebP/AVIF).
- **Reverse proxy:** Caddy or nginx with automatic HTTPS, security headers, request limits.
- **Observability:** structured JSON logs with correlation IDs, Prometheus metrics (protected), health/readiness endpoints, error tracking via a **self-hosted** option (e.g. GlitchTip/Sentry self-hosted) or a provider approved in `docs/COMPLIANCE.md` — do not send Russian users' personal data to foreign SaaS without a documented legal basis.
- **Monorepo layout (suggested):** `backend/`, `bot/` (thin; calls shared domain services), `web/` (Next.js incl. `/tg`), `packages/ui`, `infra/` (compose, proxy, backup scripts), `docs/`, `tests/e2e`. The bot and website **call the same domain/service layer** — no duplicated business rules.
- **Single source of truth:** all state (users, animals, listings, swipes, quotas, matches, messages, subscriptions, partner data) lives in PostgreSQL behind the backend. Clients (web, bot, Mini App) hold no authoritative state.

Required quality gates in CI (GitHub Actions or equivalent, runnable locally via `make ci`): lint + format (ruff, eslint, prettier), type-check (mypy/pyright, tsc), unit + integration tests, e2e tests, dependency audit (pip-audit, npm audit), secret scan (gitleaks), SAST (bandit/semgrep), container scan (trivy). Pin dependency versions; commit lockfiles.

---

### 3.1 Repository, Git workflow and presentation (do this first)

The repository is a deliverable. When I open it later it must look like a professionally maintained product repository — clean, consistent, honest and visually polished — "10 out of 10".

**Create the repository before any other work (start of Phase 1)**
- Create a **private** repository named `zooffer` on GitHub (default host; use GitLab only if GitHub is impossible and record why in an ADR). Prefer the GitHub CLI (`gh repo create zooffer --private ...`) using credentials already available in the environment. Verify visibility afterwards (e.g. `gh repo view --json visibility`) and **never make it public**.
- Never ask for, print, write to files, commit, or log any access token. Credentials come from the environment only.
- If no authenticated access exists: initialise the repository locally with the exact same structure and branches, record the exact blocker in `docs/BLOCKERS.md`, give me the precise commands to create the private remote and push everything, and continue working. Do not claim the repository was pushed unless you pushed it.
- Initialise with `main` as the default branch. Set the repository description, topics and (where possible) a social-preview image. Leave the website URL empty until a real production site exists.

**Branching and versions (every version lives on its own branch)**
- Each phase of §14 is one version. Work on `phase/NN-short-name` (e.g. `phase/01-foundation`, `phase/06-swipes-matching-quotas`); sub-branches such as `feat/...` or `fix/...` may be used inside a phase and merged into it. Each phase branch starts from the previous phase's verified state, so the branches form a readable, cumulative history.
- At each verified checkpoint: push the phase branch, open a pull request into `main` with a proper description (what changed, how it was tested, status labels, screenshots when UI changed), let CI pass, merge, and create an annotated tag `v0.N.0` plus a GitHub Release with honest release notes. **Do not delete phase branches** — every version stays available as its own branch.
- After the final phase and the self-check, cut `release/1.0` and tag `v1.0.0` only if all acceptance criteria are met; otherwise tag a pre-release and list what is outstanding.
- `main` always contains the latest verified state and must build and pass CI. Never force-push shared branches. Never rewrite published history. If branch protection is unavailable on the plan, document the conventions instead.

**Commits**
- Small, atomic commits following Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`, `ci:`, `perf:`, `security:`), imperative subject ≤ 72 characters, with a body explaining why where non-obvious. No "wip", "fix stuff" or giant mixed commits.
- Secret-scanning (gitleaks) runs in pre-commit and CI. No secret may ever enter history; if one does, rotate it and rewrite *before* anything is pushed, and document it.
- Never commit: `.env*` with values, virtual environments, `node_modules`, caches, coverage files, build output, logs, database files, backups, uploads, IDE folders, large binaries, generated dumps or leftover scratch files (the old attempts contained such junk). Maintain a thorough `.gitignore`, `.gitattributes` (line endings, linguist settings) and `.editorconfig`.

**Repository presentation (all required)**
- **README.md** (English, polished, scannable): original Zooffer wordmark/banner (SVG, created for this project), only *real* badges (CI status, version, licence), a one-paragraph pitch, key features, a **Mermaid architecture diagram**, real screenshots or short GIFs of the actual running app (website, Mini App, bot) stored optimised in `docs/assets/` and captured with seed/demo data containing no personal data or secrets, tech stack, quickstart (`make dev`) that actually works, project structure, configuration table of environment variables, testing and security overview, links into `docs/`, and an **honest implementation-status table** using the §0 labels. No invented statistics, no claims of production deployment that did not happen.
- **README.ru.md**: a concise, natural Russian companion (overview, quickstart, links), cross-linked from the English README.
- Root files: `LICENSE` (default to a proprietary "All rights reserved" notice for the Zooffer project unless I instruct otherwise; record the decision), `CHANGELOG.md` (Keep a Changelog format, kept current per version), `CONTRIBUTING.md` (setup, branching, commit style, tests, review checklist), `SECURITY.md` (private vulnerability reporting via GitHub's mechanism or a configured contact — never a fabricated address), `CODEOWNERS`, `.github/` with issue templates (bug, feature, security-hardening task), a pull-request template, `dependabot.yml`, CI workflows (lint, test, e2e, security scans) and a release workflow.
- **Issues and milestones:** create a milestone per phase and issues for notable deliverables and known gaps (`docs/BLOCKERS.md` and `docs/KNOWN_ISSUES.md` items should have matching issues); consistent labels (`phase`, `security`, `privacy`, `telegram`, `payments`, `design`, `blocked`, …).
- **Structure and naming:** tidy monorepo (§3), consistent naming and formatting enforced by tooling (ruff/black or ruff format, eslint/prettier), a `docs/README.md` index linking every document, ADRs in `docs/adr/`, no dead code, no duplicated documents, no TODO litter, no stale docs. Documentation must be generated from or checked against reality (commands in docs are executed in CI or by a script).
- **Visual polish:** consistent heading hierarchy and tables in docs, diagrams in Mermaid, optimised images with alt text, a clear repository description and topics, and a clean GitHub landing page.
- **Final repository audit:** before the last release, clone the repository fresh into an empty directory, follow the README exactly, run `make ci`, and record the result in `docs/TEST_REPORT.md`. Check that no ignored or sensitive file is tracked (`git ls-files` review, gitleaks over full history).

## 4. DESIGN SPECIFICATION (COMPLETE)

### 4.1 Intent and creative freedom

Zooffer must feel like a carefully designed consumer technology product: friendly, contemporary, confident, a little playful without being childish — never an "AI template", a generic SaaS dashboard or a conventional pet shop.

**This section defines a character and guiding principles, not a fixed layout.** The owner liked the general spirit of an earlier React concept (Princess Blue brand, light cool surfaces, composed animal cards, intuitive discovery) but does **not** want it reproduced pixel by pixel. You are free — and expected — to improve the palette, typography, layout, navigation, card composition, spacing, motion and visual language wherever that yields a stronger, more original product. Do not copy the old concept, the reference sites or Apple's interface. Do not drift away from the character below.

**Character to preserve**
- Princess Blue as the brand-colour direction (`#00539C`, initial digital approximation of PANTONE 19-4150 TCX);
- light, cool-neutral surfaces with white content areas;
- expressive typography with full Cyrillic support;
- attractive, natural-looking animal photography as the hero of every screen;
- a clean, friendly, contemporary interface; distinctive animal cards; an intuitive discovery experience; a memorable homepage;
- smooth, carefully executed motion;
- an Apple-inspired **Liquid Glass** layer used selectively (§4.5.2).

**Process requirement (Phase 4):** before building components, spend a short, time-boxed effort exploring 2–3 distinct design directions within this character (written descriptions plus quick rendered studies are enough), choose one, and record the rationale in `docs/DECISIONS.md`. Then build the chosen direction fully. Do not ask me to choose.

### 4.2 Colour tokens (CSS variables / Tailwind theme)

The values below are a **starting point**. Keep Princess Blue as the brand anchor, but refine the scale, neutrals and accents after real contrast and visual testing.

- `--brand-600: #00539C` — **Princess Blue**, initial digital approximation of PANTONE 19-4150 TCX. Primary buttons, links, active nav, wordmark.
- Derive a tonal scale from it: `--brand-50 #EAF3FB`, `--brand-100 #D3E6F7`, `--brand-200 #A8CDEE`, `--brand-400 #3C86C8`, `--brand-600 #00539C`, `--brand-700 #004280`, `--brand-900 #012A52`. Adjust values after contrast testing.
- Neutrals (cool): `--bg #F3F6FA` (page), `--surface #FFFFFF`, `--surface-2 #EAF0F6`, `--line #DCE4ED`, `--ink #0B1B2B`, `--ink-2 #44566A`, `--ink-3 #7A8CA0`.
- Semantic: `--like #FF5D73` (heart/like only), `--skip #5B6B7E`, `--success #1E9E6A`, `--warning #E8A317`, `--danger #D64545`, plus one restrained warm accent `--accent #FFB454` used sparingly (badges, highlights).
- Dark mode is optional; if implemented, it must be a deliberate palette, not inversion.
- All text/background pairs meet WCAG 2.2 AA (4.5:1 body, 3:1 large). Document contrast results.

### 4.3 Typography

- Full **Cyrillic** support is mandatory (check glyph coverage, including ё, №, ₽, «», —).
- **Headings:** a distinctive, expressive display face with Cyrillic (e.g. Unbounded, Geologica, Onest Display or comparable open-licence face). **Interface/body:** a highly legible face with tabular figures for prices (e.g. Onest, Golos Text, Inter with Cyrillic). Confirm licences (OFL or equivalent).
- **Self-host fonts** (no runtime Google Fonts request): faster in Russia, better privacy. Subset, `font-display: swap`, preload the critical weights, define metric-matched fallbacks to avoid layout shift.
- Scale (mobile → desktop): display 40→88 px, H2 28→48, H3 20→28, body 16 (never below 16 on inputs to avoid iOS zoom), small 13–14. Tight tracking on display, comfortable 1.5 line-height on body.
- Prices: `12 500 ₽` with narrow no-break space thousands separator, tabular numerals, never `RUB`/`руб.` inconsistently.

### 4.4 Wordmark

A recognisable **Zooffer** wordmark in the display face (custom-tuned letterspacing; optional subtle paw/heart/speech-bubble detail in the "oo" or terminal letter — restrained). Deliver SVG wordmark + monogram, favicon set, maskable app icons, OG image template.

### 4.5 Layout language

- 4 px spacing grid; content max-width ~1200 px with generous whitespace; radius system (12 px controls, 20–28 px cards, full pills for chips); soft cool shadows (low opacity, blue-tinted); 1 px `--line` borders on white surfaces.
- Cards are composed, not boxed: photo-led, strong name/age/city hierarchy, purpose chip, price or "Бесплатно", compact badges (Родословная, Привит, Проверено владельцем только если реально).
- Avoid visual repetition: vary card sizes in editorial grids, alternate image crops, use occasional full-bleed bands and large type moments.

### 4.5.1 Photography & imagery

Natural, well-lit animal photography with real crops (face-forward, eye level), consistent aspect ratios (4:5 cards, 1:1 animal thumbnails, 16:9 hero bands). Use only images you have the right to use (licensed/self-generated placeholders clearly marked for replacement, or user-uploaded in the product). **No stock claims, no fake testimonials, no invented statistics, no invented partner logos.** Provide tasteful empty/skeleton states.

### 4.5.2 Liquid Glass (explicit design direction: explore it, apply it selectively)

Explore a sophisticated, web-appropriate interpretation of Apple's Liquid Glass visual language and make it a recognisable but **original** part of Zooffer's identity.

**Where it belongs (functional layers that float above content):**
- the floating bottom tab bar on mobile and a compact floating/sticky header on desktop (pill shapes that can morph, expand into a sheet, or condense on scroll);
- the discovery action dock (skip / undo / like / favourite) and contextual toolbars that appear over cards or galleries;
- filter sheets, bottom sheets, popovers, menus, dialogs and toasts;
- small chips/labels placed over photographs (with a scrim so they stay legible);
- gallery controls, subtle overlay controls in the Mini App.

**Where it does not belong:** animal photographs themselves, descriptions and long text, forms and inputs, prices and numeric data, legal text, message bodies, tables, admin screens. Primary content stays opaque, stable and readable. Never stack glass on glass; never make every card glass.

**Techniques (progressive enhancement):**
- layered translucent materials using `backdrop-filter: blur() saturate()` with a brand-tinted fill (Princess Blue / cool white at low opacity), thin inner border highlights, soft specular edge gradients, restrained inner shadows, and gentle depth separation from content;
- optional refraction/lensing effect (e.g. SVG filter displacement) only where supported and performant, never required;
- fluid transitions between states (spring-based morphing of the tab pill, sheets rising from the dock), pointer/gyro-light highlights used sparingly;
- an original shape language derived from Zooffer's wordmark and cards — do not reuse Apple's icons, assets, SF fonts, naming or exact visuals.

**Accessibility and robustness (all mandatory):**
- text on glass must meet WCAG AA against the *worst-case* background beneath it; add scrims or raise opacity where needed; verify with real photos, bright and dark;
- provide solid, opaque fallbacks via `@supports not (backdrop-filter: blur(1px))`, `prefers-reduced-transparency`, `prefers-contrast: more`, forced-colors mode, and a runtime switch for low-end devices and Telegram WebViews where blur is slow;
- honour `prefers-reduced-motion` for all glass transitions;
- performance rules: at most a few blurred layers visible at once, capped blur radius on mobile, never animate blur radius itself, avoid `backdrop-filter` on large scrolling surfaces, test on a mid-range Android device; keep the §4.8 budgets;
- include a feature flag to disable glass globally if performance or contrast problems are found.

**Outcome:** the interface should feel layered, fluid and premium — glass improves depth and interaction — while photos, prices and text stay crisp. If the glass layer does not improve a given screen, leave it out.

### 4.6 References (creative inspiration only)

- https://mystaticself.com/ — study it in a real browser. Take inspiration from: app-like, text-led minimal navigation; panel/overlay transitions with clear back / previous / next / close controls; confident restraint; expressive typography, rhythm and movement; compact status microcopy. **Do not copy its layout, branding or assets.**
- If reference images or the earlier React concept are present in the workspace (`/refs`, `/design`, uploads), study them for the general feel the owner likes. They are inspiration, not specifications: do not copy complete layouts, proprietary assets or branding, and do not reproduce the old implementation. Where they differ from this document, this document governs; where you can do better, do better.

### 4.7 Homepage (required sections, in order)

1. **Hero:** memorable, typographic. Large Russian headline (e.g. «Найдите того самого — для себя или для питомца» — refine copy), supporting line, **primary CTA** «Начать подбор» (→ discovery) and **secondary CTA** «Разместить объявление». An interactive-looking **discovery preview**: a small stack of real featured animal cards the visitor can drag/flick (touch + mouse + keyboard), which really loads public featured listings from the API (no fake data in production; seed data only in dev/staging, labelled).
2. **Categories:** Продажа · Вязка · Племенная вязка · Пристройство (adoption + rehoming surfaced clearly) with distinct but cohesive treatments and counts only if real.
3. **Featured animals:** editorial grid with real listings, rotating/curated by an admin flag and quality score.
4. **How it works:** 3–4 concise steps (создайте анкету → листайте → совпадение/сообщение → договаривайтесь безопасно). Include a plain-language safety note.
5. **Partner offers:** visually integrated section (see §10), real offers only; hidden if none are active.
6. **Final CTA:** warm, short, with Telegram entry («Открыть в Telegram») and web registration.
7. **Footer:** discreet — secondary navigation, official Telegram links (bot, news channel, support), contacts, social links from config, legal documents (Политика конфиденциальности, Пользовательское соглашение, Согласие на обработку ПД, Правила размещения, Оферта/условия подписки, Реквизиты — only real ones).

### 4.8 Motion (mandatory, quality-bar)

Homepage animations are **required** and must be refined, not generic pulsing:

- Hero headline: staggered line/word reveals with masked slide-up and easing curves (cubic-bezier ≈ `0.22, 1, 0.36, 1`); weight/variable-font or underline emphasis on key words.
- Discovery preview: physics-feeling drag (spring), tilt/parallax on pointer, card stack that re-orders with overshoot-free springs; like/skip stamps that scale/rotate in.
- Scroll: section reveals via IntersectionObserver or scroll-driven animations; subtle parallax on large imagery; horizontal progress details; category cards with considered hover (image zoom + label shift); sticky header that compresses with scroll.
- Micro-interactions: pressed/hover/focus states on all controls, heart burst on like, animated counters only for real numbers, skeleton → content crossfades, route transitions that preserve context.
- **Controls:** respect `prefers-reduced-motion` (replace with opacity fades/static), pause offscreen animation, animate only `transform`/`opacity`, cap concurrent animations on mobile, no scroll-jacking that traps users, no layout shift. Budget: LCP ≤ 2.5 s and INP ≤ 200 ms on a mid-range Android over 4G; CLS ≤ 0.1; keep initial JS lean (code-split animation code).
- Explicitly **forbidden**: pulsing blurred blobs as the only animation, endless bouncing icons, parallax everywhere, random confetti, auto-playing audio/video with sound.

### 4.9 Explicitly prohibited "AI-template" patterns

Generic three-box feature grids; hero with floating gradient orbs; purple/blue-to-pink gradient backgrounds; excessive gradients; **indiscriminate glassmorphism** (frosted glass on every card/section, glass over body text, stacked glass) as opposed to the selective Liquid Glass of §4.5.2; identical repeated cards; meaningless stats («10 000+ счастливых питомцев»); fake reviews; random decorative emoji; stock-looking illustrations; "lorem ipsum" anywhere; a generic SaaS-dashboard or pet-shop look.

### 4.10 Responsive and mobile-first

- Design mobile first (320–430 px), then tablet (768–1024), desktop (1280+), wide (1536+). Test on narrow 320 px, common iPhone/Android sizes, iPad, desktop.
- Mobile: bottom tab bar (Подбор, Поиск, Избранное, Сообщения, Профиль), safe-area insets (`env(safe-area-inset-*)`), thumb-reachable actions, dynamic viewport units (`dvh`), no horizontal overflow, 44×44 px minimum targets, sticky action bars that respect the on-screen keyboard, bottom-sheet dialogs, pull-friendly lists, image galleries with swipe + pinch-zoom + lightbox, keyboard-aware forms with correct `inputmode`/`autocomplete`.
- Desktop: top navigation, two-column discovery (card + details), keyboard shortcuts for swiping (←/→/↑ and Z for undo) with visible hints and accessible alternatives.
- Dialogs: focus trap, ESC to close, scroll-lock, return focus.
- Accessibility: semantic HTML, WCAG 2.2 AA, visible focus rings, full keyboard operation, ARIA only where needed, alt text for animals, forms with associated labels and error summaries.

### 4.11 Page and workflow inventory (all required)

Public: Homepage; Discovery (guest sees a limited preview then is invited to register); Search + advanced filters; Category/landing pages (by purpose, species, breed, city); Animal profile / public listing; Partners page; Partner inquiry; Support/FAQ; Legal documents; 404/500/maintenance.

Auth & onboarding: Registration; Login; Telegram login; Account recovery; Onboarding (city, interests, notification prefs, first animal prompt, consent capture); Account linking (web ↔ Telegram).

Account area: Personal account/profile (public name = first name + optional surname only, city, private contact preferences; **no personal profile photo is shown to other users**; the owner's own private data is visible only to the owner); My animals (create/edit/archive/delete, photo management, documents); My listings (create/edit/publish/pause/renew/archive, status + moderation state); Favorites; Matches; Conversations; Subscription management (plan, entitlements, renewal, cancel, payment history); Partner offers (available to me, redeemed); Notifications centre; Settings & privacy (notification channels, blocked users, read-receipt preference, what is public vs private, data export, account deletion); Reporting dialogs.

Staff: Moderation queue; Reports; Users; Listings; Subscriptions/transactions; Partners/offers/banners; Content/pages; Audit log; System settings (free swipe limit N, plans, feature flags) — all behind RBAC + admin MFA.

Every page needs: loading, empty, error and offline states in Russian.

### 4.11.1 Listing creation wizard

Steps: purpose → species/breed/sex/age/colour/size → health & vaccination (declared) → pedigree (optional attribute) → photos (≥1, ≤10, drag-reorder, primary photo) → price/terms (₽ where relevant, negotiable flag) → location (city/region with Russian geo-data, no exact address) → description (character limits) → preview → publish (or submit for moderation). Autosave drafts server-side. Edit and re-moderation rules defined. Same wizard logic available in the bot (compact FSM) and Mini App.

---

## 5. DATA MODEL (minimum; refine as needed, with Alembic migrations)

Use UUID/ULID primary keys, `created_at/updated_at`, soft-delete where appropriate, explicit constraints and indexes.

- `users` (canonical internal ID; status; role; locale; timezone; consent versions), `auth_identities` (provider: `telegram` | `password` | …; provider_user_id = **Telegram numeric user ID**, never username; unique per provider), `credentials` (argon2id hash), `sessions` (hashed token, device, IP hash, expiry, revoked), `account_link_tokens` (single-use, hashed, expiry), `mfa_factors`, `consents` (document, version, timestamp, channel, IP hash).
- `profiles` (**public fields only**: `public_first_name`, optional `public_last_name`, city/region id) plus a **separate** `user_private_data` table (phone, email, date of birth, address, precise geo, Telegram username — encrypted where appropriate, never joined into public queries), public opaque IDs (`public_id`/slug) distinct from internal primary keys, `animals` (species, breed, sex, birth_date, colour, has_pedigree, registry, number, health flags, owner_id), `animal_photos`, `animal_documents` (private storage), `listings` (purpose, price_kopecks, currency=`RUB`, status machine `draft → pending_moderation → published → paused/expired/sold/archived/rejected`, slug, city_id, published_at, expires_at), `cities`/`regions`, `breeds` (curated dictionary).
- `swipes` (user_id, listing_id/animal_id, action `like|skip`, source, created_at; **unique (user, target)**), `favorites`, `matches` (animal_a, animal_b, owners, created_at; canonical ordered pair unique), `blocks`.
- `conversations` (type `match|inquiry`, participants, listing context), `messages` (sender, body, attachments, read_at, deleted flags), `message_reports`.
- `daily_quota_usage` (user_id, quota_date in Europe/Moscow, used_count) with atomic increment; `quota_events` (audit).
- `plans`, `subscriptions` (state machine: `pending → active → past_due → canceled → expired`), `entitlements` (derived, e.g. `unlimited_swipes`, `undo`, `boost`, `see_who_liked`, with source), `payment_orders`, `payment_events` (raw provider payload + signature result + **unique provider_event_id** for idempotency), `refunds`.
- `partners`, `partner_offers` (terms, code, starts/ends, destination URL, status), `partner_banners` (approved creative, sizes, alt text, ERID/ad-marking fields if applicable), `partner_clicks`, `partner_conversions`, `partner_inquiries`.
- `notifications` (type, channels, delivery state), `notification_preferences`, `bot_updates_seen` (update_id dedupe), `telegram_chats`.
- `reports`, `moderation_actions`, `audit_log` (append-only; actor, action, object, before/after hash).
- `referrals`, `campaign_attributions`, `analytics_events` (minimised, no raw PII).

---

## 6. CORE FEATURE REQUIREMENTS (all must really work)

### 6.1 Discovery, search, filters

- Server-side ranking and **keyset pagination**; no duplicate cards in a session; never show the user's own animals, blocked users, already-swiped targets (unless a configured recycle rule), unpublished/moderated-out items.
- Filters: purpose, species, breed, sex, age range, size, colour, city/region and radius (if geo available), price range (₽), pedigree (yes/no/any), vaccinated, delivery/transport willingness, with/without photos, newly published, partner-verified flags if real. Full-text search (Postgres FTS with Russian config, or a justified engine) with typo tolerance considered. Filters are shareable via URL and persist per user.
- Sort: relevance, newest, price asc/desc, distance (if implemented; distance expressed in coarse bands computed from city-level coordinates, never from precise locations).
- Every card, search result and listing page renders the owner only through the public owner view of §6A (first name + optional surname, or «Владелец»).

### 6.2 Swipes, undo, favorites

- Like/skip are server-recorded, idempotent, and enforce the daily quota **in the same transaction** as the swipe write (§7). Gestures: drag, buttons, keyboard.
- **Undo** (premium entitlement, configurable): reverts the last swipe, restores the quota unit per config, and is impossible if a match/message already resulted from it (document the rule).
- Favorites are independent of likes, unlimited (or configurable cap), listed with status changes (sold/paused shown clearly).

### 6.3 Matching and messaging

- Implement §1.2 exactly. Property tests: no match without reciprocal likes; no duplicate match under concurrency; no match across incompatible species/sex rules; blocked users never match.
- Messaging: persistent, ordered, paginated, read receipts (user-controllable, off-able), **no typing indicator and no online/last-seen status**, attachments (images only, same upload pipeline), per-conversation mute/block/report, anti-spam limits (new-account throttle, repeated-link/phone-number heuristics, per-minute and per-day caps), message deletion rules, retention policy. Contact details are never disclosed automatically; users may voluntarily share them only through the explicit action defined in §6A.4.
- Notifications for new match, new message, inquiry, listing status change, subscription events — delivered per user preference to web (in-app + optional email/Web Push), and Telegram. De-duplicate and batch to avoid spam.

### 6.4 Accounts and animals

Full CRUD with ownership enforcement, draft/publish states, photo reordering, document upload, listing renewal/expiry reminders, archive/restore, data export, and **account deletion** (with defined retention for legal/financial records).

### 6.5 Moderation and reporting

User reports for listings, animals, messages and users with reason taxonomy; moderation queue with SLAs; automated pre-checks (banned words, duplicate images via perceptual hash, suspicious pricing, contact-info-in-description heuristics, prohibited species/purposes list from compliance work); actions: approve/reject with reason, request changes, shadow-limit, suspend, ban; user-facing appeal path; full audit log.

### 6.6 Support

Support entry points on web, in the bot and in the Mini App; tickets stored in DB (or routed to a configured support Telegram chat/email) with status tracking; FAQ content managed by admins.

---

## 6A. PRIVACY MODEL (STRICT, ENFORCED TECHNICALLY)

### 6A.1 The rule

**Other users may see only the owner's first name and, if supplied, surname as personal identity information.** This applies identically on the website, public listings, search results, discovery cards, matches, conversations, notifications, the Telegram bot and the Telegram Mini App. If no name is available, show the neutral label «Владелец».

**Never expose to other users (in any channel, format or embedded payload):** phone numbers; email addresses; Telegram usernames or IDs; internal account IDs; personal profile photographs; dates of birth; exact addresses or precise coordinates; last-seen/online information; private activity history; private account statistics (swipe counts, quota, subscription status, payment data, notification settings); any other personal or account attribute.

**May be shown** (information the owner intentionally publishes about the animal/listing): animal photographs, species, breed, sex, age, colour, listing purpose, price in ₽, pedigree status/badge, health declarations, description, and city/region-level location — provided none of it leaks owner-private data (see 6A.3).

Public-facing restrictions are distinct from what the backend legitimately processes for authentication, billing, security, support and legal compliance: that data lives in private tables, is minimised, access-controlled, audited, and never reaches public response schemas.

### 6A.2 Display name handling

- The public name is chosen by the user in onboarding (`first name` required for publishing, `surname` optional). Prefilling from Telegram's `first_name` is allowed only with the user's explicit confirmation; a Telegram username is never prefilled or shown.
- Validate names: length limits, letters/spaces/hyphens/apostrophes only; reject digits, `@`, URLs, emails, phone-like strings and emoji strings used to smuggle contacts. Name changes are rate-limited and moderated if flagged.
- Public API responses contain a derived `owner_display_name` (or null → client shows «Владелец»), never the full profile object.

### 6A.3 Content hygiene

- Listing text, animal names and titles are checked server-side for phone numbers, emails, messenger handles and links; matches are blocked or sent to moderation (with clear Russian guidance to use the in-app conversation).
- Uploaded images have EXIF/GPS stripped; moderation includes a heuristic/manual check for contact details or personal photos visible inside listing images. Private documents (e.g. pedigree papers, which may carry owner names/addresses) are private by default and only released to a specific counterparty with the owner's explicit approval via short-lived signed URLs, with a warning to redact personal data.
- Location is stored and shown at city/region level only; precise coordinates are never persisted for public objects.
- Referral/inviter relationships, likes received, and activity are not attributable to a named person in any public view; features like «кто меня лайкнул» show only the animal and the owner's public name per 6A.1, and only to entitled users.

### 6A.4 Voluntary contact exchange

Contacts are shared only inside a conversation by an explicit user action («Поделиться контактами») with a confirmation dialog stating what will be revealed and to whom, per contact field, revocable for future messages. Nothing is shared by a like, match, inquiry, profile view, deep link or bot command. Free-text contact sharing in chat is permitted only as the user's own typed message and remains subject to anti-spam/anti-abuse rules.

### 6A.5 Technical enforcement (a hidden frontend field is not sufficient)

- **Deny-by-default serialisation:** public endpoints return explicit Pydantic response schemas with field allowlists (`PublicOwnerView`, `PublicAnimalView`, `PublicListingView`, `ConversationParticipantView`). ORM objects are never serialised directly. A CI test fails if a public schema gains a field not on the reviewed allowlist.
- **Data separation:** private data in separate tables/columns (optionally separate DB role/view for public reads) so that a careless join cannot leak it; public read paths use views/queries that never select private columns.
- **Opaque public identifiers** for listings, animals and owners; no sequential or internal IDs, Telegram IDs or usernames in URLs, API payloads, deep links, callback data or analytics.
- **All channels use the same public views**: website API, server-rendered HTML, Next.js embedded data (`__NEXT_DATA__`/RSC payloads — pass only DTOs to client components), JSON-LD, Open Graph tags, sitemaps, search index documents, Mini App API, bot messages/inline results/callback data, notification texts (emails, push, Telegram), error messages and logs.
- Search indexing (Postgres FTS or other engine) must not index private fields.
- Staff access to private data is role-limited, purpose-bound, minimal in support tooling, and audit-logged.
- Retention and deletion: documented retention schedule; self-service data export and account deletion; on deletion public listings and profile are removed and private data erased or anonymised except records legally required to be kept (documented); in surviving conversations the departed party appears as «Удалённый пользователь».
- Logging and analytics are PII-minimised (no names, contacts, usernames, free-text message bodies; hashed/truncated IPs).

### 6A.6 Required privacy tests (automated, run in CI)

- **Canary-based leak tests:** create users whose private fields (phone, email, birth date, address, Telegram username/ID, internal ID) contain unique sentinel strings. Then, as a different user *and* as an anonymous visitor, exercise every public path — REST/JSON API, server-rendered pages, embedded frontend data, JSON-LD/OG metadata, sitemaps, search results, Mini App API, simulated Telegram bot updates and outgoing bot/notification messages, WebSocket/SSE streams, error responses — and assert no sentinel ever appears. Include crawl-style tests that follow links from public pages.
- Contract tests asserting the exact key set of every public schema.
- Tests proving a like, match, inquiry, profile view or deep link never reveals contacts, and that contact sharing works only via the explicit action.
- Tests that EXIF/GPS is stripped from uploads and that private documents are inaccessible without authorisation and signed URL.
- Tests that account deletion and data export behave as specified.
- Verify the privacy model in the final report with evidence (test names and output).

---

## 7. DAILY SWIPE QUOTA (SERVER-ENFORCED)

- Configurable free limit **N** (admin setting + env default; N = 0 allowed; N = unlimited allowed for entitlement holders).
- **Quota-consuming actions** (default; configurable): each `like` and each `skip` of a *new* target consumes 1. Re-viewing, favoriting, searching, opening profiles and sending messages do not. Undo restores 1 if the undone swipe consumed it.
- **Reset rule:** at 00:00 in `Europe/Moscow` (store `quota_date` as that local date). Document and display the next reset time.
- **Atomicity:** `UPDATE … SET used_count = used_count + 1 WHERE user_id=:u AND quota_date=:d AND used_count < :limit RETURNING …` (or equivalent with row lock) in the same transaction as the swipe insert; swipe uniqueness prevents double-spend; retries are idempotent via a client-supplied swipe request ID.
- The quota is attached to the **canonical user**, so refreshing, clearing local storage, switching devices or moving to Telegram cannot bypass it. The client only displays remaining count returned by the server.
- When the limit is reached: clear Russian message, time-to-reset, and subscription upsell (without dark patterns).
- Tests: concurrency test (many parallel swipes never exceed N), timezone boundary test, cross-channel test (web + bot + Mini App share one counter), entitlement-change test.

---

## 8. TELEGRAM ECOSYSTEM (ONE PRODUCT, THREE INTERFACES)

### 8.1 Identity and linking

- One canonical `users.id`. Telegram identity = numeric Telegram user ID in `auth_identities`. **Usernames are display data only, never identity keys.**
- Registration via Telegram creates a user; later the same user can log into the website via Telegram Login (validated server-side) or by adding email/password and linking.
- Website-first users link Telegram through an explicit, protected flow: authenticated web session requests a **one-time, short-lived, single-use link token** → opens `t.me/<bot>?start=link_<token>` → bot confirms with an inline "Подтвердить привязку" button → backend atomically binds the Telegram ID. Reject if that Telegram ID already belongs to another account; offer an explicit, audited **account merge** flow requiring proof of both accounts (never silent). Prevent duplicate accounts.
- Login/session security rules in §9.1 apply to all three channels.

### 8.2 Authentication data validation (server-side only)

- **Mini App:** validate `initData` per current Telegram docs (HMAC-SHA256 with the key derived from the bot token, or the documented Ed25519 third-party method), compare constant-time, enforce `auth_date` freshness (short window) and replay protection, then mint a normal Zooffer session. Never trust `initDataUnsafe`.
- **Telegram Login (website):** validate the signed payload/token per current docs, enforce freshness.
- **Webhook:** configure a secret token and verify the `X-Telegram-Bot-Api-Secret-Token` header on every request; additionally restrict ingress as justified; deduplicate by `update_id`; respond quickly (offload slow work to the queue); handle Telegram retries idempotently.
- The bot token lives only in the server secret store — never in the website, Mini App bundle, logs or error messages. Never build user-facing URLs that contain it (e.g. file download URLs): proxy/download files server-side and serve through your own authorised storage.

### 8.3 Bot — fully implemented, not a launcher

Commands and flows (all Russian, all using the shared service layer):

- `/start` (with deep-link payloads: `link_*`, `ref_*`, `listing_*`, `utm_*`): onboarding, consent capture (explicit button, versioned, stored), account creation/lookup, welcome, main menu.
- `/menu`, `/help`, `/cancel`, `/settings`, `/profile`, `/mylistings`, `/addpet` (compact listing wizard with FSM: validation per step, back/cancel, photo upload with limits, resumable via Redis + DB draft), `/swipe` (inline-keyboard discovery with the same server-side quota), `/favorites`, `/chats`, `/subscription`, `/buy`, `/paysupport`, `/support`, `/news` (link to channel), `/link`, `/language` (ru default), `/stop` for notifications.
- Persistent main menu button opening the **Mini App** (`web_app` button) plus inline entry points to deep-link into specific listings/chats.
- **Notifications** (respecting user preferences and quiet hours): listing moderation result and status changes, new match, new message/inquiry, subscription activated/expiring/failed, quota reset reminders (opt-in), partner offers (opt-in only).
- **Reliability:** FSM state with TTL in Redis; callback-data schema with versioning and signature/ownership checks; idempotent handlers; per-user and global rate limits and Telegram flood-control handling (respect `retry_after`, queue with backoff); graceful handling of blocked bot (`Forbidden`), deleted chats, invalid input; user-friendly recovery messages («Что-то пошло не так. Попробуйте ещё раз или откройте меню»).
- **Privacy in Telegram:** bot messages, inline results, notifications and callback data use the same public views as the website (§6A): never show another user's Telegram username/ID, phone or profile photo; deep-link payloads are opaque single-use or public IDs; the bot does not ask users to share their Telegram contact/phone unless a documented, consented purpose requires it, and any such value is stored as private data only.
- **Payments in bot:** see §9.
- **Authorization:** every command/callback resolves the Telegram ID → canonical user and checks permissions server-side; admin commands (if any) require RBAC + MFA-grade confirmation and are not enabled by hard-coded IDs.

### 8.4 Mini App — fully implemented

Real interactive app, not a prototype, under `/tg/*` in the same Next.js codebase with shared API and design system:

- Auth via validated `initData` → Zooffer session; seamless account continuity with the website.
- Screens: Discovery (swipes with quota), Search + filters, Animal/listing profile, Favorites, Matches, Conversations, Listing create/manage (same wizard), Profile, Subscription (Stars purchase flow + status), Partner offers, Settings, Support.
- Telegram integration: initialise the WebApp SDK (`ready()`, `expand()`), use theme parameters only to harmonise (brand stays Princess Blue), `MainButton`/`BackButton`/`SecondaryButton` and haptic feedback where supported, `safeAreaInset`/`contentSafeAreaInset` and viewport-change handling, fullscreen/ closing confirmation when a draft is in progress, `openInvoice` for Stars, `openTelegramLink`/`shareToStory` or share via inline for sharing listings. Feature-detect by version; degrade gracefully.
- Performance on mid-range phones: small bundles, image sizes by viewport, virtualised long lists.
- **Privacy:** Telegram user data from `initData` (name, username, photo) is used only to authenticate and, with confirmation, prefill the user's own public name; it is never exposed to other users. Do not call contact-request APIs unless a consented purpose exists.
- **No separate business logic or accounts**; the Mini App is a client of the same API.

### 8.5 Production operation of the bot

Webhook behind HTTPS on the production domain; `setWebhook` performed by a deploy script with `allowed_updates` minimised and the secret token; health check endpoints; process supervision via containers (`restart: unless-stopped`) or systemd; structured logs; alerting on webhook errors/backlog (`getWebhookInfo`); the bot must run with **no developer terminal open**. Document BotFather configuration (commands list, menu button, Mini App short name, domain registration, privacy mode, payments).

---

## 9. SUBSCRIPTIONS AND PAYMENTS

### 9.1 Plans and entitlements

Configurable plans in DB (names, price, period, entitlements). Suggested starting set (editable by admin, not hard-coded): Free (N swipes/day) and one or more paid plans granting: higher/unlimited daily swipes, undo, "кто меня лайкнул" (shows only the animal and the owner's public name per §6A), profile boost, extended photo count, priority in moderation, ad-free partner section. Do not invent final prices as facts — seed placeholder prices clearly marked "configure before launch".

Entitlements are **derived server-side** from subscription state and checked by the backend on every gated action. The client never decides.

### 9.2 Providers

- **Website (₽):** integrate a Russian-ruble provider supported for the actual business form (YooKassa as the default implementation behind a `PaymentProvider` interface; others pluggable). Verify current YooKassa API, recurring-payment/auto-renewal requirements, receipt (54-ФЗ / online-cashier fiscalisation) requirements and webhook signing/IP rules before implementing. Use sandbox/test shop credentials for tests.
- **Inside Telegram (digital subscription):** follow **current official Telegram Stars requirements** for digital goods/services sold in bots and Mini Apps (invoices in currency `XTR`, `pre_checkout_query` answered within the documented window, `successful_payment` handling, subscription invoice links where used, refunds via the official method). Verify the current rules (including Telegram's policy on external payment links for digital goods) before implementing and document the findings and date in `docs/PAYMENTS.md`.
- Verify in `docs/COMPLIANCE.md` whether the purchase of a Zooffer subscription via different channels needs consistent pricing/terms, and display terms, auto-renewal conditions, cancellation path and refund policy **before** payment.

### 9.3 Required payment engineering

- State machine for orders and subscriptions; orders created server-side with server-computed price (never client-provided).
- **Entitlement activates only after server-side verified provider confirmation** (provider API re-fetch and/or verified signed webhook/`successful_payment`), never because the browser hit a success URL or a button was clicked.
- Webhook endpoints: authenticity validation (signature/IP/secret per provider docs), replay protection, **idempotency** via unique `provider_event_id`, processing in a DB transaction, safe retries, dead-letter handling and alerting.
- Handle: successful payment, pending/waiting, cancellation, failure, expiry, renewal, grace period, `past_due`, refund, chargeback; proration/upgrade rules defined and tested.
- Never store card data; use provider-hosted payment forms/tokens only.
- Admin: view orders, events, refund/revoke entitlement, manual grant (audited), reconcile report.
- If production credentials are unavailable: implement against sandbox/fakes, mark `BLOCKED` with the exact missing keys, and **do not claim payments are operational**.

---

## 10. PARTNER PROGRAM

- Entities per §5. Admin UI to create partners, upload **approved** banners (size/format validation, alt text, ad-marking fields), define offers (description, discount code, start/end, destination URL, terms, audience), pause/expire offers.
- Public surfaces: integrated homepage section (hidden when empty), dedicated `/partners` page with filters (категория: корм, магазины, ветеринария, груминг, услуги), per-offer detail with terms and expiry.
- **Tracking:** server-side redirect endpoint (`/go/{offer_id}`) records a click (hashed IP/UA, no PII), sets a first-party attribution token; conversion attribution only where a partner provides a verifiable callback/promo-code redemption — otherwise report clicks only. Fraud/duplicate-click protection.
- **Partner inquiry flow:** form (company, contact, category, message) with validation, spam protection, consent, storage and notification to admins.
- Config-driven official links: Telegram bot, news channel, support, social networks.
- **No invented partners, discounts or promotional claims.** Ship with zero partners and a polished empty state plus seed data only in dev/staging, clearly marked.
- Mark advertising according to current Russian advertising law and platform requirements (verify; see §12).

---

## 11. SEO AND GROWTH (RUSSIA-FOCUSED)

- Server-rendered public pages with unique Russian `<title>` and meta descriptions, canonical URLs, `hreflang` only if multiple locales exist, Open Graph/Twitter cards, clean URL slugs (transliterated or Cyrillic-safe), breadcrumbs, internal linking between categories/breeds/cities.
- XML sitemaps (split & paginated, `lastmod` accurate, only indexable URLs), correct `robots.txt` (disallow private areas, search-result parameter explosion, admin, chats, account, API), `noindex` for thin/duplicate pages (empty filters, deep pagination, drafts, archived items), canonical rules for filtered views, 301s for slug changes, 404/410 for removed items.
- Indexable: homepage, category/purpose/species/breed/city landing pages with real unique content and listings, individual public listings (while active; sensible handling when sold/expired). **Not indexable:** accounts, chats, admin, drafts, checkout, partner click redirects.
- Structured data **only where truthful**: `Organization`, `WebSite` + `SearchAction`, `BreadcrumbList`, `Product/Offer` for sale listings (price in RUB, availability), `FAQPage` only for real FAQ. No fake ratings/reviews.
- Yandex-specific: Webmaster-ready verification meta slot via config, fast server-rendered HTML, `Yandex Turbo` not required. Yandex Metrica **optional and consent-gated**; prefer privacy-conscious analytics (self-hosted Plausible/Umami or first-party events) and document the legal basis.
- Growth: referral links (`ref` codes, attribution to inviter, anti-abuse), UTM/campaign capture stored in `campaign_attributions`, shareable listing pages with proper OG image generation, share buttons (Telegram, VK, copy link), deep links into the Mini App.
- Server-rendered HTML, structured data, Open Graph tags and sitemaps must follow §6A: no owner private data; a seller may appear as a `Person` only with the public name, or be omitted.
- Do not promise rankings; do not fabricate traffic or conversion numbers.
- Core Web Vitals budgets from §4.8 apply to indexable pages. Include Lighthouse CI or equivalent.

---

## 12. SECURITY (CORE ENGINEERING REQUIREMENT)

Do **not** claim the application is "unhackable" or "fully secure". The objective is a **defensible, testable posture** that reduces risk, blocks common attacks, limits blast radius and detects failures. Produce `docs/THREAT_MODEL.md` (assets, actors, trust boundaries, STRIDE-style threats, mitigations) **before** Phase 2 and update it each phase. Use current OWASP guidance — ASVS (target Level 2), API Security Top 10, Cheat Sheet Series — and cite the versions used.

### 12.1 Authentication and account security
- Server-side sessions or short-lived access tokens + rotating refresh tokens, stored hashed; cookies `HttpOnly`, `Secure`, `SameSite=Lax/Strict`, `__Host-` prefix where possible; session rotation on login/privilege change (prevents fixation); idle and absolute timeouts; device/session list with revoke; logout everywhere.
- If passwords exist: **argon2id** with tuned parameters, breached-password check (k-anonymity), min-length policy, no composition theatre; email verification; safe, rate-limited, enumeration-resistant recovery with single-use expiring tokens.
- Brute-force/credential-stuffing defences: per-account, per-IP and global throttling, progressive delays, optional CAPTCHA/proof-of-work on anomalies (privacy-conscious, Russia-available provider), alerting.
- CSRF protection on all cookie-authenticated state-changing requests (SameSite + token/double-submit or Origin checks).
- **Admins and moderators: mandatory MFA** (TOTP and/or WebAuthn), short sessions, re-auth for sensitive actions, IP/anomaly alerts.
- **No default, shared or hard-coded production credentials or admin IDs.** First admin is created via an explicit one-time CLI bootstrap, not config defaults.

### 12.2 Authorization and isolation
- Deny-by-default RBAC (`user`, `moderator`, `admin`, `superadmin`), least privilege, centralised policy layer (not scattered `if` checks), every endpoint declares its required permission.
- **Ownership/object-level checks** for animals, listings, drafts, conversations/messages, documents, subscriptions, payment records, notification settings.
- IDOR/BOLA and privilege-escalation tests for every resource type and every channel (web API, bot callbacks, Mini App). Prefer unguessable IDs but never rely on them.
- Frontend hiding of controls is never a security boundary. Admin APIs live under a separate router with separate auth requirements and are not exposed on public Mini App routes.

### 12.3 API and application security
- Strict Pydantic validation (types, lengths, enums, ranges, unknown fields rejected), allow-lists for sort/filter keys; safe output encoding; React escaping + no `dangerouslySetInnerHTML` without sanitiser; Markdown/rich text sanitised server-side.
- **Specific protections, each with its own automated tests:** SQL injection (parameterised queries/ORM only, no string-built SQL, allow-listed sort/filter identifiers); stored, reflected and DOM-based XSS (contextual output encoding, no `dangerouslySetInnerHTML` without a server-side sanitiser, safe Markdown/HTML rendering with a strict allow-list, CSP); CSRF; **SSRF** (no user-controlled server-side fetches; if unavoidable, allow-list + egress controls + DNS-rebinding and redirect protection); command injection (no shell execution with user data, use argument arrays, avoid `eval`/`exec`); **template injection** (never render user input as a template; auto-escaping on); path traversal (generated file names, no user-supplied paths); unsafe/open redirects (partner redirect resolves offer IDs, never raw URLs; allow-list return URLs); HTTP **header injection** / CRLF (reject control characters in anything placed in headers); unsafe deserialisation (no pickle/YAML-load of untrusted data); **mass assignment** (explicit input schemas per operation, never bind request bodies to models); authentication and authorisation bypass; race conditions in matching, quotas and payment processing; malicious uploads; abuse of search (query-complexity/length limits, ReDoS-safe patterns), messaging, registration and public APIs.
- Do not execute user-supplied code, shell commands, SQL fragments or templates anywhere.
- CORS strict allow-list; HTTP security headers (HSTS, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`, frame protections allowing only Telegram WebView where required), **CSP** with nonces and no `unsafe-inline` for scripts (document the Telegram WebApp script requirement), SRI for any third-party script.
- Rate limits per IP/user/endpoint class (auth, swipes, messaging, uploads, search, reports, partner inquiry); request body/size limits; timeouts; connection limits; abuse/spam/scraping controls (honeypots, behavioural limits, bot detection on public listings API, pagination caps).
- Error handling returns generic messages with correlation IDs; no stack traces/secrets/internal paths to clients.

### 12.4 Database and data protection
- DB **and Redis** reachable only from app services on a private network (Redis with authentication/ACLs and TLS where it crosses hosts); no public ports, no admin tools exposed (pgAdmin etc. only via SSH tunnel/VPN if at all); least-privilege DB roles (migration role ≠ runtime role ≠ read-only reporting role); secure migrations reviewed and reversible where possible.
- Integrity: constraints, FKs, unique indexes, transactions with correct isolation for matching, quotas and payments; row-level locks or serialisable retries where needed; tests for races.
- TLS in transit everywhere (including DB/Redis if crossing hosts); encryption at rest (disk/volume or managed) per deployment, application-level encryption for especially sensitive fields (e.g. phone/email if stored, tokens) with key rotation plan.
- Data minimisation and retention schedule (messages, logs, deleted accounts, payment records), PII-safe logging (mask/hash), PII-free analytics, **backups encrypted, off-site (within Russia if required), with restore drills documented and executed**.

### 12.5 Files and media
- Allow-list MIME **by content sniffing**, not extension; max size/dimensions/count; reject polyglots; re-encode all images (strips EXIF/GPS and embedded payloads); random server-generated file names; store outside the web root/in object storage on a **separate domain/origin** (cookieless) with `Content-Disposition`/`nosniff`; private documents (pedigree papers) served via short-lived signed URLs after authorisation checks; no server-side fetching of remote media URLs by default; malware scanning (ClamAV or equivalent) for documents and images where justified, with quarantine; upload quotas per user; orphan cleanup job.
- Uploads must never be executable or interpretable by the application server.

### 12.6 Telegram security
Covered in §8.2 plus: idempotent update processing, per-user rate limiting, signed/ownership-checked callback data, no trust in forwarded/inline-supplied IDs, secrets in secret store, `getWebhookInfo` monitoring, and no sensitive data in deep-link payloads (use opaque single-use tokens).

### 12.7 Payment security
Covered in §9.3 plus: server-computed prices only, provider-authenticity checks, replay protection, transactional entitlement updates, reconciliation job, anomaly alerts (many failures, refund spikes), no card data stored.

### 12.8 Secrets, deployment and operations
- No secrets in git or client bundles; `.env.example` with placeholders only; `.gitignore` enforced; pre-commit + CI secret scanning; separate dev/staging/prod configuration; production secrets from a secrets manager or encrypted, access-controlled files with rotation procedure; startup **fails fast** if required prod secrets are missing/weak.
- HTTPS only (TLS 1.2+, modern ciphers, HSTS), automatic certificate renewal; non-root containers, read-only filesystems where possible, dropped capabilities, minimal base images, pinned digests, no privileged mode; only 80/443 (and SSH restricted by key + allow-list) exposed; firewall rules documented; server hardening checklist (unattended security updates, fail2ban or equivalent, no password SSH).
- A documented **incident-response plan** and **secret-rotation procedure** (rehearsed at least once in staging and recorded in `docs/RUNBOOK.md`); dependency update process (Dependabot/Renovate), vulnerability SLAs; centralised security logging (auth events, permission denials, rate-limit hits, payment anomalies, admin actions); alerting on anomalies; tested backup/restore.

### 12.9 Secure development and testing
- Threat modelling (above); security-focused review checklist per PR; SAST (bandit/semgrep), dependency scanning, secret scanning, container scanning; OWASP ZAP baseline/API scan **against local/staging only — never production, never destructive**; fuzz/property tests on parsers (initData, webhook payloads, upload handling).
- Automated tests for: authentication flows, session lifecycle, the authorisation matrix (every role × every resource), **IDOR/BOLA and privilege escalation**, rate limits/abuse, payment verification and idempotency/replay, input validation, quota non-bypass (including concurrency), CSRF, upload attacks (polyglots, oversized, wrong MIME, SVG/script payloads), webhook forgery, Telegram `initData` forgery/stale/replayed data, unauthorised administrative access, **injection corpora** (SQLi, XSS in every stored field and every rendering channel, SSTI, header/CRLF injection, path traversal, SSRF probes, open redirects, mass assignment), and the **privacy leak suite** of §6A.6.
- Review scanner findings: fix or document each with severity and a risk-based plan; do not merely install tools. Keep `docs/SECURITY_REPORT.md` listing tools run, versions, findings, remediation, residual risk. Distinguish verified results from assumptions.

### 12.10 Security acceptance criteria (must be evidenced)
1. Every sensitive endpoint enforces authorization (automated matrix test passes).
2. Ordinary users cannot reach moderation/admin; admins require MFA.
3. Accounts and private data are isolated (IDOR suite passes).
4. Telegram/Mini App auth data is validated server-side; forged/stale data is rejected (tests).
5. Subscription limits and entitlements cannot be bypassed by client manipulation.
6. Payment success cannot be forged from the frontend; forged/replayed webhooks are rejected and idempotent.
7. No secrets in source control history or client bundles (gitleaks + bundle scan).
8. Uploads cannot execute code; malicious-file tests pass.
9. Rate limits and abuse controls demonstrably trigger.
10. Injection and unauthorised-access test suites pass (SQLi, XSS, SSTI, SSRF, path traversal, header injection, open redirect, mass assignment, IDOR/BOLA, admin access).
11. The privacy leak suite (§6A.6) passes across API, server-rendered HTML, embedded frontend data, metadata, sitemaps, Telegram/Mini App channels and notifications: no other-user private data (only first name + optional surname) is ever exposed.
12. Security and privacy tests ran, and their results are documented in `docs/SECURITY_REPORT.md`; Critical/High findings are resolved, or explicitly documented with a risk-based plan, **before** any production-readiness claim. Never describe the platform as fully secure or unhackable.

---

## 13. RUSSIAN LEGAL AND REGULATORY REQUIREMENTS

You are not a lawyer; the output must say so. Before implementing, **research current primary sources** (official legal portals, Roskomnadzor, ФНС, Минцифры, Telegram/YooKassa official docs) and record sources + date in `docs/COMPLIANCE.md`. Determine which obligations actually apply to the real business model (operator form — ИП/ООО/самозанятый — is unknown; do not assume). Cover at least:

- **Personal data (152-ФЗ and related):** operator duties, lawful bases, **separate, explicit consent** in the form currently required, privacy policy publication, localisation of Russian citizens' personal-data databases on servers in the Russian Federation (affects hosting, backups, analytics, error tracking, email/SMS providers, CDN), Roskomnadzor notification, cross-border transfer rules, data-subject requests (access, correction, deletion, withdrawal of consent), breach notification, retention.
- **Consumer protection:** distance-selling and digital-service rules, clear pricing, subscription terms and cancellation, refund policy, public offer.
- **Online payments/fiscal:** receipts for payments (online cashier), provider requirements, subscription/auto-renewal disclosure.
- **Advertising law (38-ФЗ) and online ad marking/reporting** for partner banners and promo offers; labelling «Реклама», advertiser identification and token (ERID) requirements where applicable; no misleading claims.
- **Animals:** law on responsible treatment of animals (498-ФЗ) and related rules; veterinary rules for sale/transfer/transport (vet documents), restrictions on breeding/sale of certain species/hybrids/protected species, prohibited listings (e.g. endangered species, fighting purposes, cruelty), pedigree/registry naming rules; implement a **prohibited/restricted listings policy**, mandatory seller declarations, and moderation rules based on it.
- **Platform/marketplace and information-intermediary obligations** that may apply to a classifieds/marketplace service (verify applicability of current platform-economy and information-law requirements, user-content takedown handling, age restrictions, handling of unlawful content notices).
- **Telegram-in-Russia practicalities:** verify any current availability/regulatory constraints affecting bot/Mini App delivery and document fallback (web remains fully functional without Telegram).

Implementation requirements:
- Legal documents live **unobtrusively in the footer and secondary navigation**, but required notices/consents must appear **in context**: registration and Telegram onboarding (consent checkboxes/buttons, unticked by default, versioned records), data collection forms, partner/ad content labelling, payment and subscription steps (terms, auto-renewal, cancellation, refund), listing creation (seller declarations, prohibited-items notice).
- Provide document **templates with clearly marked fields** in `docs/legal/` for lawyer review, with company details loaded from configuration. **Never fabricate** company names, OGRN/INN, addresses, registration numbers, audits, certificates, "verified" statuses or legal assurances.
- Deliver `docs/COMPLIANCE.md` as a checklist table with columns: Requirement · Source/date · Status (`Implemented` / `Outstanding` / `Config dependency` / `Needs qualified Russian legal review`) · Where in code/doc.

---

## 14. MANDATORY PHASED EXECUTION

Work in order. Adjust sequence only where dependencies require it, and note it in `docs/DECISIONS.md`. Each phase must: produce real code; include relevant tests; fix discovered errors; update docs; end with a passing CI run, a push to the phase's own branch, a merged pull request and a version tag as defined in §3.1; produce a short report using the status labels from §0; then **continue to the next phase without waiting**, unless genuinely blocked.

1. **Architecture, repo, environment, requirements.** **First action: create the private repository and the Git/presentation scaffolding of §3.1.** Then: monorepo scaffold, tooling, CI, `make` targets, dev containers/compose, `.env.example`, ADRs, initial threat model, requirements traceability table (this document → issues/tests).
2. **Database schema and backend foundation.** Models, migrations, constraints, config with fail-fast validation, logging/metrics/health, error model, RBAC/policy layer skeleton, OpenAPI; **public response schemas/allowlists, private-data tables and the privacy-leak test harness (§6A.5–6A.6) from the start**.
3. **Authentication, accounts, secure account linking.** Sessions, password + Telegram login (validated), recovery, MFA for staff, consent records, link-token flow, merge flow, brute-force protection; auth/authorization tests.
4. **Website design and responsive interface.** Time-boxed exploration of 2–3 directions and an ADR (§4.1); tokens, typography, components, wordmark, selective Liquid Glass layer with fallbacks (§4.5.2), layouts, navigation (mobile floating tab bar/desktop), homepage with all sections and motion, accessibility and Lighthouse budgets; visual QA at all breakpoints (capture screenshots).
5. **Animal profiles, listings, search, filters.** CRUD, wizard, media pipeline, moderation states, FTS/filters, SEO-ready public pages.
6. **Swipe mechanics, favorites, matching, quotas.** §6.2, §1.2, §7 with concurrency/property tests.
7. **Messaging and notifications.** Persistent conversations, realtime, anti-spam, preferences, notification pipeline.
8. **Subscriptions and payments.** Plans, entitlements, providers, webhooks, idempotency, admin tools, sandbox tests; document blockers.
9. **Telegram bot.** Full behaviour §8.3, webhook, FSM, flood control, notifications, payments entry points; tests with a Telegram-API test double (and the Telegram test environment if credentials exist).
10. **Telegram Mini App.** §8.4 routes, validated auth, SDK integration, Stars purchase flow, device/viewport QA.
11. **Administration and moderation.** Admin UI, queues, reports, audit log, settings (N, plans, flags), MFA enforcement.
12. **Partners, SEO and growth.** §10 and §11.
13. **Security, privacy and legal.** Full §12 sweep: scanners, ZAP baseline against local/staging, header/CSP verification, injection corpora, IDOR/authorisation matrix completion, secret scans, dependency fixes; full §6A privacy suite across all channels; §13 implementation and compliance checklist.
14. **Integration, end-to-end testing and performance.** Playwright e2e across web and Mini App viewport; cross-channel scenarios (register in Telegram → log in on web → swipe on web → limit visible in bot → upgrade → entitlement visible everywhere); load tests (Locust/k6) on swipe, search, message paths; Lighthouse/CWV on key pages; accessibility audit (axe).
15. **Deployment, monitoring, backups, documentation.** Production compose/IaC for a Russia-located VPS or provider, reverse proxy/TLS, webhook registration script, monitoring/alerts, backup + **executed** restore test, runbooks, rollback, `docs/` complete.

---

## 15. DELIVERABLES AND FINAL ACCEPTANCE

The final repository must contain a runnable system, started through documented commands (`make dev`, `make test`, `make e2e`, `make ci`, `make prod-up`), with every external dependency listed.

Deliverables:
- Working website (SSR public pages + authenticated app), backend, database with migrations.
- Shared authentication and secure account linking across web, bot, Mini App.
- Animal profile and listing management for all purposes in §1.1.
- Discovery, real mutual matching, favorites, undo, persistent messaging.
- Server-enforced daily limits identical across all channels.
- Subscription and payment integration (verified in sandbox; production marked `BLOCKED` until credentials exist).
- Functioning Telegram bot (webhook) and Telegram Mini App.
- Partner management, tracking, inquiry flow, homepage and partners page.
- SEO foundations (§11).
- Protected admin + moderation with MFA and audit log.
- Responsive, accessible design that follows the creative direction of §4 (an original, improved interpretation — not a copy of any earlier concept), with selective Liquid Glass and fallbacks, the required homepage animations and reduced-motion support.
- Enforced owner privacy (§6A) with passing leak tests across every channel.
- Automated tests (unit, integration, authorization/IDOR, abuse, payment, e2e) with **actual run output** captured in `docs/TEST_REPORT.md`.
- A **private, professionally presented Git repository** as specified in §3.1: one branch and tag per phase/version, merged PRs, releases, milestones, README (EN + RU), changelog, templates and CI — verified by a fresh-clone run of the README instructions.
- Docs: `README.md`, `docs/ARCHITECTURE.md`, `DECISIONS.md`, `THREAT_MODEL.md`, `SECURITY_REPORT.md`, `PRIVACY_MODEL.md`, `COMPLIANCE.md`, `PAYMENTS.md`, `TELEGRAM.md` (BotFather setup, webhook, Mini App), `RUNBOOK.md` (deploy, rollback, backup/restore, incident response, secret rotation), `BLOCKERS.md`, `KNOWN_ISSUES.md`, API reference.

**Final report format (mandatory):** a requirements-traceability table covering every section of this prompt with status labels, links to evidence (test names, command output, screenshots), a list of `BLOCKED` items with the exact missing dependency, a list of items needing legal review, and a list of residual risks, and the repository link with a table of branches, tags and releases per version (or the exact blocker if the remote could not be created). Do not claim a feature works without the implementation and a test or documented run that supports it. Do not claim production deployment unless you actually performed it and can show the evidence.

**Self-check before declaring completion:** re-read this document top to bottom; for each section confirm implemented/verified/blocked; look for conflicts, vague areas, untested security claims and placeholder content; fix or report them. Then deliver the final report.

Begin with Phase 1 now.
