import sqlite3

DB_NAME = "bids.db"


def init_db() -> None:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Your existing bids table creation stays exactly the same
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
    # NEW: Chat History Table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_username TEXT,
            buyer_chat_id INTEGER,
            sender_role TEXT, -- 'buyer' or 'admin'
            message_text TEXT,
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


def get_user_bid(buyer_chat_id: int):
    """Returns the most recent bid for a user."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # We select timestamp here now
    cursor.execute('''
        SELECT bid_amount, contact_info, timestamp 
        FROM bids 
        WHERE buyer_chat_id = ? 
        ORDER BY timestamp DESC LIMIT 1
    ''', (buyer_chat_id,))
    
    result = cursor.fetchone()
    conn.close()
    return result

# for the chat_history.db
def save_chat_message(bot_username: str, buyer_chat_id: int, sender_role: str, message_text: str) -> None:
    """Saves a message to the chat history."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO chat_history (bot_username, buyer_chat_id, sender_role, message_text)
        VALUES (?, ?, ?, ?)
        """, (bot_username, buyer_chat_id, sender_role, message_text)
    )
    conn.commit()
    conn.close()

def get_chat_history(bot_username: str, buyer_chat_id: int, limit: int = 10) -> list:
    """Fetches history, specifically ignoring invisible system unlock tags."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT sender_role, message_text, timestamp 
        FROM (
            SELECT sender_role, message_text, timestamp 
            FROM chat_history 
            WHERE bot_username = ? AND buyer_chat_id = ? AND sender_role != 'system_unlock'
            ORDER BY timestamp DESC LIMIT ?
        ) ORDER BY timestamp ASC
        """, (bot_username, buyer_chat_id, limit)
    )
    result = cursor.fetchall()
    conn.close()
    return result

def is_bid_locked(bot_username: str, buyer_chat_id: int) -> bool:
    """Checks if the last action in the DB was an admin reply (Locked)."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT sender_role 
        FROM chat_history 
        WHERE bot_username = ? AND buyer_chat_id = ? 
          AND sender_role IN ('admin', 'system_unlock')
        ORDER BY timestamp DESC LIMIT 1
        """, (bot_username, buyer_chat_id)
    )
    result = cursor.fetchone()
    conn.close()
    return bool(result and result[0] == 'admin')

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
    return f"@{res[0]}" if res and res[0] else f"ID {buyer_chat_id}"

def unlock_bid(bot_username: str, buyer_chat_id: int) -> None:
    """Silently inserts a system marker to unlock the bid without deleting history."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO chat_history (bot_username, buyer_chat_id, sender_role, message_text)
        VALUES (?, ?, ?, ?)
        """, (bot_username, buyer_chat_id, "system_unlock", "Offer unlocked.")
    )
    conn.commit()
    conn.close()