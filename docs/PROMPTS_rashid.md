# Prompt Ledger & AI Workflow Log

This document records the prompt chains, context specifications, and human adjustments used to develop the Telegram Bot Username Sales Platform.

---

## Template (Copy for every new entry)

### [LOG-00X] Feature / Task Name
- Date: YYYY-MM-DD
- Target Component: [e.g., /bot, /web, Deployment, CI/CD]
- Objective: Brief description of what we are building or fixing.
- Context Provided: [e.g., PROJECT_SPEC.md, repository structure]
- System / Task Prompt:
> "Paste the exact prompt given to the AI here."

- AI Raw Output Summary: Brief summary of the generated output.
- Human Refinements (The "Brakes"): Manual corrections, architectural decisions, or adjustments.
- Related Git Commit: [commit hash or message]

---

## [LOG-001] Monorepo Consolidation, Repository Migration & GitFlow Setup

- Date: 2026-07-24 – Rashid Nazari
- Target Component: Repository Architecture, Git, Deployment
- Objective: Merge the independent Telegram Bot and Website repositories into a single maintainable monorepo while preserving Git history, introducing a clean GitFlow workflow, and preparing the repository for long-term collaborative development.

- Context Provided:
  - Existing Bot Repository
  - Existing Website Repository
  - PROJECT_SPEC.md
  - Existing deployment structure on Ubuntu Server
  - Existing GitHub repositories

- System / Task Prompt:

> I currently have two completely separate Git repositories:
>
> • Telegram Bot
> • Website
>
> I want to migrate them into a single professional monorepo.
>
> The final repository structure must become:
>
>
> telegram-bot-username-sales/
> ├── bot/
> ├── web/
> ├── docs/
> │   ├── PROJECT_SPEC.md
> │   └── PROMPTS.md
> ├── README.md
> ├── LICENSE
> └── .gitignore
> 
>
> Requirements:
>
> - Preserve Git history from both repositories.
> - Use Git Subtree (not Git Submodules).
> - Create a professional GitFlow branching model.
> - Create proper README structure.
> - Move all documentation into the docs folder.
> - Keep deployment unaffected after migration.
> - Explain every Git command before executing it.
> - Never rewrite commit history.
> - Produce an enterprise-grade repository layout suitable for long-term collaboration.
>
> Output the migration process step-by-step and explain the reasoning behind every architectural decision.

---

### AI Raw Output Summary

The AI generated:

- A complete monorepo migration strategy.
- Git Subtree migration workflow.
- Professional repository hierarchy.
- GitFlow branching model.
- Remote migration plan.
- Documentation organization.
- Branch strategy for future collaboration.
- Safe migration procedure without rewriting Git history.

---

### Human Refinements (The "Brakes")

Several architectural decisions were adjusted manually during implementation:

- Finalized the repository structure as:

telegram-bot-username-sales/
├── bot/
├── web/
├── docs/
│   ├── PROJECT_SPEC.md
│   └── PROMPTS.md
├── README.md
├── LICENSE
└── .gitignore

