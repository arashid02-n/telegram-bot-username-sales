# FSM bidding flow & contact entry

import re
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from states import BidStates
from database import get_user_bid
from keyboards import change_offer_keyboard
from services.notifications import finalize_and_notify

router = Router()

@router.callback_query(F.data == "make_offer")
async def cb_make_offer(callback: CallbackQuery, state: FSMContext) -> None:
    bot_username = (await callback.bot.get_me()).username
    await callback.message.answer("Enter your offer in USD (e.g., 750):")
    await state.set_state(BidStates.waiting_for_bid)
    await callback.answer()
    

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


# Catches the user typing an email or phone number
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