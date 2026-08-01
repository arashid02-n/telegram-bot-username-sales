# Prompt Ledger & AI Workflow Log

This document records the prompt chains, context specifications, and human adjustments used to develop features for the Telegram Bot Username Sales Platform.

---

## Template (Copy for every new entry)

### [LOG-00X] Feature / Task Name
- **Date:** YYYY-MM-DD
- **Target Component:** `[e.g., /bot, /web, Nginx, CI/CD]`
- **Objective:** Brief description of what we are building or fixing.
- **Context Provided:** `[e.g., PROJECT_SPEC.md, current bot.py file]`
- **System / Task Prompt:**
> "Paste the exact prompt given to the AI here."

- **AI Raw Output Summary:** Brief note on what code or text the AI produced.
- **Human Refinements (The "Brakes"):** What did you manually remove, change, or correct from the AI's output?
- **Related Git Commit:** `[commit hash or message]`

---


### [LOG-001] Live Chat State Lock & Main Chat Bid Routing
- **Date:** 2026-07-27 - Yousef Babaki
- **Target Component:** `/bot/database.py`, `/bot/main.py`
- **Objective:** Implement bi-directional proxy chat between buyer PM and Forum Topic, while enforcing that all new incoming bid notifications strictly route to the Main Admin Chat (General Topic)(`message_thread_id=None`).
- **Context Provided:** `PROJECT_SPEC.md` Non-Goals & SQLite schema, main.py
- **System / Task Prompt:**
> Implement a 'Live Chat' state lock between a buyer's private PM and a dedicated Admin Forum Topic in a Telegram Supergroup, while ensuring all new incoming bid alerts strictly route to the Main Chat.
Requirements & Workflow:
Triggering Live Chat (Admin side):
When an admin clicks the [💬 Start Negotiation] inline button on a bid alert in the admin group:
Create a new Forum Topic using context.bot.create_forum_topic.
Save user_id, topic_id, and status = 'LIVE_CHAT' in our SQLite negotiations table.
Send a notice to the buyer's private PM:
"You are now in a live chat with an admin regarding [Target Username]. You can send messages, photos, or documents directly in this chat."
Pass reply_markup=ReplyKeyboardRemove() to remove any existing bot menu buttons.
State Lock & Media Forwarding (Buyer PM -> Admin Topic):
Add a high-priority message handler that checks if buyer_user_id has an active LIVE_CHAT status in SQLite.
If status == 'LIVE_CHAT':
Intercept ALL incoming message types (Text, Photo, Document, Voice, Audio, Sticker).
Use context.bot.copy_message(chat_id=ADMIN_GROUP_ID, message_thread_id=topic_id, from_chat_id=user_id, message_id=update.message.message_id) to preserve exact formatting and attachments inside the Admin Topic.
Block standard bot commands/menu handlers while in this state.
Proxy Forwarding (Admin Topic -> Buyer PM):
Listen for messages in the Admin Supergroup where message_thread_id matches an active topic_id in SQLite.
Ignore messages sent by bots.
Forward/copy any admin message straight to the buyer's user_id PM using context.bot.copy_message.
Ending Negotiation (Admin side):
Send a pinned message in the Forum Topic with a [❌ End Negotiation] inline button.
When clicked: Update SQLite status = 'CLOSED', send a final notice to the buyer, restore the main menu keyboard (ReplyKeyboardMarkup), and call context.bot.close_forum_topic.
CRITICAL RULE — Global Main Chat Bid Routing:
Whenever ANY user places a new bid (even while admins are chatting with other buyers in sub-topics), the notification message MUST ALWAYS be posted to the Main Chat / General Topic of the Admin Group (chat_id=ADMIN_GROUP_ID, with message_thread_id=None or General Topic ID).
New bid notifications must NEVER be dispatched inside an active negotiation thread.
Output Formatting Instructions:
Explain the implementation step-by-step.
Specify the exact file names and code placement for every snippet (e.g., where to put database queries, where handler functions belong, and how/where to register them in main.py using Application.add_handler)."
you can send the answer in a few messages if needs be.

- **AI Raw Output Summary:** Provided modular handler functions, database helper functions, and exact placement instructions for `main.py` & `database.py` handler order.
- **Human Refinements (The "Brakes"):** 
  - Verified handler priority in `main.py` so the `LIVE_CHAT` state handler runs before standard command handlers.
  - Confirmed `message_thread_id=None` on bid notification alerts to prevent leakages into active negotiation threads.
  - `start negotiations` button dissappearing after being clicked.
  - customizing name of the topic in GC.
  - deleting the functions and logic for `chat history` and `bid lock` and `single message reply`
  - Fixed double notification bug when the buyer provides their contact info.
  

