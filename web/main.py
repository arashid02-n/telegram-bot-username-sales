import os
import html
import json
import logging
import httpx
from pathlib import Path
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse, FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="BuyTelegramBots Marketplace")

# Initialize Jinja2 templates directory
templates = Jinja2Templates(directory="templates")

# The ONLY folder whose files visitors may download (index.html, styles.css, ...).
# Everything else in web/ (.env, main.py, Dockerfile, templates) stays private.
STATIC_DIR = Path(__file__).resolve().parent / "static"

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


def escape_for_telegram(text: str) -> str:
    """Make buyer-typed text safe inside a Telegram HTML message.

    Telegram rejects the whole message if the text contains a raw `&`, `<`
    or `>` (e.g. "R&D Corp", "budget < 500"), so the offer would be lost.
    Quotes are left as-is: they are harmless outside HTML tags.
    """
    return html.escape(text, quote=False)


def format_telegram_message(data: FormSubmission) -> str:
    e = escape_for_telegram
    notes_section = f"\n<b>📝 Notes:</b> {e(data.notes)}" if data.notes else ""
    return (
        f"🚨 <b>NEW BUYER OFFER RECEIVED</b> 🚨\n\n"
        f"<b>🤖 Target Asset:</b> {e(data.bot_username)}\n"
        f"<b>💰 Offer Amount:</b> ${data.bid:,.2f} USD\n"
        f"<b>👤 Buyer Name:</b> {e(data.name)}\n"
        f"<b>📬 Contact Info:</b> {e(data.contact)}"
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

# Dynamic Sitemap & Robots.txt (Crucial for Google)
@app.get("/robots.txt", response_class=Response)
async def robots_txt():
    content = """User-agent: *
Allow: /
Sitemap: https://buytelegrambots.com/sitemap.xml
"""
    return Response(content=content, media_type="text/plain")

@app.get("/sitemap.xml", response_class=Response)
async def sitemap_xml():
    try:
        with open(STATIC_DIR / "bots.json", "r", encoding="utf-8") as f:
            bots = json.load(f)
    except Exception:
        bots = []

    urls_xml = "".join(
        f"<url><loc>https://buytelegrambots.com/{bot['id']}</loc><changefreq>weekly</changefreq></url>"
        for bot in bots
    )
    
    # Notice the corrected 'sitemaps.org' namespace below
    sitemap_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url><loc>https://buytelegrambots.com/</loc><changefreq>daily</changefreq></url>
    {urls_xml}
</urlset>"""
    return Response(content=sitemap_content, media_type="application/xml")


# Homepage
@app.get("/", response_class=HTMLResponse)
async def serve_homepage():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/{slug}", response_class=HTMLResponse)
async def serve_bot_landing_page(request: Request, slug: str):
    # Serve public files (styles.css, script.js, ...) ONLY from static/.
    # `slug` can never contain "/", so a request cannot leave that folder.
    if "." in slug:
        public_file = STATIC_DIR / slug
        if public_file.is_file():
            return FileResponse(public_file)
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

# Custom 404 Error Page
@app.exception_handler(StarletteHTTPException)
async def custom_404_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return templates.TemplateResponse(request=request, name="404.html", status_code=404)
    return HTMLResponse(content=str(exc.detail), status_code=exc.status_code)