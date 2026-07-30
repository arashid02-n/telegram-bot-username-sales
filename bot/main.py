import asyncio
import logging
import os
import sys

import re
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)

from dotenv import load_dotenv

from aiogram.filters import BaseFilter
from aiogram.exceptions import TelegramNetworkError, TelegramBadRequest
from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramNetworkError
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from aiogram.types import BotCommand
from aiogram.filters import Command

from database import init_db, save_or_update_bid, get_user_bid, get_buyer_username, get_buyer_offer
from database import (
    start_negotiation, get_active_topic_for_buyer, 
    get_buyer_for_topic, close_negotiation
)

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GROUP_CHAT_ID_RAW = os.getenv("GROUP_CHAT_ID", "")
# Handle standard IDs and Group IDs (which start with '-')
if GROUP_CHAT_ID_RAW.lstrip('-').isdigit():
    GROUP_CHAT_ID = int(GROUP_CHAT_ID_RAW)
else:
    GROUP_CHAT_ID = None
BOT_TOKENS_RAW = os.getenv("BOT_TOKENS", "")

PORTFOLIO_IDS = []

router = Router()

class BidStates(StatesGroup):
    waiting_for_bid = State()
    waiting_for_contact = State()


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


async def finalize_and_notify(bot, user, bid_amount, contact_info, edit_msg_id=None):
    bot_user = await bot.get_me()
    buyer_username = user.username or "N/A"
    
    # 1. Update/Save to Database
    save_or_update_bid(
        bot_username=bot_user.username,
        buyer_chat_id=user.id,
        buyer_username=buyer_username,
        bid_amount=bid_amount,
        contact_info=contact_info,
    )

    # Smart Formatting for Admin Notification
    is_email = re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", contact_info)
    clean_phone = re.sub(r"[\s\-\(\)\+]", "", contact_info)
    is_phone = clean_phone.isdigit() and 7 <= len(clean_phone) <= 15
    
    if is_email:
        # Clickable mailto: link + tap-to-copy code block
        formatted_contact = f"<a href='mailto:{contact_info}'>✉️ Email User</a> | (Copy: <code>{contact_info}</code>)"
    elif is_phone:
        # Clickable tel: link + tap-to-copy code block
        formatted_contact = f"<a href='tel:+{clean_phone}'>📞 Call User</a> | (Copy: <code>{contact_info}</code>)"
    else:
        # Standard tap-to-copy for anything else (like Telegram usernames)
        formatted_contact = f"<code>{contact_info}</code>"

    # 2. Notify Admins using your robust logging
    if GROUP_CHAT_ID:
        logger.info("Attempting to notify Group Chat: %s", GROUP_CHAT_ID)
        alert_text = (
            "📩 <b>New Offer Alert</b>\n\n"
            f"<b>Target:</b> @{bot_user.username}\n"
            f"<b>Amount:</b> ${bid_amount:,.2f}\n"
            f"<b>Buyer:</b> @{buyer_username} (<code>{user.id}</code>)\n"
            f"<b>Contact:</b> {formatted_contact}"
        )
        
        if edit_msg_id:
            try:
                await bot.edit_message_text(
                    chat_id=GROUP_CHAT_ID,
                    message_id=edit_msg_id,
                    text=alert_text,
                    reply_markup=admin_chat_keyboard(user.id)
                )
                return edit_msg_id
            except Exception as exc:
                logger.warning("Failed to edit existing admin alert, falling back to new message: %s", exc)
        
        try:
            msg = await bot.send_message(
                chat_id=GROUP_CHAT_ID, 
                text=alert_text, 
                reply_markup=admin_chat_keyboard(user.id)
            )
            logger.info("Successfully sent notification to group.")
            return msg.message_id
        except Exception as exc: 
            logger.warning("Failed to notify group %s: %s", GROUP_CHAT_ID, exc)
    else:
        logger.warning("No GROUP_CHAT_ID configured to receive notifications!")

