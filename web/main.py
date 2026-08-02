import os
import json
import logging
import httpx
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="BuyTelegramBots Marketplace")

# Initialize Jinja2 templates directory
templates = Jinja2Templates(directory="templates")

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")

if not BOT_TOKEN or not GROUP_CHAT_ID:
    logging.warning("⚠️ Secrets missing! Check your .env file.")

TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class FormSubmission(BaseModel):
    bot_username: str
    name: str
    contact: str
    bid: float
    notes: str | None = None


def format_telegram_message(data: FormSubmission) -> str:
    notes_section = f"\n<b>📝 Notes:</b> {data.notes}" if data.notes else ""
    return (
        f"🚨 <b>NEW BUYER OFFER RECEIVED</b> 🚨\n\n"
        f"<b>🤖 Target Asset:</b> {data.bot_username}\n"
        f"<b>💰 Offer Amount:</b> ${data.bid:,.2f} USD\n"
        f"<b>👤 Buyer Name:</b> {data.name}\n"
        f"<b>📬 Contact Info:</b> {data.contact}"
        f"{notes_section}\n\n"
        f"<i>⚡ Action Required: Reach out to buyer promptly.</i>"
    )


def get_expanded_bot_data(slug: str):
    """Loads bots_individual_pages.json and returns specific bot SEO page content."""
    try:
        with open("bots_individual_pages.json", "r", encoding="utf-8") as f:
            bots = json.load(f)
    except Exception as e:
        logging.error(f"Error reading bots_individual_pages.json: {e}")
        return None

    bot = next((b for b in bots if b["slug"].lower() == slug.lower()), None)
    if not bot:
        return None

    # Derive raw username for Telegram URL by stripping the leading '@' symbol from the handle
    raw_username = bot.get("handle", "").lstrip("@")

    return {
        "slug": bot["slug"],
        "handle": bot["handle"],
        "raw_username": raw_username,
        "category": bot.get("category", "Utilities"),
        "status": bot.get("status", "Accepting Bids"),
        "est_value": bot.get("est_value", "$500"),
        "min_bid": bot.get("min_bid", "100"),
        "pitch": bot.get("pitch", "High-value premium Telegram handle available for acquisition."),
        "ideal_for": bot.get("ideal_for", []),
        "use_cases": bot.get("use_cases", [])
    }


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


@app.get("/{slug}", response_class=HTMLResponse)
async def serve_bot_landing_page(request: Request, slug: str):
    # Serve static asset files directly if requested
    if os.path.isfile(slug):
        return FileResponse(slug)

    if "." in slug:
        raise HTTPException(status_code=404, detail="Not Found")

    bot = get_expanded_bot_data(slug)

    if not bot:
        raise HTTPException(status_code=404, detail="Username not found")

    title = f"Buy {bot['handle']}"
    description = f"Acquire {bot['handle']} ({bot['category']}). {bot['pitch'][:120]}..."
    telegram_cta = f"https://t.me/{bot['raw_username']}"

    return templates.TemplateResponse(
        request=request,
        name="bot_detail.html",
        context={
            "bot": bot,
            "title": title,
            "description": description,
            "telegram_cta": telegram_cta,
        }
    )


# Serve root index.html and static files
app.mount("/", StaticFiles(directory=".", html=True), name="static")