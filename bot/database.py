import sqlite3

DB_NAME = "bids.db"


def init_db() -> None:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS bids (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_username TEXT,
            buyer_chat_id INTEGER,
            buyer_username TEXT,
            bid_amount REAL,
            contact_info TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    
    # NEW: Live Negotiations Table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS negotiations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_username TEXT,
            buyer_chat_id INTEGER,
            topic_id INTEGER,
            status TEXT DEFAULT 'LIVE_CHAT',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    
    conn.commit()
    conn.close()

# for the bids.db
def save_or_update_bid(
    bot_username: str,
    buyer_chat_id: int,
    buyer_username: str,
    bid_amount: float,
    contact_info: str,
) -> None:
    """Inserts a new bid or updates an existing one for the user."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Check if a bid already exists for this buyer on this specific bot
    cursor.execute(
        "SELECT id FROM bids WHERE buyer_chat_id = ? AND bot_username = ?",
        (buyer_chat_id, bot_username)
    )
    row = cursor.fetchone()
    
    if row:
        # Update existing record and update the timestamp
        cursor.execute(
            """
            UPDATE bids 
            SET buyer_username = ?, bid_amount = ?, contact_info = ?, timestamp = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (buyer_username or "N/A", bid_amount, contact_info, row[0])
        )
    else:
        # Insert a brand new record
        cursor.execute(
            """
            INSERT INTO bids (bot_username, buyer_chat_id, buyer_username, bid_amount, contact_info)
            VALUES (?, ?, ?, ?, ?)
            """,
            (bot_username, buyer_chat_id, buyer_username or "N/A", bid_amount, contact_info),
        )
    conn.commit()
    conn.close()


def get_user_bid(bot_username: str, buyer_chat_id: int):
    """Returns the most recent bid for a user on a SPECIFIC bot."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT bid_amount, contact_info, timestamp 
        FROM bids 
        WHERE bot_username = ? AND buyer_chat_id = ? 
        ORDER BY timestamp DESC LIMIT 1
    ''', (bot_username, buyer_chat_id))
    
    result = cursor.fetchone()
    conn.close()
    return result


def get_buyer_offer(bot_username: str, buyer_chat_id: int) -> str:
    """Fetches the latest offer amount from the buyer."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT bid_amount FROM bids WHERE bot_username = ? AND buyer_chat_id = ? ORDER BY id DESC LIMIT 1", 
        (bot_username, buyer_chat_id)
    )
    res = cursor.fetchone()
    conn.close()
    return str(res[0]) if res else "Unknown"

def get_buyer_username(buyer_chat_id: int) -> str:
    """Fetches the buyer's Telegram username for the chat log title."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT buyer_username FROM bids WHERE buyer_chat_id = ? ORDER BY id DESC LIMIT 1", (buyer_chat_id,))
    res = cursor.fetchone()
    conn.close()
    
    # If the user has a real username, format it with @
    if res and res[0] and res[0] != "N/A":
        return f"@{res[0]}"
    
    return f"ID {buyer_chat_id}"



def start_negotiation(bot_username: str, buyer_chat_id: int, topic_id: int) -> None:
    """Closes any old sessions for this buyer and opens a new live chat."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE negotiations SET status = 'CLOSED' WHERE bot_username = ? AND buyer_chat_id = ?",
        (bot_username, buyer_chat_id)
    )
    cursor.execute(
        """
        INSERT INTO negotiations (bot_username, buyer_chat_id, topic_id, status)
        VALUES (?, ?, ?, 'LIVE_CHAT')
        """, (bot_username, buyer_chat_id, topic_id)
    )
    conn.commit()
    conn.close()

def get_active_topic_for_buyer(bot_username: str, buyer_chat_id: int) -> int:
    """Returns the topic_id if the buyer is in a live chat, otherwise None."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT topic_id FROM negotiations WHERE bot_username = ? AND buyer_chat_id = ? AND status = 'LIVE_CHAT'",
        (bot_username, buyer_chat_id)
    )
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else None

def get_buyer_for_topic(bot_username: str, topic_id: int) -> int:
    """Returns the buyer_chat_id bound to a specific topic."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT buyer_chat_id FROM negotiations WHERE bot_username = ? AND topic_id = ? AND status = 'LIVE_CHAT'",
        (bot_username, topic_id)
    )
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else None

def close_negotiation(bot_username: str, buyer_chat_id: int) -> None:
    """Marks the negotiation as CLOSED."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE negotiations SET status = 'CLOSED' WHERE bot_username = ? AND buyer_chat_id = ?",
        (bot_username, buyer_chat_id)
    )
    conn.commit()
    conn.close()