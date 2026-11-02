# PROJECT_SPEC.md

## 1. Core Purpose
BuyTelegramBots.com is a lightweight web application and webhook relay that showcases an inventory of Telegram handles and forwards web form bid submissions directly to a broker team's Telegram group chat.
The application also features dynamically generated, SEO-optimized landing pages for individual bots.

## 2. Tech Stack
* **Backend:** Python 3, FastAPI, Pydantic, HTTPX, `FileResponse`, `pathlib`, `python-dotenv`, Jinja2, os
* **Frontend:** Vanilla JavaScript (ES6+), HTML5 (`<dialog>` API), CSS3 (Variables, Flexbox, Grid)
* **Integrations:** Telegram Bot API (`sendMessage`), JSON static asset data (`bots.json`)
* **Relevant Files:** `main.py`, `templates/index.html`, `static/script.js`, `static/styles.css`, `static/favicon.png`, `static/bots.json`, `bots_individual_pages.json`, `templates/bot_detail.html`, `templates/404.html`

## 3. Active Features
* **Server-Rendered Asset Catalog:** The homepage (`templates/index.html`) is rendered by FastAPI/Jinja2 with one card per entry in `static/bots.json` (status badge, category tag, estimated value, link to its landing page). The cards are in the HTML the server sends, so search engines see every username and every landing-page link without running JavaScript.
* **Client-Side Category Filtering:** `script.js` filters the already-rendered cards instantly (Travel, Finance & Crypto, AI & Automation, Utilities) by setting each card's `hidden` attribute. `styles.css` needs `.asset-card[hidden] { display: none; }` for this, because `.asset-card` sets `display: flex`.
* **Dual Acquisition Paths:** Allows buyers to jump directly into Telegram or open a modal web form if they do not have Telegram installed.
* **Strict Input Validation (server-enforced):** Every rule is enforced in `main.py` (`FormSubmission`), not only in the browser: `bot_username` must be one of the handles in `static/bots.json`; `name` 1–100 chars; `contact` must match `CONTACT_PATTERN` (email, international phone, or `@TelegramUsername`); `bid` ≥ that listing's `min_bid` (from `bots_individual_pages.json`, the same number shown as "Minimum Offer" on its landing page) and ≤ $1,000,000; `notes` ≤ 1000 chars (keeps the alert under Telegram's 4096-char limit). Invalid submissions get HTTP 422 and never reach Telegram. The form's `pattern`/`min`/`max`/`maxlength` attributes mirror these rules for instant feedback: landing pages render `min="{{ bot.min_bid }}"`, and on the homepage `openOfferModal(username, minBid)` sets the shared form's `min` for the card that opened it. If the minimums can't be read, any bid > 0 is accepted (offers are never lost because of a broken file).
* **Spam Protection:** A hidden honeypot field (`hp_field`) silently drops bot submissions (returns success, sends nothing), and each visitor IP may make at most 5 accepted submissions per hour (HTTP 429 after that). The visitor IP is read from Cloudflare's `CF-Connecting-IP` header, because behind Cloudflare -> Nginx every request otherwise appears to come from `127.0.0.1`. The counter is in memory (resets on restart; assumes a single uvicorn process).
* **Environment-Aware API Routing:** Automatically detects local development environments (ports 3000/5500) vs production domains to route form POST submissions correctly. Note: CORS is disabled (same-origin only), so for local testing open the site through `uvicorn` itself rather than a separate static server on 3000/5500.
* **Telegram Notification Relay:** Formats incoming form data into structured HTML messages and dispatches them asynchronously via HTTPX to the team's Telegram group chat. Every buyer-typed field (`bot_username`, `name`, `contact`, `notes`) is passed through `escape_for_telegram()` (`html.escape(..., quote=False)`) first, so characters like `&`, `<`, `>` are shown literally instead of breaking the message or injecting formatting/links.
* **Whitelisted Static Serving:** Public frontend files (HTML, CSS, JS, favicon, `bots.json`) live in `web/static/` and are served by FastAPI **only from that folder** (`/<file.ext>` → `static/<file.ext>`; the homepage `/` is a template, and the old `/index.html` address 301-redirects to `/`). Every other file in `web/` (`.env`, `main.py`, `templates/`, etc.) returns 404. Public URLs stay at the site root (e.g. `/styles.css`).
* **Dynamic SEO Landing Pages (SSR):** Natively renders individual landing pages (e.g., /flightticketbot) on the backend via FastAPI and Jinja2. This injects specific Open Graph meta tags before the HTML leaves the server, guaranteeing rich link previews in Telegram without relying on client-side JS.

