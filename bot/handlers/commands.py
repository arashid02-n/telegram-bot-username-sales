# /start, /my_bid, /about, /support

from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from database import get_user_bid
from keyboards import main_keyboard, change_offer_keyboard

router = Router()

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
        "💬 <b>Contact Us</b>\n\n"
        "Have a question or need assistance ?\n\n"
        "• <b>Telegram:</b> @buytelegrambots_supportbot\n"
        "• <b>Email:</b> support@buytelegrambots.com\n\n"
        "Include the target handle and your offer amount when reaching out so we can help you quickly."
    )
    await message.answer(text)
