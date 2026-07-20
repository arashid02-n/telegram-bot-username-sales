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

from database import init_db, save_or_update_bid, get_user_bid, save_chat_message, get_chat_history, is_bid_locked
from database import get_buyer_username, unlock_bid
from database import get_buyer_offer

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ADMIN_CHAT_IDS_RAW = os.getenv("ADMIN_CHAT_IDS", "")
ADMIN_CHAT_IDS = []
for x in ADMIN_CHAT_IDS_RAW.split(","):
    clean_id = x.strip()
    if clean_id.isdigit() or (clean_id.startswith("-") and clean_id[1:].isdigit()):
        ADMIN_CHAT_IDS.append(int(clean_id))
BOT_TOKENS_RAW = os.getenv("BOT_TOKENS", "")

PORTFOLIO_IDS = []

router = Router()

class ChatStates(StatesGroup):
    waiting_for_buyer_reply = State()
    waiting_for_admin_reply = State()

class BidStates(StatesGroup):
    waiting_for_bid = State()
    waiting_for_contact = State()


def main_keyboard(source: str = "start") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💵 Make an Offer", callback_data="make_offer")],
            [InlineKeyboardButton(text="🌐 Explore Other IDs", callback_data=f"explore_ids:{source}")],
            [InlineKeyboardButton(text="ℹ️ Asset Info", callback_data=f"asset_info:{source}")],
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
                InlineKeyboardButton(text=f"🔹 {asset} (Premium)", url=f"https://t.me/{clean_username}")
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
            [InlineKeyboardButton(text="🌐 Explore Other IDs", callback_data=f"explore_ids:{source}")],
            [InlineKeyboardButton(text="ℹ️ Asset Info", callback_data=f"asset_info:{source}")]
        ]
    )

def asset_info_existing_keyboard(source: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Change Offer", callback_data="make_offer")],
            [InlineKeyboardButton(text="🔙 Back", callback_data=f"back:{source}")]
        ]
    )

def admin_chat_keyboard(buyer_chat_id: int, show_reply: bool = True, show_history: bool = True, unlock_state: str = "none") -> InlineKeyboardMarkup:
    buttons = []
    if show_reply:
        buttons.append([InlineKeyboardButton(text="💬 Reply to Buyer", callback_data=f"admin_reply_{buyer_chat_id}")])
    if show_history:
        buttons.append([InlineKeyboardButton(text="📜 View Chat History", callback_data=f"admin_history_{buyer_chat_id}")])
    
    # The new Unlock Toggle System
    if unlock_state == "show":
        buttons.append([InlineKeyboardButton(text="🔓 Lift Offer Lock", callback_data=f"admin_unlock_{buyer_chat_id}")])
    elif unlock_state == "confirm":
        buttons.append([
            InlineKeyboardButton(text="⚠️ Confirm Unlock", callback_data=f"admin_unlkconf_{buyer_chat_id}"),
            InlineKeyboardButton(text="❌ Cancel", callback_data=f"admin_unlkcanc_{buyer_chat_id}")
        ])
        
    return InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None

def buyer_chat_keyboard(show_reply: bool = True, show_history: bool = True) -> InlineKeyboardMarkup:
    buttons = []
    if show_reply:
        buttons.append([InlineKeyboardButton(text="💬 Reply to Broker", callback_data="buyer_reply")])
    if show_history:
        buttons.append([InlineKeyboardButton(text="📜 View Chat History", callback_data="buyer_history")])
    return InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None

def get_current_keyboard_state(reply_markup) -> tuple[bool, bool, str]:
    """Reads the current message to see which buttons and unlock states are visible."""
    has_reply = False
    has_history = False
    unlock_state = "none"
    if reply_markup and reply_markup.inline_keyboard:
        for row in reply_markup.inline_keyboard:
            for btn in row:
                if btn.callback_data:
                    if "reply" in btn.callback_data:
                        has_reply = True
                    if "history" in btn.callback_data:
                        has_history = True
                    if "admin_unlock_" in btn.callback_data:
                        unlock_state = "show"
                    if "admin_unlkconf_" in btn.callback_data:
                        unlock_state = "confirm"
    return has_reply, has_history, unlock_state

