# PROJECT_SPEC.md

## 1. Core Purpose
A multi-tenant Telegram bot system designed to broker, manage, and help negotiate the sale of Telegram bot usernames between buyers and an independent broker.

## 2. Tech Stack & Architecture
* **Language & Runtime:** Python 3.x (`asyncio`)
* **Bot Framework:** `aiogram` 3.x (Modular Routers, FSM with `MemoryStorage`, Inline Keyboards, Custom Filters)
* **Database:** SQLite 3 (`bids.db` with `bids` and active negotiation topic tracking)
* **Environment & Config:** `python-dotenv` (`load_dotenv`), `os`, `sys`, `logging`
* **Text Formatting & Parsing:** Regex (`re`) for email/phone validation, HTML Parse Mode for Telegram messages
* **Project Structure:** Modularized architecture grouped by domain:
  * `main.py` - Application entry point, bot initialization, webhook cleanup, and polling orchestration.
  * `database.py` - SQLite operations and queries.
  * `config.py` - Environment variables, logging setup, and global state constants.
  * `states.py` - FSM state definitions (`BidStates`).
  * `keyboards.py` - Inline and reply keyboard markup builders.
  * `filters.py` - Custom aiogram filters (e.g., `InLiveChatFilter`).
  * `services/notifications.py` - Admin notification formatting and dispatch logic.
  * `handlers/` - Router package separating commands, bidding FSM, callbacks, and negotiation logic.

## 3. Active Features
* **Multi-Bot Network Execution:** Runs multiple Telegram bot instances simultaneously from a comma/newline-delimited token string (`BOT_TOKENS`), dynamically auto-generating a global portfolio list (`PORTFOLIO_IDS`).
* **Bid Registration & Upsert:** Enables buyers to place or update numeric USD bids per asset; handles database persistence via `save_or_update_bid()`.
* **Smart Contact Parsing:** Detects email addresses and telephone numbers via regular expressions to auto-generate clickable `mailto:`, `tel:`, and tap-to-copy HTML text snippets for admins.
* **Admin Group Broadcasts:** Dispatches immediate alert notifications with bid details and inline control buttons to a designated centralized Telegram admin group chat (`GROUP_CHAT_ID`).
* **Two-Way Broker-Buyer Communication Channel:** Enables real-time chatting between the buyer (the bot proxies any messages received to a dedicated topic in the admin group chat) and admin (sends messages in a customized topic for the buyer, which route back to the user). The buyer cannot use standard bot functions while in negotiation mode.

## 4. Current Data Flow
1. **Initiation & Offer Entry:** Buyer launches bot (`/start` or `/my_bid`) -> FSM state accepts numeric USD input -> SQLite updates/inserts entry into `bids` table.
2. **Contact Processing:** Buyer optionally supplies email or phone -> System validates input -> Formatted contact string generated.
3. **Broker Group Alert:** System constructs HTML notification -> Pushes alert to `GROUP_CHAT_ID` with inline action button (`Start Negotiation`).
4. **Negotiation Process - Admin Side:** Admin clicks `Start Negotiation`. A new forum topic with the buyer's details opens in the Group Chat. The Admin can chat with the buyer inside this topic. Any messages sent by the admin here are redirected to the buyer via the bot.
5. **Negotiation Process - Buyer Side:** The Bot gives a notice that it has `initiated Live Mode` and any message sent here will be redirected to the admin. Standard bot routing is suspended in this state until the admin clicks `End Negotiation` inside the topic.

## 5. Expressed Non-Goals / Things to Avoid
* **No Webhooks / REST APIs:** Relying on webhooks is avoided in favor of long-polling (`dp.start_polling`) with automatic webhook purging on launch.
* **No Destructive Database Mutations:** Avoid deleting records or dropping tables when modifying offer statuses.
* **No External Cache / Complex Storage:** Avoid Redis or external message brokers; stick to lightweight, in-memory storage (`MemoryStorage`) and direct SQLite queries.
* **No Over-Engineering:** While the codebase is modularized for maintainability and separated by routing concerns, avoid heavy OOP patterns, ORMs, microservice architectures, or unnecessary abstraction layers. Keep database functions and router logic direct and readable.