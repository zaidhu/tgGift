"""
/users - Admin user management.
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy import select, func

from models import User, UserStatus
from bot.config import config
from bot.keyboards.order_actions import admin_main_keyboard

router = Router()
logger = logging.getLogger(__name__)

USERS_PER_PAGE = 10


@router.message(Command("users"))
async def cmd_users(message: Message, **kwargs):
    """Show user statistics."""
    if not config.admin.is_admin(message.from_user.id):
        await message.answer("⛔ Access denied.")
        return

    session_factory = kwargs.get("session")
    async with session_factory() as session:
        total = await session.execute(select(func.count(User.id)))
        total_count = total.scalar() or 0

        active = await session.execute(
            select(func.count(User.id)).where(User.status == UserStatus.ACTIVE)
        )
        active_count = active.scalar() or 0

        blocked = await session.execute(
            select(func.count(User.id)).where(User.status == UserStatus.BLOCKED)
        )
        blocked_count = blocked.scalar() or 0

        today = await session.execute(
            select(func.count(User.id)).where(
                func.date(User.created_at) == func.current_date()
            )
        )
        today_count = today.scalar() or 0

    text = (
        "👥 <b>User Statistics</b>\n\n"
        f"📊 <b>Total Users:</b> {total_count}\n"
        f"✅ <b>Active:</b> {active_count}\n"
        f"🚫 <b>Blocked:</b> {blocked_count}\n"
        f"📆 <b>New Today:</b> {today_count}\n"
    )

    await message.answer(text, parse_mode="HTML")


@router.callback_query(F.data == "admin_users")
async def cb_admin_users(callback: CallbackQuery, **kwargs):
    """Admin panel - users view."""
    if not config.admin.is_admin(callback.from_user.id):
        await callback.answer("⛔ Access denied.", show_alert=True)
        return

    # Show same stats inline
    session_factory = kwargs.get("session")
    async with session_factory() as session:
        total = await session.execute(select(func.count(User.id)))
        total_count = total.scalar() or 0

        active = await session.execute(
            select(func.count(User.id)).where(User.status == UserStatus.ACTIVE)
        )
        active_count = active.scalar() or 0

        blocked = await session.execute(
            select(func.count(User.id)).where(User.status == UserStatus.BLOCKED)
        )
        blocked_count = blocked.scalar() or 0

    text = (
        "👥 <b>User Management</b>\n\n"
        f"📊 <b>Total Users:</b> {total_count}\n"
        f"✅ <b>Active:</b> {active_count}\n"
        f"🚫 <b>Blocked:</b> {blocked_count}\n\n"
        f"Use /users for full statistics."
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=admin_main_keyboard())
    await callback.answer()