class InLiveChatFilter(BaseFilter):
    """Checks if a user is currently locked in a LIVE_CHAT state."""
    async def __call__(self, message: Message) -> bool | dict:
        bot_username = (await message.bot.get_me()).username
        topic_id = get_active_topic_for_buyer(bot_username, message.from_user.id)
        if topic_id:
            return {"topic_id": topic_id} # Passes topic_id to the handler
        return False

@router.message(F.chat.type == "private", InLiveChatFilter())
async def buyer_to_admin_proxy(message: Message, topic_id: int) -> None:
    """Intercepts EVERYTHING from the buyer and copies it to the Admin Forum Topic."""
    try:
        await message.bot.copy_message(
            chat_id=GROUP_CHAT_ID,
            message_thread_id=topic_id,
            from_chat_id=message.from_user.id,
            message_id=message.message_id
        )
    except Exception as e:
        logger.error("Failed to proxy buyer message to forum topic: %s", e)

@router.message(F.chat.id == GROUP_CHAT_ID, F.message_thread_id)
async def admin_to_buyer_proxy(message: Message) -> None:
    """Listens to active Forum Topics and routes broker messages directly to the buyer's PM."""
    if message.from_user.is_bot:
        return # Ignore bot notifications

    bot_username = (await message.bot.get_me()).username
    buyer_chat_id = get_buyer_for_topic(bot_username, message.message_thread_id)

    if buyer_chat_id:
        try:
            await message.bot.copy_message(
                chat_id=buyer_chat_id,
                from_chat_id=GROUP_CHAT_ID,
                message_id=message.message_id
            )
        except Exception as e:
            logger.error("Failed to proxy admin message to buyer: %s", e)

@router.message(CommandStart(), F.chat.type == "private")
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    bot_username = (await message.bot.get_me()).username
    text = (
    f"🎯 <b>@{bot_username} is for sale.</b>\n\n"
    "This bot handles offers and negotiations directly.\n\n"
    "Use the menu below to place your bid or check your current status."
    )
    await message.answer(text, reply_markup=main_keyboard())

@router.message(Command("my_bid"), F.chat.type == "private")
async def cmd_my_bid(message: Message, state: FSMContext) -> None:
    await state.clear()
    bot_username = (await message.bot.get_me()).username
    past_bid = get_user_bid(bot_username, message.from_user.id)
    
    if past_bid:
        amount, contact, timestamp = past_bid
        text = (
            "🧾 <b>Your Current Offer</b>\n\n"
            f"💰 <b>Amount:</b> ${amount:,.2f}\n"
            f"📞 <b>Contact on file:</b> <code>{contact}</code>\n"
            f"📅 <b>Date:</b> {timestamp[:16]}\n\n"
            "Would you like to modify your offer?"
        )
        await message.answer(text, reply_markup=change_offer_keyboard(source="mybid"))
    else:
        await message.answer(
            "No active bid found. Tap <b>Make an Offer</b> to get started.", 
            reply_markup=main_keyboard(source="nobid")
        )

@router.message(Command("about"), F.chat.type == "private")
async def cmd_about(message: Message, state: FSMContext) -> None:
    await state.clear()
    bot_username = (await message.bot.get_me()).username
    
    text = (
        "ℹ️ <b>How It Works</b>\n\n"
        f"This bot is the dedicated sales channel for <b>@{bot_username}</b>.\n\n"
        "1. Submit your numeric USD offer.\n"
        "2. If your offer is reviewed, an admin will open a live chat here.\n"
        "3. Agree on terms and finalize the handle transfer securely."
    )
    
    await message.answer(text)

@router.message(Command("support"), F.chat.type == "private")
async def cmd_support(message: Message, state: FSMContext) -> None:
    """Provides contact info for the broker."""
    await state.clear()
    
    text = (
        "💬 <b>Contact Admin</b>\n\n"
        "Have a question or need assistance ?\n\n"
        "• <b>Telegram:</b> @josebbk\n"
        "• <b>Email:</b> yousefbbk29@gmail.com\n\n"
        "Include the target handle and your offer amount when reaching out so we can help you quickly."
    )
    await message.answer(text)