def locked_offer_keyboard(source: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🌐 Explore Other IDs", callback_data=f"explore_ids:{source}")],
            [InlineKeyboardButton(text="ℹ️ Asset Info", callback_data=f"asset_info:{source}")]
        ]
    )

async def finalize_and_notify(bot, user, bid_amount, contact_info):
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
    if ADMIN_CHAT_IDS:
        logger.info("Attempting to notify Admin IDs: %s", ADMIN_CHAT_IDS)
        alert_text = (
            "📩 <b>New/Updated Bid Received</b>\n\n"
            f"<b>Bot:</b> @{bot_user.username}\n"
            f"<b>Buyer:</b> @{buyer_username} (ID: <code>{user.id}</code>)\n"
            f"<b>Bid:</b> ${bid_amount:,.2f}\n"
            f"<b>Contact:</b> {formatted_contact}"
        )
        # (Inside finalize_and_notify)
        for admin_id in ADMIN_CHAT_IDS:
            try:
                # ADDED: reply_markup=admin_chat_keyboard(user.id)
                await bot.send_message(chat_id=admin_id, text=alert_text, reply_markup=admin_chat_keyboard(user.id, show_history=False))
                logger.info("Successfully sent notification to admin: %s", admin_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to notify admin %s: %s", admin_id, exc)
    else:
        logger.warning("No Admin IDs configured to receive notifications!")

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    bot_username = (await message.bot.get_me()).username
    text = (
            f"🎯 <b>Digital Asset Acquisition & Brokerage</b>\n\n"
            f"Asset: <b>@{bot_username}</b>\n\n"
            "This bot and identity are managed by an independent third-party brokerage service contracted exclusively to facilitate the secure sale of this asset.\n\n"
            "Submit your acquisition proposal or review your current standing below."
        )
    await message.answer(text, reply_markup=main_keyboard())

@router.message(Command("my_bid"))
async def cmd_my_bid(message: Message, state: FSMContext) -> None:
    await state.clear()
    bot_username = (await message.bot.get_me()).username
    past_bid = get_user_bid(message.from_user.id)
    
    if past_bid:
        amount, contact, timestamp = past_bid
        if is_bid_locked(bot_username, message.from_user.id):
            text = (
                "🧾 <b>Your Current Offer (🔒 Locked)</b>\n\n"
                f"💰 <b>Amount:</b> ${amount:,.2f}\n"
                f"📞 <b>Contact on file:</b> <code>{contact}</code>\n"
                f"📅 <b>Date:</b> {timestamp[:16]}\n\n"
                "Your offer is currently under active negotiation."
            )
            await message.answer(text, reply_markup=locked_offer_keyboard(source="mybid"))
        else:
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
            "You haven't made an offer yet! 🚀\n\nTap below to get started.", 
            reply_markup=main_keyboard(source="nobid")
        )

@router.message(Command("about"))
async def cmd_about(message: Message, state: FSMContext) -> None:
    await state.clear()
    bot_username = (await message.bot.get_me()).username
    
    text = (
        "🤖 <b>About This Broker Bot</b>\n\n"
        f"This bot facilitates the secure acquisition of the <b>@{bot_username}</b> identity.\n\n"
        "• <b>Secure:</b> All negotiations are confidential.\n"
        "• <b>Direct:</b> You chat directly with the asset broker.\n"
        "• <b>Professional:</b> Streamlined offer and counter-offer process.\n\n"
        "Use /start to view the main menu, or /my_bid to check your current status."
    )
    
    await message.answer(text)

@router.message(Command("support"))
async def cmd_support(message: Message, state: FSMContext) -> None:
    """Provides contact info for the broker."""
    await state.clear()
    
    text = (
        "🎧 <b>Broker Support</b>\n\n"
        "Need assistance or prefer to negotiate directly? "
        "Our broker is available to answer your questions.\n\n"
        "✉️ <b>Email:</b> yousefbbk29@gmail.com\n"
        "💬 <b>Telegram:</b> @Josebbk\n\n"
        "<i>Please include your Telegram ID or current offer amount in your message so we can pull up your file.</i>"
    )
    await message.answer(text)

