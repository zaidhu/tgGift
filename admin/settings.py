"""
/settings - Admin bot settings management.
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from sqlalchemy import select

from models import BotSetting
from bot.config import config
from bot.keyboards.order_actions import admin_main_keyboard, admin_settings_keyboard

router = Router()
logger = logging.getLogger(__name__)


class SettingsStates(StatesGroup):
    EDITING_KEY = State()
    EDITING_VALUE = State()


@router.message(Command("settings"))
async def cmd_settings(message: Message, state: FSMContext, **kwargs):
    """Show bot settings."""
    if not config.admin.is_admin(message.from_user.id):
        await message.answer("⛔ Access denied.")
        return

    session_factory = kwargs.get("session")
    async with session_factory() as session:
        result = await session.execute(select(BotSetting).order_by(BotSetting.key))
        settings = result.scalars().all()

    if not settings:
        text = "⚙️ <b>Settings</b>\n\nNo settings configured yet."
    else:
        text = "⚙️ <b>Settings</b>\n\n"
        for s in settings:
            text += f"📋 <b>{s.key}:</b> {s.value}\n"
            if s.description:
                text += f"   _{s.description}_\n"
            text += "\n"

    keyboard = admin_settings_keyboard()
    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)


@router.callback_query(F.data == "admin_settings_list")
async def cb_settings_list(callback: CallbackQuery, **kwargs):
    """Show settings list."""
    if not config.admin.is_admin(callback.from_user.id):
        await callback.answer("⛔ Access denied.", show_alert=True)
        return

    session_factory = kwargs.get("session")
    async with session_factory() as session:
        result = await session.execute(select(BotSetting).order_by(BotSetting.key))
        settings = result.scalars().all()

    if not settings:
        text = "⚙️ <b>Settings</b>\n\nNo settings configured yet."
    else:
        text = "⚙️ <b>Current Settings</b>\n\n"
        for s in settings:
            text += f"• <b>{s.key}:</b> {s.value}\n"

    keyboard = admin_settings_keyboard()
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "admin_settings_edit")
async def cb_settings_edit(callback: CallbackQuery, state: FSMContext, **kwargs):
    """Start editing a setting."""
    if not config.admin.is_admin(callback.from_user.id):
        await callback.answer("⛔ Access denied.", show_alert=True)
        return

    await state.set_state(SettingsStates.EDITING_KEY)
    await callback.message.edit_text(
        "✏️ <b>Edit Setting</b>\n\n"
        "Send the setting key you want to edit.\n"
        "Send /cancel to abort.",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(SettingsStates.EDITING_KEY)
async def msg_editing_key(message: Message, state: FSMContext, **kwargs):
    """Receive setting key."""
    key = (message.text or "").strip()
    if not key:
        await message.answer("⚠️ Please enter a valid setting key.")
        return

    await state.update_data(edit_key=key)
    await state.set_state(SettingsStates.EDITING_VALUE)

    await message.answer(f"Enter the new value for <b>{key}</b>:", parse_mode="HTML")


@router.message(SettingsStates.EDITING_VALUE)
async def msg_editing_value(message: Message, state: FSMContext, **kwargs):
    """Save new setting value."""
    value = message.text or ""
    state_data = await state.get_data()
    key = state_data.get("edit_key", "")

    session_factory = kwargs.get("session")
    async with session_factory() as session:
        # Upsert setting
        result = await session.execute(
            select(BotSetting).where(BotSetting.key == key)
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.value = value
        else:
            setting = BotSetting(key=key, value=value)
            session.add(setting)

        await session.commit()

    await state.clear()
    await message.answer(
        f"✅ <b>Setting Updated</b>\n\n"
        f"<b>{key}:</b> {value}",
        parse_mode="HTML",
        reply_markup=admin_main_keyboard(),
    )


@router.callback_query(F.data == "admin_settings")
async def cb_admin_settings(callback: CallbackQuery, **kwargs):
    """Admin panel - settings."""
    if not config.admin.is_admin(callback.from_user.id):
        await callback.answer("⛔ Access denied.", show_alert=True)
        return

    keyboard = admin_settings_keyboard()
    await callback.message.edit_text(
        "⚙️ <b>Settings</b>\n\nUse the buttons below to manage settings.",
        parse_mode="HTML",
        reply_markup=keyboard,
    )
    await callback.answer()
