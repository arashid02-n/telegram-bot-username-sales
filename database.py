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


def save_bid(
    bot_username: str,
    buyer_chat_id: int,
    buyer_username: str,
    bid_amount: float,
    contact_info: str,
) -> None:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO bids (bot_username, buyer_chat_id, buyer_username, bid_amount, contact_info)
        VALUES (?, ?, ?, ?, ?)
        """,
        (bot_username, buyer_chat_id, buyer_username or "N/A", bid_amount, contact_info),
    )
    conn.commit()
    conn.close()