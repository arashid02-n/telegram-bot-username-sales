import asyncio
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramNetworkError
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from database import init_db
from config import BOT_TOKENS_RAW, PORTFOLIO_IDS, logger

# NEW: Import your master router from the handlers package
from handlers import main_router


async def setup_bot_commands(bot: Bot):
    """Pushes the command menu to the Telegram UI."""
    bot_commands = [
        BotCommand(command="start", description="Main Menu / Restart"),
        BotCommand(command="my_bid", description="View or Edit Offer"),
        BotCommand(command="about", description="How It Works"),
        BotCommand(command="support", description="Contact Broker"),
    ]
    await bot.set_my_commands(bot_commands)


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
            await setup_bot_commands(bot)
            logger.info("Successfully cleared webhook for bot.")
        except Exception as exc:
            logger.warning("Could not clear webhook: %s", exc)
    # ---------------------------------

    dp = Dispatcher(storage=MemoryStorage())
    
    # NEW: Register the master router
    dp.include_router(main_router)

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