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

from database import init_db, save_or_update_bid, get_user_bid

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

router = Router()


class BidStates(StatesGroup):
    waiting_for_bid = State()
    waiting_for_contact = State()


def main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💵 Make an Offer", callback_data="make_offer")],
            [InlineKeyboardButton(text="ℹ️ Asset Info", callback_data="asset_info")],
        ]
    )

def asset_info_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💵 Make an Offer", callback_data="make_offer")],
            [InlineKeyboardButton(text="🔙 Back", callback_data="back_to_main")]
        ]
    )

def skip_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏭️ Skip", callback_data="skip_contact")]
        ]
    )

def change_offer_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Change Offer", callback_data="make_offer")],
            # Points to the context-aware cb handler for existing users
            [InlineKeyboardButton(text="ℹ️ Asset Info", callback_data="asset_info_existing")]
        ]
    )

def asset_info_existing_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Change Offer", callback_data="make_offer")],
            [InlineKeyboardButton(text="🔙 Back", callback_data="back_to_existing")]
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
        for admin_id in ADMIN_CHAT_IDS:
            try:
                await bot.send_message(chat_id=admin_id, text=alert_text)
                logger.info("Successfully sent notification to admin: %s", admin_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to notify admin %s: %s", admin_id, exc)
    else:
        logger.warning("No Admin IDs configured to receive notifications!")

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    text = (
        "🔥 <b>Premium Asset For Sale</b> 🔥\n\n"
        "This is a rare, premium Telegram/TON identity — a high-value digital asset "
        "that carries real authority and recognition.\n\n"
        "💰 <b>Asking Price: $1,000 USD</b>\n\n"
        "🔒 <b>Privacy First:</b> Your contact details are strictly confidential. We utilize a client-side, serverless privacy tool to instantly redact sensitive information like emails and phone numbers before any external processing.\n\n"
        "Serious counter-offers are welcome. Tap below to make a bid or learn more."
    )
    await message.answer(text, reply_markup=main_keyboard())

@router.message(Command("my_bid"))
async def cmd_my_bid(message: Message, state: FSMContext) -> None:
    """Instantly pulls up their current bid status."""
    await state.clear()  # Crucial: Drops any pending FSM tasks
    
    past_bid = get_user_bid(message.from_user.id)
    if past_bid:
        amount, contact, timestamp = past_bid
        text = (
            "🧾 <b>Your Current Offer</b>\n\n"
            f"💰 <b>Amount:</b> ${amount:,.2f}\n"
            f"📞 <b>Contact on file:</b> <code>{contact}</code>\n"
            f"📅 <b>Date:</b> {timestamp[:16]} (UTC)\n\n"
            "Would you like to modify your offer?"
        )
        await message.answer(text, reply_markup=change_offer_keyboard())
    else:
        await message.answer(
            "You haven't made an offer yet! 🚀\n\nTap below to get started.", 
            reply_markup=main_keyboard()
        )

@router.message(Command("about"))
async def cmd_about(message: Message, state: FSMContext) -> None:
    """A shortcut to the asset information text."""
    await state.clear()
    
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
    
    # Dynamically serve the correct keyboard based on user history
    past_bid = get_user_bid(message.from_user.id)
    keyboard = asset_info_existing_keyboard() if past_bid else asset_info_keyboard()
    
    await message.answer(text, reply_markup=keyboard)

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

@router.callback_query(F.data == "asset_info")
async def cb_asset_info(callback: CallbackQuery) -> None:
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
        await callback.message.edit_text(text, reply_markup=asset_info_keyboard())
    except TelegramBadRequest as exc:
        # Ignore the error if the user just double-clicked the button
        if "message is not modified" not in str(exc):
            logger.error("Failed to edit asset info message: %s", exc)
    await callback.answer()

@router.callback_query(F.data == "back_to_main")
async def cb_back_to_main(callback: CallbackQuery) -> None:
    text = (
        "🔥 <b>Premium Asset For Sale</b> 🔥\n\n"
        "This is a rare, premium Telegram/TON identity — a high-value digital asset "
        "that carries real authority and recognition.\n\n"
        "💰 <b>Asking Price: $1,000 USD</b>\n\n"
        "🔒 <b>Privacy First:</b> Your contact details are strictly confidential. We utilize a client-side, serverless privacy tool to instantly redact sensitive information like emails and phone numbers before any external processing.\n\n"
        "Serious counter-offers are welcome. Tap below to make a bid or learn more."
    )
    try:
        await callback.message.edit_text(text, reply_markup=main_keyboard())
    except TelegramBadRequest:
        pass
    await callback.answer()

@router.callback_query(F.data == "make_offer")
async def cb_make_offer(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.answer(
        "Please type your offer as a numerical amount in USD (e.g. 750)."
    )
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

@router.message()
async def catch_all_messages(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    
    # If they are in the middle of something, don't interrupt
    if current_state is not None:
        return 

    # Look up their past offer
    past_bid = get_user_bid(message.from_user.id)
    
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
        await message.answer(text, reply_markup=change_offer_keyboard())
    else:
        # If they've never bid and type randomly, just show the main menu with privacy note
        text = (
            "Welcome! 🚀\n\n"
            "🔒 <b>Privacy First:</b> Your contact details are strictly confidential. We utilize a client-side, serverless privacy tool to instantly redact sensitive information like emails and phone numbers before any external processing.\n\n"
            "Click below to make an offer or learn more."
        )
        await message.answer(text, reply_markup=main_keyboard())

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
            "🔥 <b>Premium Asset For Sale</b> 🔥\n\n"
            "This is a rare, premium Telegram/TON identity — a high-value digital asset "
            "that carries real authority and recognition.\n\n"
            "💰 <b>Asking Price: $1,000 USD</b>\n\n"
            "Serious counter-offers are welcome. Tap below to make a bid or learn more."
        )
        try:
            await callback.message.edit_text(text, reply_markup=main_keyboard())
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

    # --- NEW WEBHOOK CLEANUP CODE ---
    logger.info("Cleaning up any active webhooks...")
    for bot in bots:
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            await setup_bot_commands(bot)
            logger.info("Successfully cleared webhook and set commands for bot.")
        except Exception as exc:
            logger.warning("Could not clear webhook/set commands: %s", exc)
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