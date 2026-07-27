from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import logging
import os
from dotenv import load_dotenv

# Load secrets from .env file
load_dotenv()

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="Web Form Telegram Relay")

# Securely grab tokens from environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")

if not BOT_TOKEN or not GROUP_CHAT_ID:
    logging.warning("⚠️ Secrets missing! Check your .env file.")

TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"


# Enable CORS so your website frontend can send POST requests without browser blocks
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace "*" with your frontend domain in production, replace with: ( "https://buytelegrambots.com", "https://www.buytelegrambots.com" )
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 1. Define the incoming form payload structure
# (We changed item_requested -> bot_username and budget -> bid to match index.html exactly)
class FormSubmission(BaseModel):
    bot_username: str
    name: str
    contact: str
    bid: str | int | float
    notes: str | None = None


# 2. Format payload into clean HTML for Telegram
def format_telegram_message(data: FormSubmission) -> str:
    text = (
        "<b>📥 New Web Form Bid Received!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>🤖 Target Asset:</b> <code>@{data.bot_username.replace('@', '')}</code>\n"
        f"<b>💰 Offer Amount:</b> ${data.bid}\n"
        f"<b>👤 Buyer Name:</b> {data.name}\n"
        f"<b>💬 Contact Info:</b> <code>{data.contact}</code>\n"
    )
    if data.notes:
        text += f"\n<b>📝 Additional Notes:</b>\n<i>{data.notes}</i>"

    return text


# 3. Webhook endpoint to receive form POSTs
@app.post("/api/submit-form", status_code=status.HTTP_200_OK)
async def handle_form_submission(form_data: FormSubmission):
    formatted_message = format_telegram_message(form_data)

    payload = {
        "chat_id": GROUP_CHAT_ID,
        "text": formatted_message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(TELEGRAM_API_URL, json=payload, timeout=10.0)
            result = response.json()

            if not result.get("ok"):
                logging.error(f"Telegram API Error: {result}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Failed to deliver message to Telegram.",
                )

        except httpx.RequestError as exc:
            logging.error(f"Network error connecting to Telegram: {exc}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Telegram API connection failed.",
            )

    return {"status": "success", "message": "Request delivered to team group chat."}

from fastapi.staticfiles import StaticFiles

# ==========================================
# SERVE FRONTEND STATIC FILES
# (Must be placed AFTER all /api routes!)
# ==========================================
app.mount("/", StaticFiles(directory=".", html=True), name="static")