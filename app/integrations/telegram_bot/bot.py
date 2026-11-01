"""
Telegram Notification & Security Bot Service.
Features:
1. Resilient Redis-backed user onboarding with INLINE NUMPAD to bypass Telegram's "shared code" block.
2. Direct URL threat detection with local PostgreSQL caching & Gemini AI fallback.
3. High-priority push alerts when dangerous links appear in monitored chats.
"""

import html
import json
import logging
import re
import secrets
import uuid
from typing import Any

import redis.asyncio as aioredis
from sqlalchemy import select
from telegram import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.security import hash_password
from app.db.session import get_standalone_db_session
from app.modules.telegram_accounts.models import TelegramAccount
from app.modules.telegram_accounts.service import TelegramAccountService
from app.modules.url_scanning.pipeline import extract_urls_from_text
from app.modules.url_scanning.service import UrlScanService
from app.modules.users.models import User

logger = logging.getLogger(__name__)


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Returns persistent main menu keyboard."""
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("📱 Hisobimni ulash"), KeyboardButton("📊 Mening holatim")],
            [KeyboardButton("❓ Yordam")],
        ],
        resize_keyboard=True,
    )


def get_numpad_keyboard(code_so_far: str = "") -> InlineKeyboardMarkup:
    """
    Renders an inline numeric keypad.
    Entering digits via inline callbacks completely bypasses Telegram's
    message-content scanner which blocks OTPs shared in chat messages.
    """
    masked = " ".join(list(code_so_far) + ["•"] * (5 - len(code_so_far)))
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(text=f"🔢 Kod: {masked}", callback_data="num_noop")],
            [
                InlineKeyboardButton(text="1", callback_data="num_1"),
                InlineKeyboardButton(text="2", callback_data="num_2"),
                InlineKeyboardButton(text="3", callback_data="num_3"),
            ],
            [
                InlineKeyboardButton(text="4", callback_data="num_4"),
                InlineKeyboardButton(text="5", callback_data="num_5"),
                InlineKeyboardButton(text="6", callback_data="num_6"),
            ],
            [
                InlineKeyboardButton(text="7", callback_data="num_7"),
                InlineKeyboardButton(text="8", callback_data="num_8"),
                InlineKeyboardButton(text="9", callback_data="num_9"),
            ],
            [
                InlineKeyboardButton(text="⌫ O'chirish", callback_data="num_del"),
                InlineKeyboardButton(text="0", callback_data="num_0"),
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data="num_cancel"),
            ],
        ]
    )


async def get_or_create_user(telegram_user_id: int) -> User:
    """Gets or registers a platform user associated with this Telegram ID."""
    email = f"tg_{telegram_user_id}@phishguard.local"
    async with get_standalone_db_session() as db:
        stmt = select(User).where(User.email == email)
        res = await db.execute(stmt)
        user = res.scalar_one_or_none()
        if not user:
            user = User(
                email=email,
                hashed_password=hash_password(secrets.token_hex(16)),
                role="USER",
                is_active=True,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
        return user


# ------------------------------------------------------------------------------
# Redis State Helpers (Survives bot restarts)
# ------------------------------------------------------------------------------
async def get_user_auth_state(tg_user_id: int) -> dict[str, Any] | None:
    settings = get_settings()
    try:
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        raw = await r.get(f"bot_auth:{tg_user_id}")
        await r.aclose()
        if raw:
            return json.loads(raw)
    except Exception as e:
        logger.error("Error reading bot_auth: %s", e)
    return None


async def set_user_auth_state(tg_user_id: int, data: dict[str, Any], ttl: int = 600) -> None:
    settings = get_settings()
    try:
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await r.set(f"bot_auth:{tg_user_id}", json.dumps(data), ex=ttl)
        await r.aclose()
    except Exception as e:
        logger.error("Error setting bot_auth: %s", e)


async def clear_user_auth_state(tg_user_id: int) -> None:
    settings = get_settings()
    try:
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await r.delete(f"bot_auth:{tg_user_id}")
        await r.aclose()
    except Exception as e:
        logger.error("Error clearing bot_auth: %s", e)


# ------------------------------------------------------------------------------
# Alert Notification Functions (For Celery background tasks)
# ------------------------------------------------------------------------------
def build_alert_message(
    chat_title: str,
    defanged_url_str: str,
    risk_score: int,
    impersonated_brand: str | None,
    reasons: list[str],
) -> str:
    brand_line = f"🎯 <b>Soxtalashtirilgan Brend:</b> {html.escape(impersonated_brand)}\n" if impersonated_brand else ""
    reasons_text = "\n".join([f"• {html.escape(r)}" for r in reasons[:3]]) if reasons else "• Xavfsizlik mezonlari bo'yicha shubha uyg'otdi"

    if risk_score >= 70:
        header = "🚨 <b>DIQQAT: XAVFLI FISHING HAVOLASI (Yomon)!</b>"
        badge = "🔴 O'ta Xavfli (Yomon)"
        advice = (
            "🛡 <b>XAVFSIZLIK TAVSIYALARI:</b>\n"
            "1. Ushbu havolaga aslo kirmang va ma'lumot qoldirmang!\n"
            "2. Hech qanday login, parol, karta raqami yoki Telegram SMS kodlarini kiritmang!"
        )
    elif risk_score >= 50:
        header = "⚠️ <b>DIQQAT: FIRIBGARLIK (SCAM) HAVOLASI (Yomon)!</b>"
        badge = "🟠 Firibgarlik (Scam)"
        advice = (
            "🛡 <b>XAVFSIZLIK TAVSIYALARI:</b>\n"
            "1. Shubhali moliyaviy yoki soxta sovrin va'da qiluvchi sayt.\n"
            "2. Hech qanday to'lov qilmang va ma'lumot qoldirmang!"
        )
    elif risk_score >= 40:
        header = "⚠️ <b>DIQQAT: SHUBHALI HAVOLA!</b>"
        badge = "🟡 Shubhali"
        advice = (
            "🛡 <b>XAVFSIZLIK TAVSIYALARI:</b>\n"
            "1. Sayt yangi yoki shubhali belgilarga ega.\n"
            "2. Ehtiyotkorlik bilan foydalaning."
        )
    else:
        header = "✅ <b>XULOSA: XAVFSIZ / YAXSHI HAVOLA!</b>"
        badge = "🟢 Xavfsiz (Yaxshi)"
        advice = (
            "🛡 <b>XULOSA:</b>\n"
            "Ushbu havola xavfsiz va toza deb topildi. Hech qanday xavf aniqlanmadi."
        )

    fallback_reason = "• Sayt xavfsiz, SSL va domen tekshiruvidan muvaffaqiyatli o'tdi" if risk_score < 40 else "• Xavfsizlik mezonlari bo'yicha shubha uyg'otdi"
    reasons_text = "\n".join([f"• {html.escape(r)}" for r in reasons[:3]]) if reasons else fallback_reason

    return (
        f"{header}\n\n"
        f"📍 <b>Manba (Guruh / Kontakt):</b> {html.escape(chat_title)}\n"
        f"🔗 <b>Havola:</b> <code>{html.escape(defanged_url_str)}</code>\n"
        f"{brand_line}"
        f"📊 <b>Xavf Darajasi:</b> {risk_score}/100 ({badge})\n\n"
        f"🔍 <b>Tahlil Natijasi:</b>\n"
        f"{reasons_text}\n\n"
        f"{advice}"
    )


def build_alert_keyboard(alert_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(text="❓ Qo'llab-quvvatlash", url="https://t.me/phishguard_support")],
        ]
    )


async def send_phishing_alert(
    bot_token: str,
    chat_id: int,
    alert_id: str,
    chat_title: str,
    defanged_url: str | None = None,
    risk_score: int = 0,
    impersonated_brand: str | None = None,
    reasons: list[str] | None = None,
    defanged_url_str: str | None = None,
) -> bool:
    from telegram import Bot

    url_to_show = defanged_url or defanged_url_str or "N/A"
    bot = Bot(token=bot_token)
    msg_text = build_alert_message(chat_title, url_to_show, risk_score, impersonated_brand, reasons or [])
    kb = build_alert_keyboard(alert_id)
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=msg_text,
            reply_markup=kb,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        return True
    except Exception as e:
        logger.error("Failed to deliver alert to %s: %s", chat_id, e)
        return False


# ------------------------------------------------------------------------------
# Command Handlers
# ------------------------------------------------------------------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_message:
        return

    # Track unique bot users for platform analytics
    if update.effective_user:
        try:
            settings = get_settings()
            r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            await r.sadd("bot:unique_users", str(update.effective_user.id))
            await r.aclose()
        except Exception as e:
            logger.warning("Could not record bot:unique_users in Redis: %s", e)

    welcome_text = (
        "Assalomu alaykum! 🛡️\n\n"
        "Men <b>StartApp PhishGuard</b> — Telegram guruh va shaxsiy chatlaringizni "
        "xavfli fishing va firibgarlik havolalaridan himoya qiluvchi xavfsizlik botiman.\n\n"
        "⚡️ <b>Asosiy imkoniyatlar:</b>\n"
        "1. <b>Tezkor tekshirish:</b> Menga istalgan shubhali havolani yuboring — "
        "keshdan (0.1 soniyada) yoki Gemini AI orqali tekshirib beraman.\n"
        "2. <b>24/7 Guruhlar monitoringi:</b> «📱 Hisobimni ulash» tugmasi orqali "
        "Telegram hisobingizni ulab qo'ysangiz, siz a'zo bo'lgan barcha guruhlardagi "
        "havolalar orqa fonda avtomatik tekshirib boriladi!\n\n"
        "Quyidagi tugmalardan birini tanlang:"
    )
    await update.effective_message.reply_text(
        welcome_text,
        reply_markup=get_main_keyboard(),
        parse_mode="HTML",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_message:
        return
    help_text = (
        "❓ <b>Qanday foydalaniladi?</b>\n\n"
        "🔗 <b>Havolani tekshirish:</b>\n"
        "Shunchaki havolani xabar sifatida menga yuboring (masalan: <code>https://misol.uz</code>). "
        "Agar havola avval bazamizda bo'lsa, bir zumda keshdan javob beraman, aks holda "
        "Gemini AI orqali to'liq tekshirib, xavf darajasini aytaman.\n\n"
        "📱 <b>Guruhlarni himoya qilish:</b>\n"
        "«📱 Hisobimni ulash» tugmasini bosing va telefon raqamingizni yuboring. "
        "Telegramingizga kelgan 5 xonali kodni xabar qilib emas, <b>ekrandagi raqamli tugmalarni bosib</b> kiriting. "
        "Shunda hisobingiz ulanadi va barcha guruhlaringiz xavfsizlik nazoratiga olinadi."
    )
    await update.effective_message.reply_text(help_text, parse_mode="HTML", reply_markup=get_main_keyboard())


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_message or not update.effective_user:
        return
    tg_user_id = update.effective_user.id
    async with get_standalone_db_session() as db:
        stmt = select(TelegramAccount).where(
            TelegramAccount.telegram_user_id == tg_user_id,
            TelegramAccount.status == "CONNECTED",
        )
        res = await db.execute(stmt)
        account = res.scalar_one_or_none()

    if account:
        text = (
            "✅ <b>Sizning holatingiz: Himoyalangansiz!</b>\n\n"
            f"📱 <b>Ulangan Telegram ID:</b> <code>{tg_user_id}</code>\n"
            f"🛡 <b>Monitoring holati:</b> FAOL (24/7 kuzatuvda)\n"
            f"🕒 <b>Ulangan vaqt:</b> {account.last_connected_at.strftime('%Y-%m-%d %H:%M UTC')}\n\n"
            "Siz a'zo bo'lgan barcha guruh va kanallar fishing havolalardan himoyalangan."
        )
    else:
        text = (
            "⚠️ <b>Sizning holatingiz: Hisobingiz ulanmagan</b>\n\n"
            "Guruhlaringizdagi xavfli havolalarni orqa fonda avtomatik aniqlash uchun "
            "pastdagi <b>«📱 Hisobimni ulash»</b> tugmasini bosing."
        )
    await update.effective_message.reply_text(text, parse_mode="HTML", reply_markup=get_main_keyboard())


async def connect_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Starts the account connection prompt."""
    if not update.effective_message or not update.effective_user:
        return
    tg_user_id = update.effective_user.id

    # Check if already connected
    async with get_standalone_db_session() as db:
        stmt = select(TelegramAccount).where(
            TelegramAccount.telegram_user_id == tg_user_id,
            TelegramAccount.status == "CONNECTED",
        )
        res = await db.execute(stmt)
        if res.scalar_one_or_none():
            await update.effective_message.reply_text(
                "✅ Sizning hisobingiz allaqachon ulangan va monitoring faol!",
                reply_markup=get_main_keyboard(),
            )
            return

    phone_keyboard = ReplyKeyboardMarkup(
        [
            [KeyboardButton("📱 Telefon raqamimni yuborish", request_contact=True)],
            [KeyboardButton("❌ Bekor qilish")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    await set_user_auth_state(tg_user_id, {"step": "WAIT_PHONE"})

    msg = (
        "📱 <b>Telegram hisobingizni ulash:</b>\n\n"
        "Guruhlaringizdagi havolalarni avtomatik kuzatish uchun telefon raqamingizni yuboring.\n\n"
        "Pastdagi <b>«📱 Telefon raqamimni yuborish»</b> tugmasini bosing yoki "
        "raqamingizni xalqaro formatda yozing (masalan: <code>+998901234567</code>):"
    )
    await update.effective_message.reply_text(msg, reply_markup=phone_keyboard, parse_mode="HTML")


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_message or not update.effective_user:
        return
    await clear_user_auth_state(update.effective_user.id)
    await update.effective_message.reply_text("Amal bekor qilindi.", reply_markup=get_main_keyboard())


# ------------------------------------------------------------------------------
# Inline Numpad Callback Handler (Prevents Telegram "shared code" block!)
# ------------------------------------------------------------------------------
async def numpad_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles button presses on the virtual numeric keypad.
    Since callback data is not a chat message, Telegram's message scanner
    cannot detect the OTP code, allowing smooth login!
    """
    query = update.callback_query
    if not query or not update.effective_user:
        return

    await query.answer()
    data = query.data or ""
    tg_user_id = update.effective_user.id

    auth_state = await get_user_auth_state(tg_user_id) or {}
    phone = auth_state.get("phone")
    phone_code_hash = auth_state.get("phone_code_hash")
    current_code = auth_state.get("entered_code", "")

    if data == "num_noop":
        return

    if data == "num_cancel":
        await clear_user_auth_state(tg_user_id)
        await query.edit_message_text("❌ Ulanish bekor qilindi.")
        await query.message.reply_text("Bosh menyu:", reply_markup=get_main_keyboard())
        return

    if data == "num_del":
        current_code = current_code[:-1]
        auth_state["entered_code"] = current_code
        await set_user_auth_state(tg_user_id, auth_state)
        await query.edit_message_reply_markup(reply_markup=get_numpad_keyboard(current_code))
        return

    # Digit clicked
    digit = data.replace("num_", "")
    if digit.isdigit() and len(current_code) < 5:
        current_code += digit
        auth_state["entered_code"] = current_code
        await set_user_auth_state(tg_user_id, auth_state)

        if len(current_code) < 5:
            await query.edit_message_reply_markup(reply_markup=get_numpad_keyboard(current_code))
            return

        # Exactly 5 digits collected -> trigger verification immediately!
        await query.edit_message_text(f"⏳ Kod tekshirilmoqda: <code>{current_code}</code>...", parse_mode="HTML")

        try:
            user = await get_or_create_user(tg_user_id)
            result = await TelegramAccountService.verify_code(
                user_id=user.id,
                phone_number=phone,
                phone_code_hash=phone_code_hash,
                code=current_code,
            )

            if result.get("status") == "NEED_2FA":
                auth_state["step"] = "WAIT_2FA"
                auth_state["entered_code"] = ""
                await set_user_auth_state(tg_user_id, auth_state)
                await query.edit_message_text(
                    "🔐 <b>2FA Bulutli Paroli Talab Qilinadi</b>\n\n"
                    "Akkauntingizda ikki bosqichli autentifikatsiya (2FA) yoqilgan.\n"
                    "Iltimos, Telegram 2FA bulutli parolingizni xabar sifatida yozing:",
                    parse_mode="HTML",
                )
                return

            if result.get("status") == "CONNECTED":
                await clear_user_auth_state(tg_user_id)
                await query.edit_message_text(
                    "🎉 <b>Tabriklaymiz! Telegram hisobingiz muvaffaqiyatli ulandi!</b>\n\n"
                    "🛡️ <b>24/7 Monitoring faollashtirildi:</b>\n"
                    "Endi siz a'zo bo'lgan barcha guruh va chatlar avtomatik kuzatiladi. "
                    "Agar kimdir fishing yoki soxta havola tashlasa, sizga shu yerda darhol signal yuboraman!",
                    parse_mode="HTML",
                )
                await query.message.reply_text("Boshqaruv menyusi:", reply_markup=get_main_keyboard())
                return

            msg_res = result.get("message", "Noma'lum holat")
            await query.edit_message_text(f"Natija: {msg_res}")
            return

        except Exception as e:
            logger.error("Error verifying code via numpad: %s", e)
            auth_state["entered_code"] = ""
            await set_user_auth_state(tg_user_id, auth_state)
            await query.edit_message_text(
                f"❌ Xatolik: {html.escape(str(e))}\n\nQaytadan raqamli tugmalarni bosib kiriting:",
                reply_markup=get_numpad_keyboard(""),
            )


# ------------------------------------------------------------------------------
# Universal Message Router (Phone, 2FA, URL, Buttons)
# ------------------------------------------------------------------------------
async def universal_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_message or not update.effective_user:
        return

    tg_user_id = update.effective_user.id
    contact = update.effective_message.contact
    raw_text = (update.effective_message.text or "").strip()

    # 1. Check navigation buttons
    if raw_text == "📱 Hisobimni ulash":
        await connect_command(update, context)
        return
    elif raw_text == "📊 Mening holatim":
        await status_command(update, context)
        return
    elif raw_text == "❓ Yordam":
        await help_command(update, context)
        return
    elif raw_text == "❌ Bekor qilish":
        await cancel_command(update, context)
        return

    auth_state = await get_user_auth_state(tg_user_id) or {}
    current_step = auth_state.get("step")

    # 2. Check if a Phone Number was sent (Contact button or text)
    phone_input = None
    if contact and contact.phone_number:
        phone_input = contact.phone_number
    elif current_step == "WAIT_PHONE":
        phone_input = raw_text
    elif not current_step and re.match(r"^\+?\d{9,15}$", re.sub(r"[\s-]", "", raw_text)):
        phone_input = raw_text

    if phone_input:
        digits = re.sub(r"\D", "", phone_input)
        if len(digits) < 9:
            await update.effective_message.reply_text(
                "❌ Telefon raqami kamida 9 ta raqamdan iborat bo'lishi kerak. Qaytadan kiriting:"
            )
            return

        clean_phone = "+" + digits
        status_msg = await update.effective_message.reply_text(
            "⏳ Telegram'dan yangi tasdiqlash kodi so'ralmoqda...",
            reply_markup=ReplyKeyboardRemove(),
        )

        try:
            handshake = await TelegramAccountService.send_code(clean_phone)
            await set_user_auth_state(
                tg_user_id,
                {
                    "step": "WAIT_CODE",
                    "phone": clean_phone,
                    "phone_code_hash": handshake["phone_code_hash"],
                    "entered_code": "",
                },
            )

            prompt_text = (
                f"📩 <b>Tasdiqlash kodi yuborildi!</b>\n\n"
                f"Raqam: <code>{clean_phone}</code>\n\n"
                f"⚠️ <b>MUHIM:</b> Telegram'dan kelgan 5 xonali kodni <b>pastdagi tugmachalarni bosib</b> kiriting "
                f"(shunda Telegram uni bloklamaydi):\n\n"
                f"<i>(Agar tugmalar chiqmasa, kodni to'g'ridan-to'g'ri yozib yuborsangiz ham bo'ladi)</i>"
            )
            try:
                await status_msg.delete()
            except Exception:
                pass

            await update.effective_message.reply_text(
                prompt_text,
                reply_markup=get_numpad_keyboard(""),
                parse_mode="HTML",
            )
            return
        except Exception as e:
            logger.error("Failed to send telegram code: %s", e)
            try:
                await status_msg.delete()
            except Exception:
                pass
            await update.effective_message.reply_text(
                f"❌ Kodni yuborishda xatolik: {html.escape(str(e))}\n\nIltimos, qaytadan urinib ko'ring.",
                reply_markup=get_main_keyboard(),
            )
            await clear_user_auth_state(tg_user_id)
            return

    # 3. Check if user typed OTP digits into the chat text directly
    clean_digits = "".join(filter(str.isdigit, raw_text))
    if (current_step == "WAIT_CODE" or not current_step) and 4 <= len(clean_digits) <= 6:
        phone = auth_state.get("phone")
        phone_code_hash = auth_state.get("phone_code_hash")

        if phone and phone_code_hash:
            status_msg = await update.effective_message.reply_text("⏳ Kod tekshirilmoqda...")
            try:
                user = await get_or_create_user(tg_user_id)
                result = await TelegramAccountService.verify_code(
                    user_id=user.id,
                    phone_number=phone,
                    phone_code_hash=phone_code_hash,
                    code=clean_digits,
                )

                if result.get("status") == "NEED_2FA":
                    auth_state["step"] = "WAIT_2FA"
                    await set_user_auth_state(tg_user_id, auth_state)
                    await status_msg.edit_text(
                        "🔐 <b>2FA Bulutli Paroli Talab Qilinadi</b>\n\n"
                        "Akkauntingizda 2FA yoqilgan. Iltimos, 2FA parolingizni yozing:",
                        parse_mode="HTML",
                    )
                    return

                if result.get("status") == "CONNECTED":
                    await clear_user_auth_state(tg_user_id)
                    await status_msg.edit_text(
                        "🎉 <b>Tabriklaymiz! Telegram hisobingiz muvaffaqiyatli ulandi!</b>\n\n"
                        "🛡️ <b>24/7 Monitoring faollashtirildi:</b> Endi siz a'zo bo'lgan barcha guruhlar kuzatuvda!",
                        parse_mode="HTML",
                    )
                    await update.effective_message.reply_text("Bosh menyu:", reply_markup=get_main_keyboard())
                    return
            except Exception as verify_err:
                logger.warning("Code verification via text failed: %s", verify_err)
                warn_msg = (
                    f"❌ <b>Tasdiqlashda xatolik:</b> {html.escape(str(verify_err))}\n\n"
                    "💡 <b>Telegram cheklovi:</b> Agar Telegram kodni 'chatda tarqatildi' deb bekor qilgan bo'lsa, "
                    "Iltimos, qaytadan «📱 Hisobimni ulash» tugmasini bosing va kodni <b>ekrandagi raqamli tugmalarni bosib</b> kiriting:"
                )
                await status_msg.edit_text(
                    warn_msg,
                    reply_markup=get_numpad_keyboard(""),
                    parse_mode="HTML",
                )
                return

    # 4. Check if 2FA password was sent
    if current_step == "WAIT_2FA":
        phone = auth_state.get("phone")
        if not phone:
            await update.effective_message.reply_text("Sessiya topilmadi. Qaytadan boshlang.", reply_markup=get_main_keyboard())
            await clear_user_auth_state(tg_user_id)
            return

        status_msg = await update.effective_message.reply_text("⏳ 2FA paroli tekshirilmoqda...")
        try:
            user = await get_or_create_user(tg_user_id)
            result = await TelegramAccountService.verify_2fa(
                user_id=user.id,
                phone_number=phone,
                password_2fa=raw_text,
            )

            if result.get("status") == "CONNECTED":
                await clear_user_auth_state(tg_user_id)
                await status_msg.edit_text(
                    "🎉 <b>Tabriklaymiz! Hisobingiz 2FA orqali muvaffaqiyatli ulandi!</b>\n\n"
                    "🛡️ <b>Monitoring faol:</b> Barcha guruhlaringiz himoyaga olindi.",
                    parse_mode="HTML",
                )
                await update.effective_message.reply_text("Boshqaruv menyusi:", reply_markup=get_main_keyboard())
                return
            await status_msg.edit_text(f"Natija: {result.get('message', 'Xatolik')}")
            return
        except Exception as e:
            logger.error("Error verifying 2FA: %s", e)
            await status_msg.edit_text(f"❌ 2FA paroli noto'g'ri: {html.escape(str(e))}\nQaytadan kiriting:")
            return

    # 5. Check if URLs were sent for scanning
    urls = extract_urls_from_text(raw_text)
    if urls:
        target_url = urls[0]
        status_msg = await update.effective_message.reply_text(
            "🔍 <b>Havola xavfsizligi tahlil qilinmoqda...</b>\n"
            "<i>(Kesh, DNS, SSL va Gemini AI tekshiruvlari)</i>",
            parse_mode="HTML",
        )
        try:
            result = await UrlScanService.scan_and_evaluate(target_url)

            verdict = result.get("verdict", "BENIGN")
            risk_score = result.get("risk_score", 0)
            domain = result.get("domain", "")
            cached = result.get("cached", False)
            impersonated_brand = result.get("impersonated_brand")
            reasons = result.get("reasons", [])

            if verdict == "MALICIOUS" or risk_score >= 60:
                status_header = "🚨 <b>XULOSA: XAVFLI FISHING / FIRIBGARLIK!</b>"
                verdict_badge = "🔴 <b>O'ta Xavfli</b>"
                advice = (
                    "⚠️ <b>XAVFSIZLIK TAVSIYASI:</b>\n"
                    "1. Ushbu saytga aslo kirmang va ma'lumot qoldirmang!\n"
                    "2. Hech qachon bank karta ma'lumotlari yoki SMS kodlarini kiritmang!"
                )
            elif verdict == "SUSPICIOUS" or risk_score >= 35:
                status_header = "⚠️ <b>XULOSA: SHUBHALI HAVOLA!</b>"
                verdict_badge = "🟡 <b>Shubhali</b>"
                advice = "Ehtiyot bo'ling. Ushbu sayt yangi yoki shubhali belgilarga ega."
            else:
                status_header = "✅ <b>XULOSA: XAVFSIZ HAVOLA</b>"
                verdict_badge = "🟢 <b>Toza / Benign</b>"
                advice = "Hozircha ushbu manzilda hech qanday fishing yoki zararli faoliyat aniqlanmadi."

            brand_line = f"🎯 <b>Soxtalashtirilgan Brend:</b> {html.escape(impersonated_brand)}\n" if impersonated_brand else ""
            reasons_text = "\n".join([f"• {html.escape(r)}" for r in reasons[:3]]) if reasons else "• Standart xavfsizlik mezonlari qoniqarli"
            cache_badge = "⚡️ <i>(Avval tekshirilgan — keshdan olindi)</i>" if cached else "🤖 <i>(Gemini AI va skaner orqali yangi tahlil qilindi)</i>"

            response_text = (
                f"{status_header}\n{cache_badge}\n\n"
                f"🔗 <b>Havola:</b> <code>{html.escape(target_url)}</code>\n"
                f"🌐 <b>Domen:</b> <code>{html.escape(domain)}</code>\n"
                f"📊 <b>Xavf darajasi:</b> {risk_score}/100 ({verdict_badge})\n"
                f"{brand_line}"
                f"📋 <b>Asosiy xususiyatlar:</b>\n"
                f"{reasons_text}\n\n"
                f"{advice}"
            )
            await status_msg.edit_text(response_text, parse_mode="HTML")
            return
        except Exception as e:
            logger.error("Error during manual URL scanning: %s", e)
            await status_msg.edit_text(f"❌ Xatolik: {html.escape(str(e))}")
            return

    # 6. Default fallback
    await update.effective_message.reply_text(
        "Menga tekshirish uchun biron-bir havola (masalan: <code>https://misol.uz</code>) yuboring, "
        "yoki hisobingizni ulash uchun <b>«📱 Hisobimni ulash»</b> tugmasini bosing.",
        parse_mode="HTML",
        reply_markup=get_main_keyboard(),
    )


# ------------------------------------------------------------------------------
# Bot Daemon Runner
# ------------------------------------------------------------------------------
def run_bot() -> None:
    settings = get_settings()
    setup_logging()
    logger.info("Starting Telegram Notification & Interactive Security Bot daemon...")

    app = ApplicationBuilder().token(settings.TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("connect", connect_command))
    app.add_handler(CommandHandler("cancel", cancel_command))

    # Inline Numpad callback handler
    app.add_handler(CallbackQueryHandler(numpad_callback_handler, pattern=r"^num_"))

    # All non-command messages routed through the resilient universal handler
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, universal_message_handler))

    app.run_polling()


if __name__ == "__main__":
    run_bot()
