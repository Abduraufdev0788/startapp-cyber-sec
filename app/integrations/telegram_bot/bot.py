"""
Telegram Notification Bot Service.
Delivers real-time phishing and scam alerts to users with defanged URLs and Deep Links
directing them to the application to review and dismiss the active threat.
"""

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from app.core.config import get_settings
from app.core.logging import setup_logging

logger = logging.getLogger(__name__)


def build_alert_message(
    chat_title: str,
    defanged_url: str,
    risk_score: int,
    impersonated_brand: str | None,
    reasons: list[str],
) -> str:
    """Formats the alert message in Uzbek with bullet points and clear safety advice."""
    brand_line = f"🎯 Soxtalashtirilgan Brend: {impersonated_brand}\n" if impersonated_brand else ""
    reasons_text = "\n".join([f"• {r}" for r in reasons[:3]])

    return (
        f"🚨 DIQQAT: TELEGRAMINGIZGA XAVFLI FISHING HAVOLASI KELDI!\n\n"
        f"📍 Guruh/Chat: {chat_title}\n"
        f"🔗 Zararli Havola: {defanged_url}\n"
        f"{brand_line}"
        f"⚠️ Xavf Darajasi: {risk_score}/100 (O'ta Yuqori)\n\n"
        f"🔍 Aniqlangan Asosiy Belgilar:\n"
        f"{reasons_text}\n\n"
        f"🛡 TAVSIYA ETILADIGAN HARAKATLAR:\n"
        f"1. Ushbu havolaga aslo kirmang!\n"
        f"2. Hech qanday login, parol yoki Telegram SMS kodlarini kiritmang!\n\n"
        f"⚠️ Ushbu xavf ilovangizda faol holatda turibdi. Xavfni ko'rish va o'chirish uchun quyidagi tugmani bosing:"
    )


def build_alert_keyboard(alert_id: str) -> InlineKeyboardMarkup:
    """Creates the deep-link inline keyboard button directing the user to the app."""
    # Deep link to web application or Telegram Mini App
    app_url = f"https://app.phishguard.uz/alerts/{alert_id}"

    keyboard = [
        [
            InlineKeyboardButton(
                text="📲 Ilovaga o'tish va xavfni ko'rish",
                url=app_url,
            )
        ],
        [
            InlineKeyboardButton(
                text="❓ Qo'llab-quvvatlash",
                url="https://t.me/phishguard_support",
            )
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


async def send_phishing_alert(
    bot_token: str,
    chat_id: int,
    alert_id: str,
    chat_title: str,
    defanged_url: str,
    risk_score: int,
    impersonated_brand: str | None,
    reasons: list[str],
) -> bool:
    """Sends a high-priority phishing alert directly to the user's Telegram DM."""
    from telegram import Bot

    bot = Bot(token=bot_token)
    message_text = build_alert_message(
        chat_title=chat_title,
        defanged_url=defanged_url,
        risk_score=risk_score,
        impersonated_brand=impersonated_brand,
        reasons=reasons,
    )
    keyboard = build_alert_keyboard(alert_id)

    try:
        await bot.send_message(
            chat_id=chat_id,
            text=message_text,
            reply_markup=keyboard,
            disable_web_page_preview=True,  # Never render preview of phishing targets!
        )
        logger.info("Alert successfully delivered to chat_id=%s for alert_id=%s", chat_id, alert_id)
        return True
    except Exception as e:
        logger.error("Failed to deliver Telegram bot alert: %s", str(e), exc_info=True)
        return False


# ------------------------------------------------------------------------------
# Bot Command Handlers
# ------------------------------------------------------------------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /start command."""
    if not update.effective_message:
        return
    welcome_text = (
        "Assalomu alaykum! 🛡️\n\n"
        "Men **PhishGuard** — Telegram guruh va kanallaringizdagi xavfli fishing va firibgarlik havolalarini "
        "kuzatuvchi va sizni ogohlantiruvchi xavfsizlik botiman.\n\n"
        "Xavfli havola aniqlanganda, sizga shu yerda darhol bildirishnoma yuboraman va xavfni ilovangizda "
        "ko'rib, bartaraf etishingiz mumkin bo'ladi."
    )
    await update.effective_message.reply_text(welcome_text, parse_mode="Markdown")


def run_bot() -> None:
    """Runs the Telegram notification bot daemon."""
    settings = get_settings()
    setup_logging()
    logger.info("Starting Telegram Notification Bot daemon...")

    app = ApplicationBuilder().token(settings.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))

    app.run_polling()


if __name__ == "__main__":
    run_bot()