@router.callback_query(F.data.startswith("asset_info:"))
async def cb_asset_info(callback: CallbackQuery) -> None:
    source = callback.data.split(":")[1]
    bot_username = (await callback.bot.get_me()).username
    
    # 1. Check if the buyer is currently locked
    locked = is_bid_locked(bot_username, callback.from_user.id)
    
    text = (
        "ℹ️ <b>Asset Information</b>\n\n"
        f"<b>Username:</b> @{bot_username}\n"
        "<b>Status:</b> Accepting Offers\n"
        "<b>Description:</b> Premium Telegram Identity.\n\n"
        "Securely acquire this high-value asset via our premium brokerage platform."
    )
    
    # 2. Build the keyboard dynamically
    buttons = []
    if not locked:
        # ONLY show this button if they are NOT locked. 
        # (Change "make_offer" if your bot uses a different callback to start bids)
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
            f"🎯 <b>Digital Asset Escrow & Acquisition</b>\n\n"
            f"Asset: <b>@{bot_user.username}</b>\n\n"
            "This identity is managed under formal brokerage protocol. "
            "Submit your acquisition proposal below or review your current standing."
        )
        markup = main_keyboard(source="start")
    elif source == "nobid":
        text = "You haven't made an offer yet! 🚀\n\nTap below to get started."
        markup = main_keyboard(source="nobid")
    else:
        past_bid = get_user_bid(callback.from_user.id)
        if not past_bid:
            text = f"Welcome! 🚀\n\nThe asset <b>@{bot_user.username}</b> is currently accepting offers."
            markup = main_keyboard(source="start")
        else:
            amount, contact, timestamp = past_bid
            locked = is_bid_locked(bot_user.username, callback.from_user.id)
            
            if locked:
                if source == "mybid":
                    text = (
                        "🧾 <b>Your Current Offer (🔒 Locked)</b>\n\n"
                        f"💰 <b>Amount:</b> ${amount:,.2f}\n"
                        f"📞 <b>Contact on file:</b> <code>{contact}</code>\n"
                        f"📅 <b>Date:</b> {timestamp[:16]}\n\n"
                        "Your offer is currently under active negotiation."
                    )
                else: # catchall
                    text = (
                        "🔒 <b>Offer Locked</b>\n\n"
                        "Your offer is currently under active negotiation with our broker. "
                        "To send a message, please use the 'Reply to Broker' button attached to the chat history."
                    )
                markup = locked_offer_keyboard(source)
            else:
                if source == "mybid":
                    text = (
                        "🧾 <b>Your Current Offer</b>\n\n"
                        f"💰 <b>Amount:</b> ${amount:,.2f}\n"
                        f"📞 <b>Contact on file:</b> <code>{contact}</code>\n"
                        f"📅 <b>Date:</b> {timestamp[:16]}\n\n"
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
            f"🎯 <b>Digital Asset Acquisition & Brokerage</b>\n\n"
            f"Asset: <b>@{bot_username}</b>\n\n"
            "This bot and identity are managed by an independent third-party brokerage service contracted exclusively to facilitate the secure sale of this asset.\n\n"
            "Submit your acquisition proposal or review your current standing below."
        )
    try:
        await callback.message.edit_text(text, reply_markup=main_keyboard())
    except TelegramBadRequest:
        pass
    await callback.answer()

@router.callback_query(F.data == "make_offer")
async def cb_make_offer(callback: CallbackQuery, state: FSMContext) -> None:
    bot_username = (await callback.bot.get_me()).username
    
    # 🔒 BID LOCK CHECK
    if is_bid_locked(bot_username, callback.from_user.id):
        await callback.message.answer(
            "🔒 <b>Offer Locked</b>\n\n"
            "Your offer is currently under active negotiation with our broker. "
            "To discuss adjusting your offer, please reply directly in the chat."
        )
        await callback.answer()
        return

    await callback.message.answer("Please type your offer as a numerical amount in USD (e.g. 750).")
    await state.set_state(BidStates.waiting_for_bid)
    await callback.answer()