@router.callback_query(F.data.startswith("asset_info:"))
async def cb_asset_info(callback: CallbackQuery) -> None:
    source = callback.data.split(":")[1]
    bot_username = (await callback.bot.get_me()).username
    
    text = (
        "ℹ️ <b>Handle Information</b>\n\n"
        f"• <b>Username:</b> @{bot_username}\n"
        "• <b>Status:</b> Accepting Offers\n"
        "• <b>Transfer:</b> Direct Telegram Username Transfer\n\n"
        "Use the button below to submit your offer."
    )
    
    # 2. Build the keyboard dynamically
    buttons = []
    buttons.append([InlineKeyboardButton(text="💰 Make / Change Offer", callback_data="make_offer")])
    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data=f"back:{source}")])
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    try:
        await callback.message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest:
        pass
    await callback.answer()

@router.callback_query(F.data.startswith("back:"))
async def cb_back_routing(callback: CallbackQuery) -> None:
    source = callback.data.split(":")[1]
    bot_user = await callback.bot.get_me()
    
    if source == "start":
        text = (
            f"🎯 <b>@{bot_user.username} is for sale.</b>\n\n"
            "This bot handles offers and negotiations directly.\n\n"
            "Use the menu below to place your bid or check your current status."
        )
        markup = main_keyboard(source="start")
    elif source == "nobid":
        text = "No active bid found. Tap <b>Make an Offer</b> to get started."
        markup = main_keyboard(source="nobid")
    else:
        past_bid = get_user_bid(bot_user.username, callback.from_user.id)
        
        if not past_bid:
            text = f"Welcome! 🚀\n\nThe asset <b>@{bot_user.username}</b> is currently accepting offers."
            markup = main_keyboard(source="start")
        else:
            amount, contact, timestamp = past_bid
            
            if source == "mybid":
                text = (
                    "🧾 <b>Your Current Offer</b>\n\n"
                    f"💰 <b>Amount:</b> ${amount:,.2f}\n"
                    f"📞 <b>Contact on file:</b> <code>{contact}</code>\n"
                    f"📅 <b>Date:</b> {timestamp[:16]}\n\n"
                    "Would you like to modify your offer?"
                )
            elif source == "end_nego":
                text = (
                    "🔴 <b>Negotiation Closed</b>\n\n"
                    "The broker has ended this live session. We still have your offer on file:\n\n"
                    f"💰 <b>Amount:</b> ${amount:,.2f}\n"
                    f"📞 <b>Contact on file:</b> <code>{contact}</code>\n\n"
                    "Would you like to modify your offer?"
                )
            else: # catchall
                text = (
                    "👋 Welcome back!\n\n"
                    "We have your current offer on file:\n"
                    f"💰 <b>Amount:</b> ${amount:,.2f}\n"
                    f"📞 <b>Contact on file:</b> <code>{contact}</code>\n"
                    f"📅 <b>Date:</b> {timestamp[:16]}\n\n"
                    "Would you like to modify your offer?"
                )
            markup = change_offer_keyboard(source)

    try:
        await callback.message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest:
        pass
    await callback.answer()

@router.callback_query(F.data == "back_to_main")
async def cb_back_to_main(callback: CallbackQuery) -> None:
    text = (
    f"🎯 <b>@{bot_username} is for sale.</b>\n\n"
    "This bot handles offers and negotiations directly.\n\n"
    "Use the menu below to place your bid or check your current status."
    )
    try:
        await callback.message.edit_text(text, reply_markup=main_keyboard())
    except TelegramBadRequest:
        pass
    await callback.answer()

@router.callback_query(F.data == "make_offer")
async def cb_make_offer(callback: CallbackQuery, state: FSMContext) -> None:
    bot_username = (await callback.bot.get_me()).username
    await callback.message.answer("Enter your offer in USD (e.g., 750):")
    await state.set_state(BidStates.waiting_for_bid)
    await callback.answer()

