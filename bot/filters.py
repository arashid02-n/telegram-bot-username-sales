# Custom aiogram filters (e.g., InLiveChatFilter)

from aiogram.filters import BaseFilter
from aiogram.types import Message
from database import get_active_topic_for_buyer


class InLiveChatFilter(BaseFilter):
    """Checks if a user is currently locked in a LIVE_CHAT state."""
    async def __call__(self, message: Message) -> bool | dict:
        bot_username = (await message.bot.get_me()).username
        topic_id = get_active_topic_for_buyer(bot_username, message.from_user.id)
        if topic_id:
            return {"topic_id": topic_id} # Passes topic_id to the handler
        return False