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
    conn.commit()
    conn.close()


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