@router.message(BidStates.waiting_for_bid)
async def process_bid_amount(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip().replace("$", "").replace(",", "")

    # 1. Try to convert the input to a float instead of using .isdigit()
    try:
        bid_amount = float(raw)
        if bid_amount < 0:
            # Prevent negative bids
            raise ValueError
    except ValueError:
        await message.answer(
            "⚠️ Please enter a valid numeric amount (e.g. 750 or 12.50)."
        )
        return

    await state.update_data(bid_amount=bid_amount)
    
    # 2. Smart Contact Info Query
    past_bid = get_user_bid(message.from_user.id)
    
    if past_bid:
        _, existing_contact, _ = past_bid
        if not existing_contact or existing_contact == "Skipped (Telegram Only)":
            text = (
                "Great, got your offer! 🎯\n\n"
                "You haven't provided contact info yet.\n"
                "If you would prefer faster contact, please share your\n<b>cell phone number</b>\nOR\n<b>email address</b>.\n\n"
                "<i>(Otherwise, just press the Skip button below.)</i>"
            )
        else:
            text = (
                "Great, got your offer! 🎯\n\n"
                f"Your current contact info is:\n<code>{existing_contact}</code>\n\n"
                "If you want to replace this info, please type your new email or phone number.\n"
                "Otherwise, press the 'Skip' button to keep your existing contact info."
            )
    else:
        text = (
            "Great, got your offer! 🎯\n\n"
            "Our broker will reach out to you using your Telegram ID.\n"
            "If you would prefer faster contact, please share your\n<b>cell phone number</b>\nOR\n<b>email address</b>.\n\n"
            "<i>(Otherwise, just press the Skip button below.)</i>"
        )
        
    await message.answer(text, reply_markup=skip_inline_keyboard())
    await state.set_state(BidStates.waiting_for_contact)


# 1. Catches the user typing an email or phone number
@router.message(BidStates.waiting_for_contact)
async def process_contact_text(message: Message, state: FSMContext) -> None:
    contact_info = message.text.strip()
    
    # Validation
    is_email = re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", contact_info)
    clean_phone = re.sub(r"[\s\-\(\)\+]", "", contact_info)
    is_phone = clean_phone.isdigit() and 7 <= len(clean_phone) <= 15

    if not is_email and not is_phone:
        await message.answer(
            "⚠️ That doesn't look like a valid email or phone number.\n\n"
            "Please enter a valid format, or press '⏭️ Skip'.",
            reply_markup=skip_inline_keyboard()
        )
        return

    data = await state.get_data()
    await finalize_and_notify(message.bot, message.from_user, data.get("bid_amount"), contact_info)
    
    await message.answer("✅ Thank you! Your offer has been recorded and forwarded to the broker.")
    await state.clear()

# 2. Catches the user pressing the Inline "Skip" button
@router.callback_query(BidStates.waiting_for_contact, F.data == "skip_contact")
async def process_contact_skip(callback: CallbackQuery, state: FSMContext) -> None:
    # Remove the skip button so they can't click it twice
    await callback.message.edit_reply_markup(reply_markup=None) 
    
    data = await state.get_data()
    
    # Fetch past bid to see if they already have valid contact details
    past_bid = get_user_bid(callback.from_user.id)
    if past_bid:
        _, existing_contact, _ = past_bid
        # Keep existing contact details if found, otherwise default to Skipped
        contact_info = existing_contact if existing_contact else "Skipped (Telegram Only)"
    else:
        contact_info = "Skipped (Telegram Only)"
        
    await finalize_and_notify(callback.bot, callback.from_user, data.get("bid_amount"), contact_info)
    
    await callback.message.answer("✅ Thank you! Your offer has been recorded and forwarded to the broker.")
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "asset_info_existing")
async def cb_asset_info_existing(callback: CallbackQuery) -> None:
    """Displays asset info with custom buttons for existing bidders."""
    text = (
        "ℹ️ <b>Why This Asset Matters</b>\n\n"
        "In the Web3 era, a premium Telegram/TON identity is more than a name — "
        "it's a scarce, verifiable digital credential. Short, memorable identifiers "
        "function like premium real estate: they signal legitimacy, are instantly "
        "recognizable, and hold resale value as adoption of decentralized identity "
        "grows.\n\n"
        "Owning one means owning a piece of digital infrastructure that becomes "
        "harder to acquire over time, not easier."
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
    past_bid = get_user_bid(callback.from_user.id)
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
            f"🎯 <b>Digital Asset Acquisition & Brokerage</b>\n\n"
            f"Asset: <b>@{bot_username}</b>\n\n"
            "This bot and identity are managed by an independent third-party brokerage service contracted exclusively to facilitate the secure sale of this asset.\n\n"
            "Submit your acquisition proposal or review your current standing below."
        )
        try:
            await callback.message.edit_text(text, reply_markup=main_keyboard())
        except TelegramBadRequest:
            pass
    await callback.answer()