@router.callback_query(F.data.startswith("admin_negotiate_"))
async def cb_start_negotiation(callback: CallbackQuery) -> None:
    buyer_chat_id = int(callback.data.split("_")[2])
    bot_username = (await callback.bot.get_me()).username
    buyer_name = get_buyer_username(buyer_chat_id)

    # Fetch and format the offer amount for the Topic Title
    raw_offer = get_buyer_offer(bot_username, buyer_chat_id)
    try:
        offer_str = f"${float(raw_offer):,.0f}"
    except (ValueError, TypeError):
        offer_str = f"${raw_offer}"
        
    topic_name = f"{offer_str} - {buyer_name} - @{bot_username}"

    try:
        # 1. Create Forum Topic with new naming convention
        topic = await callback.bot.create_forum_topic(
            chat_id=GROUP_CHAT_ID,
            name=topic_name
        )
        topic_id = topic.message_thread_id

        # 2. Save State to SQLite
        start_negotiation(bot_username, buyer_chat_id, topic_id)

        # 3. Remove the "Start Negotiation" button from the original alert
        await callback.message.edit_reply_markup(reply_markup=None)

        # 4. Alert the Buyer
        await callback.bot.send_message(
            chat_id=buyer_chat_id,
            text=f"🟢 <b>Live Chat Initiated</b>\n\nYou are in a direct chat with an admin regarding <b>@{bot_username}</b> ({offer_str}).\n\nAny message you type here will be sent straight to the broker.",
            reply_markup=ReplyKeyboardRemove()
        )

        # 5. Pin End Negotiation Button in Topic
        end_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ End Negotiation", callback_data=f"admin_endnego_{buyer_chat_id}")]
        ])
        
        pin_msg = await callback.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            message_thread_id=topic_id,
            text=f"🔴 <b>LIVE CHAT Initiated</b> — {buyer_name} (ID: <code>{buyer_chat_id}</code>)\n\nMessages typed in this topic are forwarded directly to the buyer's PM.",
            reply_markup=end_kb
        )
        
        await callback.bot.pin_chat_message(
            chat_id=GROUP_CHAT_ID,
            message_id=pin_msg.message_id
        )

        await callback.answer("Live Chat Topic Created & Locked!")
    except Exception as e:
        await callback.answer(f"Error creating topic: {e}", show_alert=True)
        logger.error("Failed to create topic: %s", e)

@router.callback_query(F.data.startswith("admin_endnego_"))
async def cb_end_negotiation(callback: CallbackQuery) -> None:
    buyer_chat_id = int(callback.data.split("_")[2])
    bot_username = (await callback.bot.get_me()).username

    # 1. Update SQLite Status
    close_negotiation(bot_username, buyer_chat_id)

    # 2. Close Forum Topic
    try:
        await callback.bot.close_forum_topic(
            chat_id=GROUP_CHAT_ID,
            message_thread_id=callback.message.message_thread_id
        )
    except Exception as e:
        logger.error("Failed to close forum topic: %s", e)

   # 3. Notify Buyer and Restore UI Menu
    await callback.bot.send_message(
        chat_id=buyer_chat_id,
        text="🔴 <b>Live Chat Ended</b>\n\nThe live chat has closed. Your offer remains on file. You can continue managing your offer using the menu below.",
        reply_markup=change_offer_keyboard(source="end_nego") # <-- Updated keyboard
    )

    await callback.answer("Topic closed. Buyer notified.")