- Preserved both repositories using Git Subtree rather than Submodules.
- Added dedicated documentation inside the docs/ directory.
- Standardized GitFlow branches (main, develop, feature/*, release/*, hotfix/*).
- Performed deployment validation after migration to ensure production remained operational.
- Verified that Git history from both original repositories remained intact after import.

---

### Related Git Commit

chore(repo): consolidate bot and website repositories into a unified monorepo

---

## [LOG-002] Full-Site Copywriting, SEO & Data-Layer Content Overhaul

- Date: 2026-08-05 – Rashid Nazari
- Target Component: /web (bots.json, bots_individual_pages.json), docs (copy deliverables)
- Objective: Run a complete conversion-copywriting, SEO, and UX-writing audit of the live marketplace (Home page + all 18 individual bot listing pages), then rewrite every text surface — hero, trust badges, CTAs, offer form, FAQ, homepage card short descriptions, and full product-page copy (pitch / ideal buyer profile / use cases) — and apply the approved text directly into the two live data files without altering any non-text field.

- Context Provided:
  - Live site content, crawled directly from buytelegrambots.com (Home page + all 18 individual listing URLs: gramauctionbot, tradegramsbot, flightticketbot, thataicoachbot, gramiumbot, gramancebot, onegrambot, mygramsbot, freegramsbot, milligrambot, dollarstogramsbot, eurostogramsbot, poundstogramsbot, bitcoin2grambot, dollars2gramsbot, euros2gramsbot, pound2grambot, grams4freebot)
  - `bots.json` (Home page listing data)
  - `bots_individual_pages.json` (individual product-page data)
  - `main.py` and `templates/bot_detail.html` (to diagnose why edited copy wasn't rendering live)
  - `docs/PROJECT_SPEC_web.md` (confirmed FastAPI + Jinja2 SSR architecture, no frontend framework)

- System / Task Prompt:

> ROLE
> You are a Senior Conversion Copywriter, SEO Strategist, UX Writer, and Brand Messaging Expert specializing in high-converting SaaS platforms, digital marketplaces, and Telegram-related businesses.
> Your job is NOT to redesign the UI.
> Your job is to completely audit and rewrite every piece of text on the website to maximize trust, clarity, SEO, and conversion rate.
> You must think like someone working at Stripe, Linear, Notion, Vercel, or GitHub.
>
> PROJECT
> Website: buytelegrambots.com
> Business Model: Telegram Username & Bot Marketplace
> Type: Auction Marketplace
> Target Audience: Buyers looking to purchase premium Telegram bots and Telegram usernames.
> Primary Goal: Convert visitors into qualified buyers by encouraging them to submit an offer. After an offer is submitted, negotiations are handled by the platform administrator.
> Competitive Advantages: Safe transactions, fast negotiations, professional service.
> Brand Voice: Professional, modern, trustworthy, clean, confident, minimal.
> Website Structure: Home, Individual Product Pages (each Telegram bot has its own page).
>
> YOUR TASK
> First, analyze the ENTIRE website. Do NOT rewrite anything immediately. Instead produce a complete audit. For every page explain: what is good, what is weak, what reduces trust, what hurts conversions, what hurts SEO, what should be removed, what should be rewritten, what should be added.
> Then improve every section including: Hero Title, Hero Subtitle, CTA Buttons, Product Headlines, Product Descriptions, FAQ, Trust Section, Feature Sections, Footer, Error Messages, Empty States, Form Labels, Offer Submission Flow, Success Messages, Navigation Labels.
> Generate: better page titles, meta descriptions, H1/H2 hierarchy, internal linking suggestions, keyword placement, keyword density improvements, structured content suggestions, for primary keywords (buy telegram bots, telegram bots for sale, telegram usernames for sale, telegram marketplace, telegram auction) plus researched high-value long-tail keywords.
> Research leading marketplaces and premium SaaS websites for inspiration; explain what can be learned from them without copying their content.
> Work page by page. For each page provide: Audit, Problems, SEO Improvements, Copywriting Improvements, Complete rewritten content, Explanation of why each change improves conversions.
> At the end, generate a professional PROMPTS.md document containing every AI prompt required to reproduce all generated copy in the future.

- AI Raw Output Summary:
  - A full audit-and-rewrite document covering the Home page (hero, trust badges, category filters, How-It-Works modal, offer form, empty/success states, footer) and a Product Page template, plus new Trust & Safety and FAQ sections, SEO metadata patterns, and a standalone `PROMPTS.md` prompt library.
  - Live-crawled all 18 individual product pages and discovered two real, shipped bugs during the audit rather than assumed ones: (1) the offer-form's minimum-bid copy was hardcoded to a single global value while several listings had different real minimums, producing a visible on-page contradiction; (2) the offer-modal title rendered a literal unfilled placeholder (`@Bot`) instead of the actual handle.
  - Produced full copywriting rewrites for all 18 listings (unique `pitch` / `ideal_for` / `use_cases`, replacing category-wide duplicate boilerplate) and a separate homepage card format (`Best For:` label + shortened description).
  - Diagnosed, from `main.py` and `bot_detail.html`, why previously-approved copy wasn't appearing live: the code correctly reads `bot.pitch`/`ideal_for`/`use_cases` from `bots_individual_pages.json`, so the gap was a stale/unsynced data file on the deployed branch rather than a template or routing bug.

- Human Refinements (The "Brakes"):
  - Corrected an early assumption that the site had no per-listing URLs (single-page/modal architecture) after being given the live `/gramauctionbot`-style URL — audit was revised to reflect the real, already-existing per-listing pages.
  - Rejected the marketplace's "escrow" language (both in the transfer-mechanism copy and inside a use-case description) as a mislabeled claim — the actual mechanism is a direct @BotFather transfer, not third-party escrow — and flagged it as a trust/compliance risk rather than a wording preference.
  - Enforced a strict "text-only" edit boundary on every JSON pass: preserved `id`/`username` in `bots.json` and `slug`/`handle` in `bots_individual_pages.json` exactly as shipped (rather than normalizing field names across the two files) after confirming `main.py`/`bot_detail.html` hardcode those exact keys — changing them would have broken the live routes.
  - Verified line-for-line, via diff, that every JSON hand-off changed only the intended field(s) (`desc`, or `pitch`/`ideal_for`/`use_cases`) and left `est_value`, `min_bid`, `status`, `status_code`, and `category` untouched, before handing files back.
  - Preserved original file formatting (2-space indent, trailing-newline behavior) to keep diffs clean for review.

- Related Git Commit: `docs(web): homepage & product-page copywriting overhaul (bots.json, bots_individual_pages.json)` — *(placeholder — replace with actual commit hash/message once committed)*