# --- NEGOTIATION ENGINE HANDLERS ---

def format_history_text(history, is_admin: bool = False) -> str:
    """Formats chat history top-to-bottom with visual distinction."""
    if not history:
        return "📭 <i>No messages recorded yet.</i>"
    
    lines = []
    # history is fetched DESC (newest first) by SQL, but get_chat_history 
    # should ideally return it ASC (oldest first) for top-to-bottom reading.
    for role, text, ts in history:
        time_str = ts[11:16] # Extract HH:MM
        
        if role == 'admin':
            name = "💼 <b>Broker Support</b>" if not is_admin else "💼 <b>You (Broker)</b>"
            # Using blockquotes to visually separate the admin's text
            lines.append(f"{name} <i>({time_str})</i>:\n<blockquote>{text}</blockquote>")
        else:
            name = "👤 <b>Buyer</b>" if is_admin else "👤 <b>You</b>"
            # Standard text for the buyer
            lines.append(f"{name} <i>({time_str})</i>:\n{text}")
            
    full_text = "\n\n".join(lines)
    
    # 🛡️ SAFETY CHECK: Telegram 4096 character limit safeguard
    # Safely drops older lines instead of raw-slicing strings to protect HTML tags
    if len(full_text) > 3800:
        notice = "<i>[Earlier messages omitted due to length...]</i>\n\n"
        while len(lines) > 1 and len(notice + "\n\n".join(lines)) > 3800:
            lines.pop(0) # Remove the oldest message
        full_text = notice + "\n\n".join(lines)
        
    return full_text


# 1. Admin presses "Reply to Buyer"
@router.callback_query(F.data.startswith("admin_reply_"))
async def cb_admin_initiate_reply(callback: CallbackQuery, state: FSMContext) -> None:
    buyer_chat_id = int(callback.data.split("_")[2])
    
    _, has_history, unlock_state = get_current_keyboard_state(callback.message.reply_markup)
    try:
        # Removes the reply button but keeps history and unlock button visible
        await callback.message.edit_reply_markup(reply_markup=admin_chat_keyboard(buyer_chat_id, show_reply=False, show_history=has_history, unlock_state=unlock_state))
    except TelegramBadRequest:
        pass

    await state.update_data(target_buyer_id=buyer_chat_id)
    await state.set_state(ChatStates.waiting_for_admin_reply)
    
    text = (
        f"📝 <b>Broker Communication Channel</b> (Buyer ID: <code>{buyer_chat_id}</code>)\n\n"
        "⚠️ Please send your entire response in a single message. "
        "This secure session will close automatically upon transmission."
    )
    await callback.message.answer(text)
    await callback.answer()