@router.message(BidStates.waiting_for_bid, F.chat.type == "private")
async def process_bid_amount(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip().replace("$", "").replace(",", "")

    try:
        bid_amount = float(raw)
        if bid_amount < 0:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ Enter a valid number in USD (e.g. 750 or 12.50).")
        return

    bot_username = (await message.bot.get_me()).username
    past_bid = get_user_bid(bot_username, message.from_user.id)
    if past_bid:
        _, existing_contact, _ = past_bid
        contact_info = existing_contact if existing_contact else "Skipped (Telegram Only)"
    else:
        contact_info = "Skipped (Telegram Only)"

    # Save the returned message_id from the first alert
    alert_msg_id = await finalize_and_notify(message.bot, message.from_user, bid_amount, contact_info)

    text = (
        f"✅ <b>Offer Received: ${bid_amount:,.2f}</b>\n\n"
        "An admin has been notified.\n\n"
        "Your offer has been sent to the broker.\n\n"
        "<i>Optional: Reply with an email or phone number if you prefer contact outside Telegram.</i>"
    )
    
    # Store BOTH the bid amount and the alert message ID
    await state.update_data(bid_amount=bid_amount, alert_msg_id=alert_msg_id)
    await state.set_state(BidStates.waiting_for_contact)
    
    await message.answer(text, reply_markup=change_offer_keyboard(source="start"))

# 1. Catches the user typing an email or phone number
@router.message(BidStates.waiting_for_contact, F.chat.type == "private")
async def process_contact_text(message: Message, state: FSMContext) -> None:
    contact_info = message.text.strip()
    
    is_email = re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", contact_info)
    clean_phone = re.sub(r"[\s\-\(\)\+]", "", contact_info)
    is_phone = clean_phone.isdigit() and 7 <= len(clean_phone) <= 15

    if not is_email and not is_phone:
        await state.clear()
        if message.text.startswith("/"):
            return 
        await message.answer("✅ Offer active on Telegram. Use the menu below to navigate.")
        return

    data = await state.get_data()
    bid_amount = data.get("bid_amount")
    alert_msg_id = data.get("alert_msg_id") # Retrieve the ID
    
    # Pass the edit_msg_id to update the existing alert in place
    await finalize_and_notify(message.bot, message.from_user, bid_amount, contact_info, edit_msg_id=alert_msg_id)
    
    await message.answer("✅ <b>Contact info saved.</b> We'll reach out using this contact if needed.")
    await state.clear()


@router.callback_query(F.data == "asset_info_existing")
async def cb_asset_info_existing(callback: CallbackQuery) -> None:
    """Displays asset info with custom buttons for existing bidders."""
    text = (
        "ℹ️ <b>Username Value</b>\n\n"
        f"<b>@{bot_username}</b> is a short, memorable Telegram handle.\n\n"
        "Clean handles build trust, elevate brand identity, and retain long-term value across Telegram & TON ecosystem."
    )
    try:
        await callback.message.edit_text(text, reply_markup=asset_info_existing_keyboard())
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc):
            logger.error("Failed to edit asset info message: %s", exc)
    await callback.answer()

@router.callback_query(F.data == "back_to_existing")
async def cb_back_to_existing(callback: CallbackQuery) -> None:
    """Takes the existing bidder back to their custom bid preview instead of start."""
    # Add the bot_username fetch, then change the call:
    bot_username = (await callback.bot.get_me()).username
    past_bid = get_user_bid(bot_username, callback.from_user.id)
    if past_bid:
        amount, contact, timestamp = past_bid
        text = (
            "👋 Welcome back!\n\n"
            "We have your current offer on file:\n"
            f"💰 <b>Amount:</b> ${amount:,.2f}\n"
            f"📞 <b>Contact on file:</b> <code>{contact}</code>\n"
            f"📅 <b>Date:</b> {timestamp[:16]} (UTC)\n\n"
            "Would you like to modify your offer?"
        )
        try:
            await callback.message.edit_text(text, reply_markup=change_offer_keyboard())
        except TelegramBadRequest:
            pass
    else:
        # Fallback to main menu if no past bid is found
        text = (
            f"🎯 <b>@{bot_username} is for sale.</b>\n\n"
            "This bot handles offers and negotiations directly.\n\n"
            "Use the menu below to place your bid or check your current status."
        )
        try:
            await callback.message.edit_text(text, reply_markup=main_keyboard())
        except TelegramBadRequest:
            pass
    await callback.answer()

@router.callback_query(F.data.startswith("explore_ids"))
async def cb_explore_ids(callback: CallbackQuery) -> None:
    # Extracts the source tag, safely defaulting to "start" for old buttons
    source = callback.data.split(":")[1] if ":" in callback.data else "start"
    bot_user = await callback.bot.get_me()
    text = (
        "🌐 <b>Other Available Usernames</b>\n\n"
        "Browse our portfolio of usernames open for acquisition:"
    )
    try:
        await callback.message.edit_text(text, reply_markup=explore_ids_keyboard(bot_user.username, source))
    except TelegramBadRequest:
        pass
    await callback.answer()