* **One Canonical Address (`SITE_URL`):** The site's only public address is `https://www.buytelegrambots.com` (the version without `www` 301-redirects to it). `main.py` defines it once as `SITE_URL` (overridable in `web/.env`) and exposes it to every template as `{{ SITE_URL }}`. `robots.txt`, every `sitemap.xml` entry, each landing page's canonical link and its JSON-LD `url` are built from it. The homepage template uses `{{ SITE_URL }}` for its canonical and `og:url` too.

## 4. Current Data Flow
1. **Catalog Load:** FastAPI reads `static/bots.json` -> renders `templates/index.html` with every card already in the HTML -> browser shows it; JS only handles filtering and the offer modal.
2. **Modal Trigger:** User clicks "submit via Web Form" -> JS populates target handle in target field -> Displays `<dialog>` modal.
3. **Client Submission:** User submits form -> browser validates inputs (the listing's minimum, $1,000,000 maximum, contact pattern, notes length) -> JS sends JSON POST payload (including the empty honeypot `hp_field`) to `/api/submit-form`.
4. **Backend Processing:** FastAPI receives request -> Pydantic model (`FormSubmission`) enforces all field rules (422 if invalid) -> honeypot check (drop silently) -> per-IP rate limit (429 if exceeded) -> Escapes buyer-typed text -> Formats HTML alert body.
5. **Telegram Dispatch:** Backend fires asynchronous POST request via HTTPX to Telegram API (`sendMessage`) -> Alert delivers to `GROUP_CHAT_ID`.
6. **Dynamic Route Navigation:** ser navigates to /<slug> -> FastAPI intercepts and checks bots_individual_pages.json -> If found, injects data into templates/bot_detail.html via Jinja2 -> Returns fully rendered SSR HTML to the client

## 5. Expressed Non-Goals / Things to Avoid
* **No Local Database Persistence:** Avoids SQL databases or ORMs; leads are forwarded directly to Telegram in real time rather than stored on a local server.
* **No Heavy Frontend Frameworks:** Avoids React, Vue, or complex build pipelines; strictly uses native vanilla JS, native HTML `<dialog>`, and raw CSS. All dynamic routing must remain on the FastAPI backend using Vanilla JS and HTML templating.
* **No On-Site Payment Processing:** Avoids holding funds or handling payment gateways on the web; transfer and payment execution happen offline via @BotFather or direct broker chat.
* **No User Accounts or Authentication:** Avoids login flows, buyer profiles, or session tracking.
* **No Browser-Only Rules:** Every rule in the web form must also be enforced in `FormSubmission`. Anyone can post to `/api/submit-form` without a browser. When changing a form `pattern`, update `CONTACT_PATTERN` too (and keep `-`, `(`, `)` escaped inside `[...]` — modern browsers reject the pattern otherwise and silently skip the check).
* **No Open CORS:** Do not re-add `CORSMiddleware` with `allow_origins=["*"]`; the form and API share one domain.
* **No Unescaped User Text in Telegram Messages:** Never insert buyer-typed text into a Telegram HTML message without `escape_for_telegram()`. A single raw `&` or `<` makes Telegram reject the whole message and the offer is lost.
* **No Client-Side Catalog Rendering:** Do not go back to building the homepage cards in JavaScript (`fetch('bots.json')`). Google may not run it, and then the homepage has no usernames and no links to the landing pages.
* **No Addresses That Redirect:** Never write `https://buytelegrambots.com/...` (without `www`) in a canonical link, sitemap, robots.txt, `og:url` or JSON-LD. Google does not index addresses that redirect. Use `{{ SITE_URL }}` in templates and `SITE_URL` in Python.
* **No Private Files in `static/`:** Everything inside `web/static/` is downloadable by anyone. Never place secrets, `.env` files, source code, or internal data there, and never serve files from the `web/` folder itself (no `StaticFiles(directory=".")`, no `os.path.isfile(slug)`).