# 2. Admin types their message
@router.message(ChatStates.waiting_for_admin_reply)
async def process_admin_reply(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    buyer_chat_id = data.get("target_buyer_id")
    bot_username = (await message.bot.get_me()).username
    
    # Save to history & forward to buyer
    save_chat_message(bot_username, buyer_chat_id, "admin", message.text)
    
    formatted_msg = (
        "💼 <b>Latest message from Broker Support:</b>\n\n"
        f"{message.text}"
    )
    
    try:
        # We ensure chat_id and text are explicitly included here!
        await message.bot.send_message(
            chat_id=buyer_chat_id, 
            text=formatted_msg, 
            reply_markup=buyer_chat_keyboard(show_reply=True, show_history=True)
        )
        
        # Admin gets a plain confirmation with NO buttons. State ends.
        await message.answer("✅ <i>Message successfully delivered to the buyer. The reply session is now closed.</i>")
    except Exception as exc:
        await message.answer(f"❌ <i>Delivery failed: {exc}</i>")
        
    await state.clear()

# 3. Buyer presses "Reply to Broker"
@router.callback_query(F.data == "buyer_reply")
async def cb_buyer_initiate_reply(callback: CallbackQuery, state: FSMContext) -> None:
    # We add an extra '_' here to catch the 3rd variable (unlock_state)
    _, has_history, _ = get_current_keyboard_state(callback.message.reply_markup)
    try:
        await callback.message.edit_reply_markup(reply_markup=buyer_chat_keyboard(show_reply=False, show_history=has_history))
    except TelegramBadRequest:
        pass

    # Enter state and prompt for message
    await state.set_state(ChatStates.waiting_for_buyer_reply)
    
    text = (
        "📝 <b>Secure Broker Response</b>\n\n"
        "⚠️ Please send your response in a single message. "
        "This secure session will close automatically upon transmission."
    )
    await callback.message.answer(text)
    await callback.answer()

# 4. Buyer types their message
@router.message(ChatStates.waiting_for_buyer_reply)
async def process_buyer_reply(message: Message, state: FSMContext) -> None:
    bot_username = (await message.bot.get_me()).username
    buyer_chat_id = message.from_user.id
    
    # Save message to DB
    save_chat_message(bot_username, buyer_chat_id, "buyer", message.text)
    
    # Fetch their current offer
    offer_amount = get_buyer_offer(bot_username, buyer_chat_id)
    
    # Create a natively clickable username, or fallback to an HTML profile link
    if message.from_user.username:
        buyer_link = f"@{message.from_user.username}"
    else:
        buyer_link = f"<a href='tg://user?id={buyer_chat_id}'>{message.from_user.first_name}</a>"

    admin_alert = (
        f"💬 <b>Reply from Buyer:</b> {buyer_link}\n"
        f"💰 <b>Current Offer:</b> {offer_amount}\n\n"
        f"{message.text}"
    )

    if ADMIN_CHAT_IDS:
        for admin_id in ADMIN_CHAT_IDS:
            try:
                await message.bot.send_message(
                    chat_id=admin_id, 
                    text=admin_alert, 
                    reply_markup=admin_chat_keyboard(
                        buyer_chat_id, 
                        show_reply=True, 
                        show_history=True, 
                        unlock_state="show"
                    )
                )
            except Exception:
                pass

    await message.answer(
        "✅ <i>Your message has been delivered to the broker.</i>",
        reply_markup=buyer_chat_keyboard(show_reply=False, show_history=True)
    )
    await state.clear()

# 5. View Chat History Handlers
@router.callback_query(F.data.startswith("admin_history_"))
async def cb_admin_history(callback: CallbackQuery) -> None:
    buyer_chat_id = int(callback.data.split("_")[2])
    bot_username = (await callback.bot.get_me()).username
    history = get_chat_history(bot_username, buyer_chat_id)
    buyer_name = get_buyer_username(buyer_chat_id)
    
    # Unpack 3 variables now
    has_reply, _, unlock_state = get_current_keyboard_state(callback.message.reply_markup)
    
    # Username is dynamically injected into the title
    text = f"📜 <b>Chat History ({buyer_name})</b>\n\n" + format_history_text(history, is_admin=True)
    
    try:
        await callback.message.edit_text(text, reply_markup=admin_chat_keyboard(buyer_chat_id, show_reply=has_reply, show_history=False, unlock_state=unlock_state))
    except TelegramBadRequest:
        pass
    await callback.answer()

@router.callback_query(F.data == "buyer_history")
async def cb_buyer_history(callback: CallbackQuery) -> None:
    bot_username = (await callback.bot.get_me()).username
    history = get_chat_history(bot_username, callback.from_user.id)
    
    # We add an extra '_' here to catch the 3rd variable (unlock_state)
    has_reply, _, _ = get_current_keyboard_state(callback.message.reply_markup)
    
    text = "📜 <b>Chat History</b>\n\n" + format_history_text(history, is_admin=False)
    
    try:
        await callback.message.edit_text(text, reply_markup=buyer_chat_keyboard(show_reply=has_reply, show_history=False))
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("explore_ids"))
async def cb_explore_ids(callback: CallbackQuery) -> None:
    # Extracts the source tag, safely defaulting to "start" for old buttons
    source = callback.data.split(":")[1] if ":" in callback.data else "start"
    bot_user = await callback.bot.get_me()
    text = (
        "🌐 <b>Premium Brokerage Inventory</b>\n\n"
        "Explore our other high-value assets and premium TON infrastructure options below:"
    )
    try:
        await callback.message.edit_text(text, reply_markup=explore_ids_keyboard(bot_user.username, source))
    except TelegramBadRequest:
        pass
    await callback.answer()

