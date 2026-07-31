# Environment variables, constants, and logging setup

import logging
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GROUP_CHAT_ID_RAW = os.getenv("GROUP_CHAT_ID", "")
# Handle standard IDs and Group IDs (which start with '-')
if GROUP_CHAT_ID_RAW.lstrip('-').isdigit():
    GROUP_CHAT_ID = int(GROUP_CHAT_ID_RAW)
else:
    GROUP_CHAT_ID = None

BOT_TOKENS_RAW = os.getenv("BOT_TOKENS", "")

PORTFOLIO_IDS = []