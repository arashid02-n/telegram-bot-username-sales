# gram-bid-system
Multi-bot Telegram bidding system for managing offers and sales inquiries for premium Telegram usernames

# Bot structure:
.
├── database.py              # Existing database operations
├── config.py                # Environment variables, constants, and logging setup
├── states.py                # FSM state definitions
├── keyboards.py             # All inline and reply keyboard constructors
├── filters.py               # Custom aiogram filters (e.g., InLiveChatFilter)
├── services/
│   ├── __init__.py
│   └── notifications.py    # Admin notification formatting and dispatch logic
├── handlers/
│   ├── __init__.py          # Main router registry combining all sub-routers
│   ├── commands.py          # /start, /my_bid, /about, /support handlers
│   ├── bidding.py           # FSM bid submission and contact collection flow
│   ├── callbacks.py         # Navigation, back-routing, asset info, explore IDs
│   └── negotiation.py       # Live chat proxying and admin negotiation topic controls
├── main.py                  # Entry point, bot initialization, webhook cleanup, polling loop
└── .env                     # Environment configuration