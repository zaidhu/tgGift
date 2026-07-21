"""
/system - Admin system health and status.
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy import text

from bot.config import config
from bot.keyboards.order_actions import admin_main_keyboard

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("system"))
async def cmd_system(message: Message, **kwargs):
    """Show system health status."""
    if not config.admin.is_admin(message.from_user.id):
        await message.answer("⛔ Access denied.")
        return

    session_factory = kwargs.get("session")

    # Check database
    db_status = "✅ Connected"
    try:
        async with session_factory() as session:
            result = await session.execute(text("SELECT 1"))
            result.scalar()
    except Exception as e:
        db_status = f"❌ Error: {str(e)[:50]}"

    # Check Redis
    redis_status = "⚠️ Not configured"
    try:
        import redis
        r = redis.from_url(config.redis.url)
        r.ping()
        redis_status = "✅ Connected"
    except Exception as e:
        redis_status = f"❌ Error: {str(e)[:50]}"

    # Bot info
    bot = message.bot
    try:
        me = await bot.get_me()
        bot_username = me.username
    except Exception:
        bot_username = "Unknown"

    text = (
        "⚙️ <b>System Status</b>\n\n"
        f"🤖 <b>Bot:</b> @{bot_username}\n"
        f"🗄️ <b>Database:</b> {db_status}\n"
        f"📦 <b>Redis:</b> {redis_status}\n"
        f"🌍 <b>Environment:</b> {config.environment}\n"
        f"💰 <b>Currency:</b> {config.payment.currency}\n\n"
        f"<b>Admin Config:</b>\n"
        f"   Owner ID: {config.admin.owner_id}\n"
        f"   Admin IDs: {config.admin.admin_ids}\n"
    )

    await message.answer(text, parse_mode="HTML")


@router.callback_query(F.data == "admin_system")
async def cb_admin_system(callback: CallbackQuery, **kwargs):
    """Admin panel - system status."""
    if not config.admin.is_admin(callback.from_user.id):
        await callback.answer("⛔ Access denied.", show_alert=True)
        return

    session_factory = kwargs.get("session")

    db_status = "✅ Connected"
    try:
        async with session_factory() as session:
            result = await session.execute(text("SELECT 1"))
            result.scalar()
    except Exception:
        db_status = "❌ Error"

    bot = callback.bot
    try:
        me = await bot.get_me()
        bot_username = me.username
    except Exception:
        bot_username = "Unknown"

    text = (
        "⚙️ <b>System Status</b>\n\n"
        f"🤖 <b>Bot:</b> @{bot_username}\n"
        f"🗄️ <b>Database:</b> {db_status}\n"
        f"🌍 <b>Environment:</b> {config.environment}\n"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=admin_main_keyboard())
    await callback.answer()
