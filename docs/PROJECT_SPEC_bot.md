# PROJECT_SPEC.md

## 1. Core Purpose
A multi-tenant Telegram bot system designed to broker, manage, and help negotiate the sale of Telegram bot usernames between buyers and an independent broker.

## 2. Tech Stack & Architecture
* **Language & Runtime:** Python 3.x (`asyncio`)
* **Bot Framework:** `aiogram` 3.x (Modular Routers, FSM with `MemoryStorage`, Inline Keyboards, Custom Filters)
* **Database:** SQLite 3 (`bot/bids.db` with `bids` and active negotiation topic tracking). The path is absolute (resolved from `database.py`'s own folder, overridable with `DB_PATH` in `bot/.env`), so the same file is used no matter which folder the bot is started from.
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

## 5. Button Map
Every inline button's `callback_data` and the one handler that answers it. A handler whose `callback_data` no button produces is dead code. It can only be triggered by a hand-crafted update and is easy to break unnoticed. Remove it, or add its button in the same change.

| `callback_data` | Button(s) | Handler |
|---|---|---|
| `make_offer` | Make an Offer / Change Offer / Make / Change Offer | `handlers/bidding.py` `cb_make_offer` |
| `asset_info:<source>` | Username Info | `handlers/callbacks.py` `cb_asset_info` |
| `explore_ids:<source>` | Other Available Usernames | `handlers/callbacks.py` `cb_explore_ids` |
| `back:<source>` | Back | `handlers/callbacks.py` `cb_back_routing` |
| `admin_negotiate_<buyer_id>` | Start Negotiation (admin group) | `handlers/negotiation.py` |
| `admin_endnego_<buyer_id>` | End Negotiation (admin topic) | `handlers/negotiation.py` |

`<source>` (`start`, `nobid`, `mybid`, `end_nego`, `catchall`) tells **Back** which screen to return to.

## 6. Expressed Non-Goals / Things to Avoid
* **No Webhooks / REST APIs:** Relying on webhooks is avoided in favor of long-polling (`dp.start_polling`) with automatic webhook removal on launch. Pending updates are **kept** (`drop_pending_updates=False`): messages buyers sent while the bot was down or restarting are answered when it comes back (Telegram holds them up to 24h). Do not switch this back to `True`.
* **Production:** runs as the systemd service `gram-bid-system` (definition in `deploy/gram-bid-system.service`); see `PROJECT_SPEC_deployment.md`.
* **No Destructive Database Mutations:** Avoid deleting records or dropping tables when modifying offer statuses.
* **No External Cache / Complex Storage:** Avoid Redis or external message brokers; stick to lightweight, in-memory storage (`MemoryStorage`) and direct SQLite queries.
* **No Over-Engineering:** While the codebase is modularized for maintainability and separated by routing concerns, avoid heavy OOP patterns, ORMs, microservice architectures, or unnecessary abstraction layers. Keep database functions and router logic direct and readable.