async def setup_bot_commands(bot: Bot):
    """Pushes the command menu to the Telegram UI."""
    bot_commands = [
        BotCommand(command="start", description="Main Menu / Restart"),
        BotCommand(command="my_bid", description="View or Edit Offer"),
        BotCommand(command="about", description="Asset Information"),
        BotCommand(command="support", description="Contact Broker"),
    ]
    await bot.set_my_commands(bot_commands)

@router.message(F.chat.type == "private")
async def catch_all_messages(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is not None:
        return 

    bot_username = (await message.bot.get_me()).username
    past_bid = get_user_bid(bot_username, message.from_user.id)
    
    if past_bid:
        amount, contact, timestamp = past_bid
        text = (
            "👋 Welcome back!\n\n"
            "We have your current offer on file:\n"
            f"💰 <b>Amount:</b> ${amount:,.2f}\n"
            f"📞 <b>Contact on file:</b> <code>{contact}</code>\n"
            f"📅 <b>Date:</b> {timestamp[:16]}\n\n"
            "Would you like to modify your offer?"
        )
        await message.answer(text, reply_markup=change_offer_keyboard(source="catchall"))
    else:
        # Default start layout for users who haven't bid yet
        text = (
            f"🎯 <b>@{bot_username} is for sale.</b>\n\n"
            "This bot handles offers and negotiations directly.\n\n"
            "Use the menu below to place your bid or check your current status."
        )
        await message.answer(text, reply_markup=main_keyboard(source="start"))

async def run_bots() -> None:
    if not BOT_TOKENS_RAW:
        logger.error("BOT_TOKENS is not set in .env")
        sys.exit(1)

    # Normalize newlines into commas so it never trips over multiline formatting
    normalized_tokens = BOT_TOKENS_RAW.replace("\n", ",")
    
    tokens = []
    for item in normalized_tokens.split(","):
        # Strip inline comments (#), whitespace, and stray quotes
        clean_token = item.split("#")[0].strip().strip('"').strip("'")
        if clean_token:
            tokens.append(clean_token)

    if not tokens:
        logger.error("No valid bot tokens found in BOT_TOKENS")
        sys.exit(1)

    bots = [
        Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        for token in tokens
    ]

    # --- DYNAMIC PORTFOLIO GENERATION ---
    global PORTFOLIO_IDS
    PORTFOLIO_IDS.clear()
    logger.info("Fetching bot usernames for the portfolio...")
    for bot in bots:
        try:
            me = await bot.get_me()
            PORTFOLIO_IDS.append(f"@{me.username}")
            logger.info("Added @%s to portfolio.", me.username)
        except Exception as exc:
            logger.error("Could not fetch bot info for a token: %s", exc)
    # ------------------------------------

    # --- WEBHOOK CLEANUP & COMMANDS ---
    logger.info("Cleaning up any active webhooks...")
    for bot in bots:
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            # await setup_bot_commands(bot) # <-- If you have your command menu setup here
            await setup_bot_commands(bot)
            logger.info("Successfully cleared webhook for bot.")
        except Exception as exc:
            logger.warning("Could not clear webhook: %s", exc)
    # ---------------------------------

    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    await dp.start_polling(*bots)


def main() -> None:
    init_db()
    try:
        asyncio.run(run_bots())
    except (TelegramNetworkError, ConnectionError, OSError) as exc:
        print("\n" + "=" * 70)
        print("  CONNECTION FAILED: Could not reach api.telegram.org")
        print("=" * 70)
        print(f"  Details: {exc}")
        print(
            "\n  Telegram's API appears to be blocked by your local network/ISP.\n"
            "  Please make sure your system-wide VPN is ACTIVE and running in\n"
            "  'TUN Mode' or 'Global Mode' (not just browser/proxy mode),\n"
            "  then restart this script.\n"
        )
        print("=" * 70 + "\n")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nBot stopped by user.")


if __name__ == "__main__":
    main()