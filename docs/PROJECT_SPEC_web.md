# PROJECT_SPEC.md

## 1. Core Purpose
BuyTelegramBots.com is a lightweight web application and webhook relay that showcases an inventory of Telegram handles and forwards web form bid submissions directly to a broker team's Telegram group chat.
The application also features dynamically generated, SEO-optimized landing pages for individual bots.

## 2. Tech Stack
* **Backend:** Python 3, FastAPI, Pydantic, HTTPX, StaticFiles, `python-dotenv`, Jinja2, os
* **Frontend:** Vanilla JavaScript (ES6+), HTML5 (`<dialog>` API), CSS3 (Variables, Flexbox, Grid)
* **Integrations:** Telegram Bot API (`sendMessage`), JSON static asset data (`bots.json`)
* **Relevant Files:** `main.py`, `index.html`, `script.js`, `styles.css`, `bots.json`, `bots_individual_pages.json`, `\templates\bot_detail.html`

## 3. Active Features
* **Dynamic Asset Catalog Loading:** Fetches and renders available bot cards directly from `bots.json` with status badges, category tags, and estimated market valuations.
* **Client-Side Category Filtering:** Filters listed handles instantly across categories (Travel, Finance & Crypto, AI & Automation, Utilities) without reloading the page.
* **Dual Acquisition Paths:** Allows buyers to jump directly into Telegram or open a modal web form if they do not have Telegram installed.
* **Strict Input Validation:** Enforces regex validation for contacts (Telegram handle, email, or international phone) and hard-caps minimum bid amounts at $100.
* **Environment-Aware API Routing:** Automatically detects local development environments (ports 3000/5500) vs production domains to route form POST submissions correctly.
* **Telegram Notification Relay:** Formats incoming form data into structured HTML messages and dispatches them asynchronously via HTTPX to the team's Telegram group chat.
* **Built-In Static Serving:** Configured to serve static frontend files (HTML, CSS, JS) directly through the FastAPI app instance.
* **Dynamic SEO Landing Pages (SSR):** Natively renders individual landing pages (e.g., /flightticketbot) on the backend via FastAPI and Jinja2. This injects specific Open Graph meta tags before the HTML leaves the server, guaranteeing rich link previews in Telegram without relying on client-side JS.

## 4. Current Data Flow
1. **Catalog Load:** Frontend initializes -> JS fetches `bots.json` -> Renders inventory cards in DOM.
2. **Modal Trigger:** User clicks "submit via Web Form" -> JS populates target handle in target field -> Displays `<dialog>` modal.
3. **Client Submission:** User submits form -> JS validates inputs ($100 minimum, contact pattern) -> JS sends JSON POST payload to `/api/submit-form`.
4. **Backend Processing:** FastAPI receives request -> Pydantic model (`FormSubmission`) parses and validates schema -> Formats HTML alert body.
5. **Telegram Dispatch:** Backend fires asynchronous POST request via HTTPX to Telegram API (`sendMessage`) -> Alert delivers to `GROUP_CHAT_ID`.
6. **Dynamic Route Navigation:** ser navigates to /<slug> -> FastAPI intercepts and checks bots_individual_pages.json -> If found, injects data into templates/bot_detail.html via Jinja2 -> Returns fully rendered SSR HTML to the client

## 5. Expressed Non-Goals / Things to Avoid
* **No Local Database Persistence:** Avoids SQL databases or ORMs; leads are forwarded directly to Telegram in real time rather than stored on a local server.
* **No Heavy Frontend Frameworks:** Avoids React, Vue, or complex build pipelines; strictly uses native vanilla JS, native HTML `<dialog>`, and raw CSS. All dynamic routing must remain on the FastAPI backend using Vanilla JS and HTML templating.
* **No On-Site Payment Processing:** Avoids holding funds or handling payment gateways on the web; transfer and payment execution happen offline via @BotFather or direct broker chat.
* **No User Accounts or Authentication:** Avoids login flows, buyer profiles, or session tracking.