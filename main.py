import asyncio
import logging
import os
import sys

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

from database import init_db, save_bid

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
            [InlineKeyboardButton(text="💬 Make an Offer", callback_data="make_offer")],
            [InlineKeyboardButton(text="ℹ️ Asset Info", callback_data="asset_info")],
        ]
    )


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    text = (
        "🔥 <b>Premium Asset For Sale</b> 🔥\n\n"
        "This is a rare, premium Telegram/TON identity — a high-value digital asset "
        "that carries real authority and recognition.\n\n"
        "💰 <b>Asking Price: $1,000 USD</b>\n\n"
        "Serious counter-offers are welcome. Tap below to make a bid or learn more."
    )
    await message.answer(text, reply_markup=main_keyboard())


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
        await callback.message.edit_text(text, reply_markup=main_keyboard())
    except TelegramBadRequest as exc:
        # Ignore the error if the user just double-clicked the button
        if "message is not modified" not in str(exc):
            logger.error("Failed to edit asset info message: %s", exc)
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

    if not raw.isdigit():
        await message.answer(
            "⚠️ Please enter a valid numeric amount (digits only, e.g. 750)."
        )
        return

    bid_amount = float(raw)
    await state.update_data(bid_amount=bid_amount)
    await message.answer(
        "Great, got your offer! 🎯\n\n"
        "If you would prefer faster contact, please share your **cell phone number** or **email address** below.\n\n"
        "*(If you prefer to just be contacted here on Telegram, simply type 'skip'.)*"
    )
    await state.set_state(BidStates.waiting_for_contact)


@router.message(BidStates.waiting_for_contact)
async def process_contact_info(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    bid_amount = data.get("bid_amount")
    contact_info = (message.text or "").strip()

    bot_user = await message.bot.get_me()
    buyer_username = message.from_user.username or "N/A"

    save_bid(
        bot_username=bot_user.username,
        buyer_chat_id=message.from_user.id,
        buyer_username=buyer_username,
        bid_amount=bid_amount,
        contact_info=contact_info,
    )

    await message.answer(
        "✅ Thank you! Your offer has been recorded and forwarded to the broker. "
        "You'll be contacted shortly if there's interest."
    )

    if ADMIN_CHAT_IDS:
        logger.info("Attempting to notify Admin IDs: %s", ADMIN_CHAT_IDS)
        alert_text = (
            "📩 <b>New Bid Received</b>\n\n"
            f"<b>Bot:</b> @{bot_user.username}\n"
            f"<b>Buyer:</b> @{buyer_username} (ID: <code>{message.from_user.id}</code>)\n"
            f"<b>Bid:</b> ${bid_amount:,.2f}\n"
            f"<b>Contact:</b> {contact_info}"
        )
        for admin_id in ADMIN_CHAT_IDS:
            try:
                await message.bot.send_message(chat_id=admin_id, text=alert_text)
                logger.info("Successfully sent notification to admin: %s", admin_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to notify admin %s: %s", admin_id, exc)
    else:
        logger.warning("No Admin IDs configured to receive notifications!")

    await state.clear()


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
            # Drops the webhook and ignores any old/pending clicks 
            await bot.delete_webhook(drop_pending_updates=True)
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