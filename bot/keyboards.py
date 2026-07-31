# All inline and reply keyboard constructors

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import PORTFOLIO_IDS

def main_keyboard(source: str = "start") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💵 Make an Offer", callback_data="make_offer")],
            [InlineKeyboardButton(text="🌐 Other Available Usernames", callback_data=f"explore_ids:{source}")],
            [InlineKeyboardButton(text="ℹ️ Username Info", callback_data=f"asset_info:{source}")],
        ]
    )

def asset_info_keyboard(source: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💵 Make an Offer", callback_data="make_offer")],
            [InlineKeyboardButton(text="🔙 Back", callback_data=f"back:{source}")]
        ]
    )

def explore_ids_keyboard(current_bot_username: str, source: str) -> InlineKeyboardMarkup:
    buttons = []
    for asset in PORTFOLIO_IDS:
        if asset.strip("@").lower() != current_bot_username.lower():
            clean_username = asset.strip("@")
            buttons.append([
                InlineKeyboardButton(text=f"🔹 {asset}", url=f"https://t.me/{clean_username}")
            ])
    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data=f"back:{source}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def skip_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏭️ Skip", callback_data="skip_contact")]
        ]
    )

def change_offer_keyboard(source: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Change Offer", callback_data="make_offer")],
            [InlineKeyboardButton(text="🌐 Other Available Usernames", callback_data=f"explore_ids:{source}")],
            [InlineKeyboardButton(text="ℹ️ Username Info", callback_data=f"asset_info:{source}")]
        ]
    )

def asset_info_existing_keyboard(source: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Change Offer", callback_data="make_offer")],
            [InlineKeyboardButton(text="🔙 Back", callback_data=f"back:{source}")]
        ]
    )

def admin_chat_keyboard(buyer_chat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Start Negotiation", callback_data=f"admin_negotiate_{buyer_chat_id}")]
    ])