"""
Admin panel main entry point.
"""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery

from bot.config import config
from bot.keyboards.order_actions import admin_main_keyboard

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "admin_panel")
async def cb_admin_panel(callback: CallbackQuery, **kwargs):
    """Show admin panel main menu."""
    if not config.admin.is_admin(callback.from_user.id):
        await callback.answer("⛔ Access denied.", show_alert=True)
        return

    text = (
        "🛡️ <b>Admin Panel</b>\n\n"
        "Select an option below:"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=admin_main_keyboard())
    await callback.answer()
