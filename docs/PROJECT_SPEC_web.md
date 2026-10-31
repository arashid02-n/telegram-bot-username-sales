# PROJECT_SPEC.md

## 1. Core Purpose
BuyTelegramBots.com is a lightweight web application and webhook relay that showcases an inventory of Telegram handles and forwards web form bid submissions directly to a broker team's Telegram group chat.
The application also features dynamically generated, SEO-optimized landing pages for individual bots.

## 2. Tech Stack
* **Backend:** Python 3, FastAPI, Pydantic, HTTPX, `FileResponse`, `pathlib`, `python-dotenv`, Jinja2, os
* **Frontend:** Vanilla JavaScript (ES6+), HTML5 (`<dialog>` API), CSS3 (Variables, Flexbox, Grid)
* **Integrations:** Telegram Bot API (`sendMessage`), JSON static asset data (`bots.json`)
* **Relevant Files:** `main.py`, `static/index.html`, `static/script.js`, `static/styles.css`, `static/favicon.png`, `static/bots.json`, `bots_individual_pages.json`, `templates/bot_detail.html`, `templates/404.html`

## 3. Active Features
* **Dynamic Asset Catalog Loading:** Fetches and renders available bot cards directly from `bots.json` with status badges, category tags, and estimated market valuations.
* **Client-Side Category Filtering:** Filters listed handles instantly across categories (Travel, Finance & Crypto, AI & Automation, Utilities) without reloading the page.
* **Dual Acquisition Paths:** Allows buyers to jump directly into Telegram or open a modal web form if they do not have Telegram installed.
* **Strict Input Validation (server-enforced):** Every rule is enforced in `main.py` (`FormSubmission`), not only in the browser: `bot_username` must be one of the handles in `static/bots.json`; `name` 1–100 chars; `contact` must match `CONTACT_PATTERN` (email, international phone, or `@TelegramUsername`); `bid` > 0 and ≤ $1,000,000; `notes` ≤ 1000 chars (keeps the alert under Telegram's 4096-char limit). Invalid submissions get HTTP 422 and never reach Telegram. The form's `pattern`/`min`/`max`/`maxlength` attributes mirror these rules for instant feedback; the browser additionally requires a $100 minimum.
* **Spam Protection:** A hidden honeypot field (`hp_field`) silently drops bot submissions (returns success, sends nothing), and each visitor IP may make at most 5 accepted submissions per hour (HTTP 429 after that). The visitor IP is read from Cloudflare's `CF-Connecting-IP` header, because behind Cloudflare -> Nginx every request otherwise appears to come from `127.0.0.1`. The counter is in memory (resets on restart; assumes a single uvicorn process).
* **Environment-Aware API Routing:** Automatically detects local development environments (ports 3000/5500) vs production domains to route form POST submissions correctly. Note: CORS is disabled (same-origin only), so for local testing open the site through `uvicorn` itself rather than a separate static server on 3000/5500.
* **Telegram Notification Relay:** Formats incoming form data into structured HTML messages and dispatches them asynchronously via HTTPX to the team's Telegram group chat. Every buyer-typed field (`bot_username`, `name`, `contact`, `notes`) is passed through `escape_for_telegram()` (`html.escape(..., quote=False)`) first, so characters like `&`, `<`, `>` are shown literally instead of breaking the message or injecting formatting/links.
* **Whitelisted Static Serving:** Public frontend files (HTML, CSS, JS, favicon, `bots.json`) live in `web/static/` and are served by FastAPI **only from that folder** (`/` → `static/index.html`, `/<file.ext>` → `static/<file.ext>`). Every other file in `web/` (`.env`, `main.py`, `Dockerfile`, `templates/`, etc.) returns 404. Public URLs stay at the site root (e.g. `/styles.css`).
* **Dynamic SEO Landing Pages (SSR):** Natively renders individual landing pages (e.g., /flightticketbot) on the backend via FastAPI and Jinja2. This injects specific Open Graph meta tags before the HTML leaves the server, guaranteeing rich link previews in Telegram without relying on client-side JS.

## 4. Current Data Flow
1. **Catalog Load:** FastAPI serves `static/index.html` at `/` -> JS fetches `/bots.json` (served from `static/`) -> Renders inventory cards in DOM.
2. **Modal Trigger:** User clicks "submit via Web Form" -> JS populates target handle in target field -> Displays `<dialog>` modal.
3. **Client Submission:** User submits form -> browser validates inputs ($100 minimum, $1,000,000 maximum, contact pattern, notes length) -> JS sends JSON POST payload (including the empty honeypot `hp_field`) to `/api/submit-form`.
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
* **No Private Files in `static/`:** Everything inside `web/static/` is downloadable by anyone. Never place secrets, `.env` files, source code, or internal data there, and never serve files from the `web/` folder itself (no `StaticFiles(directory=".")`, no `os.path.isfile(slug)`).