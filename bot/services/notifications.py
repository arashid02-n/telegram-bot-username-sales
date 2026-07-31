# Admin notification formatting and dispatch logic

import re
from config import GROUP_CHAT_ID, logger
from database import save_or_update_bid
from keyboards import admin_chat_keyboard



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