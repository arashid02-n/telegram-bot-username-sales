# Navigation, asset info, & explore IDs callbacks

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext

from database import get_user_bid
from keyboards import (
    main_keyboard, change_offer_keyboard, 
    asset_info_existing_keyboard, explore_ids_keyboard
)
from config import logger

router = Router()

@router.callback_query(F.data.startswith("asset_info:"))
async def cb_asset_info(callback: CallbackQuery) -> None:
    source = callback.data.split(":")[1]
    bot_username = (await callback.bot.get_me()).username
    
    text = (
        "ℹ️ <b>Username Information</b>\n\n"
        f"• <b>Username:</b> @{bot_username}\n"
        "• <b>Status:</b> Accepting Offers\n"
        "• <b>Transfer:</b> Direct Telegram Username Transfer\n\n"
        "Use the button below to submit your offer."
    )
    
    # 2. Build the keyboard dynamically
    buttons = []
    buttons.append([InlineKeyboardButton(text="💵 Make / Change Offer", callback_data="make_offer")])
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
                    "🧾 Your Current Offer\n\n"
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
            "🧾 Your Current Offer\n\n"
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
            "🧾 Your Current Offer\n\n"
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