- **Related Git Commit:** `feat(bot): add live chat state lock and main chat bid routing guardrail.`

### [LOG-002] Feature / Task Name
- **Date:** 2026-7-29 - Yousef Babaki
- **Target Component:** `/web/main.py`, `/web/script.js`, `/web/styles.css`, `/web/bot_detail.html`, `/web/bots_individual_pages.json`
- **Objective:** Building dynamic landing pages for individual usernames.
- **Context Provided:** `PROJECT_SPEC.md`, `index.html`, `script.js`, `styles.css`, `bots.json`, `main.py`
- **System / Task Prompt:**
> Dynamic SEO Landing Pages for Individual Usernames:
I have attached my PROJECT_SPEC.md along with my code files.
Objective:
Build dynamic landing pages for individual usernames (e.g., [domain.com/flighttickets](https://domain.com/flighttickets)) driven by a local usernames.json dataset, with dynamic SEO meta tags and fully responsive layouts that render cleanly across mobile phones, tablets, laptops, and desktop PCs.
Requirements & Deliverables:
Data Model (bots_individual_pages.json):
Create a structured JSON file listing usernames. Include fields: slug, handle (e.g., @flighttickets), title, status (AVAILABLE/SOLD), min_bid, description, and an array of use_cases.
Dynamic Route Component (BotsDetail.jsx):
Use react-router-dom to extract the slug parameter from the URL.
Match the parameter against usernames.json.
Cross-Device Responsive Layout: Use standard Tailwind CSS breakpoints (sm:, md:, lg:) to ensure the page layout scales fluidly. On desktops and laptops, use standard centered containers with generous spacing. On tablets and mobile phones, adapt padding, font sizes, and layout grids so no text overflows or creates horizontal scrollbars. Match the color scheme, typography, and container styling of the attached homepage component.
Dynamic SEO Update: Use a standard React useEffect hook to dynamically update document.title and <meta name="description"> when the page mounts or the slug changes (do NOT install extra packages like react-helmet).
Call To Action (CTA): Display a prominent button linking directly to the Telegram bot with a deep-link parameter ([https://t.me/YourBotName?start=](https://t.me/YourBotName?start=)[slug]).
404 Fallback State: If the URL slug does not exist in usernames.json, display a clean, responsive 'Username Not Found' view with a button returning to the main page.
Router Setup (App.jsx):
Show how to integrate this new route into App.jsx alongside existing routes.
Nginx SPA Configuration:
Provide the exact Nginx try_files rule to ensure direct URL loads or refreshes on /flighttickets do not trigger a 404 error on the live server.
Output Formatting Instructions:

Explain the implementation step-by-step.
Specify exact file paths and code placement for every snippet.
Keep language direct, concise, and free of AI marketing fluff (no "digital assets" terminology), strictly following the rules in PROJECT_SPEC.md.

- **AI Raw Output Summary:** How to Implement Dynamic Username Pages in Vanilla JS + FastAPI.
- **Human Refinements (The "Brakes"):** 
> Fixed a direct contradiction between the prompt and the PROJECT_SPEC.md concerning Frontend Frameworks such as React and Tailwind CSS.
> Fixed a `\s Syntax Warning` error
> Clicking the handle in the main page should redirect us to that bot page.
> Better CSS for `Back to Available Inventory` button.
> Removed the bot page html from the main.py and placed it in its own `.html` file.

- **Related Git Commit:** `feat(web):created individual pages for each bot username`

### [LOG-003] Feature / Task Name
- **Date:** 2026-7-30 - Yousef Babaki
- **Target Component:** `/bot/main.py`
- **Objective:** Copywriting & Messaging Overhaul For the Bot
- **Context Provided:** `[PROJECT_SPEC_bot.md`, `/bot/main.py`
- **System / Task Prompt:**
> [ROLE & PERSONA]
You are a Senior UX Copywriter and Telegram Bot Developer. Your goal is to conduct a complete Copywriting & Messaging Overhaul for a Telegram bot project.

[CONTEXT & INPUTS]
I will provide two files:
1. `project_spec.md` — Project context and specifications.
2. `main.py` — The core application containing bot strings and notification logic.

[OBJECTIVE & TONE GUIDE]
- Strip AI Fluff & Corporate Jargon: Ban bloated marketing phrases like "digital asset," "premium offering," "unrivaled opportunity," or excessive corporate speak.
- Punchy & Direct Copy: Rewrite messages to be concise, transparent, and direct (e.g., "Telegram Bot Username For Sale. That’s it!").
- Frictionless Sales Flow: Ensure a consistent, grounded tone across the end-to-end user journey (Bid Submission -> Seller Alert -> Negotiation -> Deal Close).

[CRITICAL CONSTRAINTS]
1. Database Variables Must Remain Intact: Never remove, rename, or drop dynamic database placeholders (e.g., `{username}`, `{bid_amount}`, `{seller_id}`). They must be preserved within the rewritten text.
2. Exact Location Reporting: For every message reviewed, state the exact function name and line number(s) in `main.py` where the string resides.
3. Interactive One-By-One Execution: DO NOT rewrite everything in a single response. We will review and refine messages sequentially, one by one.

[STEP-BY-STEP WORKFLOW]
1. Initial Scan: Briefly outline the sequential message flow mapped from `main.py` (from initial listing to final transaction).
2. First Target String: Present Message #1 only with:
   - Location: Function name & Line number(s).
   - Current Code & Text: The raw text with placeholders.
   - Proposed Rewrites: 2-3 direct, zero-fluff alternatives.
3. User Lock-In: Wait for my explicit approval or manual refinement of Message #1 before proceeding to Message #2.

Confirm you understand this workflow, and I will upload `project_spec.md` and `main.py`.

- **AI Raw Output Summary:** The complete sequence mapped out from main.py. We’ll strip the corporate bloat out of every step to create a frictionless, high-converting flow.
- **Human Refinements (The "Brakes"):** Chose from the suggested text and made minor refinements if needed.
- **Related Git Commit:** `feat(bot): Copywriting & Messaging Overhaul Fix.`


### [LOG-004] Feature / Task Name
- **Date:** 2026-8-30 - Yousef Babaki
- **Target Component:** `bot/main.py`
- **Objective:** All functions and etc. live inside one long `main.py` file, Distribute these components into logical `.py` files (e.g., `config.py`, `utils.py`, `handlers/`, etc.) that are imported by `main.py`
- **Context Provided:** `PROJECT_SPEC.md`, `main.py`
- **System / Task Prompt:**
> [ROLE & PERSONA]
You are a Senior Python Architect specializing in clean code, software modularization, and safe refactoring practices. Your objective is to guide me through breaking down this single monolithic `main.py` file into clean, manageable, multi-file modules without introducing bugs or breaking functionality.

[CONTEXT & OBJECTIVE]
- Current State: All functions, business calculations, database logic, configuration, and event/request handlers live inside one long `main.py` file.
- Objective: Distribute these components into logical `.py` files (e.g., `config.py`, `utils.py`, `handlers/`, etc.) that are imported by `main.py`.
- Critical Requirement: The application currently works properly. You must ensure zero breaking changes, maintain variable scopes, and prevent circular import issues.

[REFACTORING CONSTRAINTS]
1. Zero Breaking Changes: Do not rewrite core logic or change variable/function signatures unless strictly necessary for importing.
2. Avoid Circular Imports: Carefully group dependencies so modules import cleanly without cyclic references.
3. Modular Separation of Concerns: Group code logically based on function (Configuration -> Database/Data Models -> Helper/Calculations -> Handlers/Routes -> App Initialization).
4. Step-by-Step Execution: Do NOT output all refactored code blocks at once. Proceed incrementally, module by module.

[REQUIRED RESPONSE WORKFLOW]
1. Proposed Project Directory Tree: Map out the recommended folder and file layout (e.g., showing where each category of code will live).
2. Step-by-Step Refactoring Plan: Outline the extraction order (from lowest-dependency modules like config/utils to higher-dependency modules like handlers).
3. Step 1 Instructions: Present ONLY the first module to create. For this step, specify:
   - Target File Path: (e.g., `config.py` or `utils/helpers.py`)
   - Code to Extract: Exact functions, classes, or variables to move from `main.py`.
   - Import Statements: The exact `import` statements required in both the new file and back in `main.py`.
   - Verification Check: A quick check to confirm the app still runs before moving to Step 2.

Acknowledge that you understand these instructions, and then start.

- **AI Raw Output Summary:** A refactoring architecture and step-by-step roadmap for modularizing the codebase without breaking existing functionality or creating circular dependencies
- **Human Refinements (The "Brakes"):** Fixed wrong name imports and and Fixed Router Order in `handlers/__init__.py`
- **Related Git Commit:** `feat(bot): Breaking main.py file into multiple files for easier management.`