@router.callback_query(F.data.startswith("admin_unlock_"))
async def cb_admin_unlock(callback: CallbackQuery) -> None:
    buyer_chat_id = int(callback.data.split("_")[2])
    has_reply, has_history, _ = get_current_keyboard_state(callback.message.reply_markup)
    
    try:
        # Switch button to "confirm" state
        await callback.message.edit_reply_markup(reply_markup=admin_chat_keyboard(buyer_chat_id, show_reply=has_reply, show_history=has_history, unlock_state="confirm"))
    except TelegramBadRequest:
        pass
    await callback.answer()

@router.callback_query(F.data.startswith("admin_unlkcanc_"))
async def cb_admin_unlock_cancel(callback: CallbackQuery) -> None:
    buyer_chat_id = int(callback.data.split("_")[2])
    has_reply, has_history, _ = get_current_keyboard_state(callback.message.reply_markup)
    
    try:
        # Switch button back to "show" state
        await callback.message.edit_reply_markup(reply_markup=admin_chat_keyboard(buyer_chat_id, show_reply=has_reply, show_history=has_history, unlock_state="show"))
    except TelegramBadRequest:
        pass
    await callback.answer()

@router.callback_query(F.data.startswith("admin_unlkconf_"))
async def cb_admin_unlock_confirm(callback: CallbackQuery) -> None:
    buyer_chat_id = int(callback.data.split("_")[2])
    bot_username = (await callback.bot.get_me()).username
    
    # 1. Unlock the bid in the DB
    unlock_bid(bot_username, buyer_chat_id)
    
    # 2. Update Admin message to remove the unlock buttons entirely
    has_reply, has_history, _ = get_current_keyboard_state(callback.message.reply_markup)
    try:
        await callback.message.edit_reply_markup(reply_markup=admin_chat_keyboard(buyer_chat_id, show_reply=has_reply, show_history=has_history, unlock_state="none"))
    except TelegramBadRequest:
        pass
    # Fetch their name from your DB helper function
    buyer_name = get_buyer_username(buyer_chat_id)
    
    # Send the admin a message with the clickable profile link
    await callback.message.answer(
        f"✅ <b>Offer Unlocked</b> for <a href='tg://user?id={buyer_chat_id}'>{buyer_name}</a>. "
        "They can now modify their bid or use bot menus normally."
    )
    
    # 3. Notify the Buyer that negotiations have concluded
    buyer_text = (
        "🔓 <b>Negotiations Concluded</b>\n\n"
        "The broker has unlocked your offer. You may now modify your bid amount or explore other assets."
    )
    try:
        await callback.bot.send_message(chat_id=buyer_chat_id, text=buyer_text, reply_markup=change_offer_keyboard(source="start"))
    except Exception:
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

@router.message()
async def catch_all_messages(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is not None:
        return 

    bot_username = (await message.bot.get_me()).username
    past_bid = get_user_bid(message.from_user.id)
    
    if past_bid:
        amount, contact, timestamp = past_bid
        
        # 🔒 IF LOCKED (Admin has replied): Show the locked notice
        if is_bid_locked(bot_username, message.from_user.id):
            text = (
                "🔒 <b>Active Negotiation Locked</b>\n\n"
                "Please use the <b>'💬 Reply to Broker'</b> button attached to your history log to send a message. "
                "If you have already submitted your response, please await the broker's review."
            )
            await message.answer(text, reply_markup=locked_offer_keyboard(source="catchall"))
            
        # 🔓 IF NOT LOCKED (Offer made, but admin hasn't replied yet): 
        # Do NOT forward random text. Just show normal menu so other functions work.
        else:
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
            f"Welcome! 🚀\n\n"
            f"The asset <b>@{bot_username}</b> is currently accepting offers.\n\n"
            f"Click below to make an offer or explore other options."
        )
        await message.answer(text, reply_markup=main_keyboard(source="start"))

async def run_bots() -> None:
    if not BOT_TOKENS_RAW:
        logger.error("BOT_TOKENS is not set in .env")
        sys.exit(1)

    tokens = [t.strip() for t in BOT_TOKENS_RAW.split(",") if t.strip()]
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