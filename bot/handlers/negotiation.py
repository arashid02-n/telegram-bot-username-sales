# Admin group live chat & user live message proxying

from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery, 
    InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
)

from config import GROUP_CHAT_ID, logger
from database import (
    get_buyer_username, get_buyer_offer, 
    start_negotiation, get_buyer_for_topic, close_negotiation
)
from filters import InLiveChatFilter
from keyboards import change_offer_keyboard

router = Router()


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
            text=f"🟢 <b>Live Chat Initiated</b>\n\nYou are in a direct chat with an admin regarding <b>@{bot_username}</b> ({offer_str}).\n\nAny message you type here will be sent straight to the broker.\n(Bot functions will not work at this moment.)",
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