from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import CallbackQuery, ChatJoinRequest, LabeledPrice, Message, PreCheckoutQuery

from app.catalog import TOOLS, STYLE_CATEGORY, UTILITY_CATEGORY
from app.config import Settings
from app.db import MongoStore, today_key, utcnow
from app.keyboards import (
    admin_back_keyboard,
    admin_ban_keyboard,
    admin_bot_settings_keyboard,
    admin_broadcast_keyboard,
    admin_force_keyboard,
    admin_keyboard,
    admin_premium_keyboard,
    admin_referral_keyboard,
    category_keyboard,
    confirm_keyboard,
    force_gate_keyboard,
    language_keyboard,
    main_menu_keyboard,
    output_style_keyboard,
    premium_keyboard,
    profile_keyboard,
    referral_keyboard,
    result_keyboard,
    settings_keyboard,
    support_keyboard,
    task_detail_keyboard,
    tasks_keyboard,
    tool_prompt_keyboard,
)
from app.renderers import (
    admin_broadcast_screen,
    admin_force_screen,
    admin_home_screen,
    admin_bot_settings_screen,
    admin_referral_screen,
    admin_stats_screen,
    cancelled_screen,
    category_screen,
    choose_tool_first_screen,
    empty_input_screen,
    force_subscription_screen,
    help_screen,
    logs_screen,
    main_caption,
    premium_screen,
    processing_error_screen,
    processing_screen,
    profile_screen,
    referral_leaderboard_screen,
    referral_screen,
    result_screen,
    settings_screen,
    support_screen,
    system_status_screen,
    task_detail_screen,
    tasks_screen,
    too_long_screen,
    terms_screen,
    tool_prompt,
    unauthorized_screen,
)
from app.text_style import bold_unicode
from app.text_tools import process_tool


logger = logging.getLogger(__name__)
router = Router(name="text_tool_bot")
STARTED_AT = utcnow()


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, bot: Bot, store: MongoStore, settings: Settings) -> None:
    user = await _ensure_user_access(message, bot, store, settings, referral_arg=command.args)
    if not user:
        return
    config = await store.runtime_config()
    await _send_or_edit(
        message,
        main_caption(str(config.get("start_caption") or ""), user),
        main_menu_keyboard(),
        photo_url=str(config.get("start_photo_url") or ""),
    )


@router.message(Command("admin"))
async def cmd_admin(message: Message, store: MongoStore, settings: Settings) -> None:
    if not settings.is_admin(message.from_user.id if message.from_user else None):
        await message.answer(unauthorized_screen())
        return
    await _show_admin_home(message, store)


@router.message(Command("help"))
async def cmd_help(message: Message, bot: Bot, store: MongoStore, settings: Settings) -> None:
    if not await _ensure_user_access(message, bot, store, settings):
        return
    await message.answer(help_screen(), reply_markup=main_menu_keyboard())


@router.chat_join_request()
async def chat_join_request(update: ChatJoinRequest, store: MongoStore) -> None:
    chat = update.chat
    await store.record_force_request(
        update.from_user.id,
        chat.id,
        username=getattr(chat, "username", None),
        title=getattr(chat, "title", None),
    )


@router.callback_query(F.data.in_({"fs:check", "fs:continue"}))
async def cb_force_check(call: CallbackQuery, bot: Bot, store: MongoStore, settings: Settings) -> None:
    user = await store.upsert_user(call.from_user)
    missing = await _missing_force_channels(bot, store, call.from_user.id)
    if missing:
        await _send_or_edit(call, force_subscription_screen(missing), force_gate_keyboard(missing))
        return
    config = await store.runtime_config()
    await _send_or_edit(
        call,
        main_caption(str(config.get("start_caption") or ""), user),
        main_menu_keyboard(),
        photo_url=str(config.get("start_photo_url") or ""),
    )
    await store.add_log("force_subscription", "Force-subscription check passed", user_id=user["user_id"])


@router.callback_query(F.data == "menu:home")
async def cb_home(call: CallbackQuery, bot: Bot, store: MongoStore, settings: Settings) -> None:
    if not await _ensure_user_access(call, bot, store, settings):
        return
    config = await store.runtime_config()
    await _send_or_edit(
        call,
        main_caption(str(config.get("start_caption") or ""), await store.get_user(call.from_user.id)),
        main_menu_keyboard(),
        photo_url=str(config.get("start_photo_url") or ""),
    )


@router.callback_query(F.data.startswith("cat:"))
async def cb_category(call: CallbackQuery, bot: Bot, store: MongoStore, settings: Settings) -> None:
    if not await _ensure_user_access(call, bot, store, settings):
        return
    category = call.data.split(":", 1)[1]
    if category not in {STYLE_CATEGORY, UTILITY_CATEGORY}:
        await call.answer("Unknown category.", show_alert=True)
        return
    await _send_or_edit(call, category_screen(category), category_keyboard(category))


@router.callback_query(F.data.startswith("tool:"))
async def cb_tool(call: CallbackQuery, bot: Bot, store: MongoStore, settings: Settings) -> None:
    if not await _ensure_user_access(call, bot, store, settings):
        return
    tool_key = call.data.split(":", 1)[1]
    if tool_key not in TOOLS:
        await call.answer("Unknown tool.", show_alert=True)
        return
    await store.set_pending_tool(call.from_user.id, tool_key)
    await _send_or_edit(call, tool_prompt(tool_key), tool_prompt_keyboard(TOOLS[tool_key].category))


@router.callback_query(F.data.startswith("retry:"))
async def cb_retry(call: CallbackQuery, bot: Bot, store: MongoStore, settings: Settings) -> None:
    if not await _ensure_user_access(call, bot, store, settings):
        return
    tool_key = call.data.split(":", 1)[1]
    if tool_key not in TOOLS:
        await call.answer("Unknown tool.", show_alert=True)
        return
    await store.set_pending_tool(call.from_user.id, tool_key)
    await _send_or_edit(call, tool_prompt(tool_key), tool_prompt_keyboard(TOOLS[tool_key].category))


@router.callback_query(F.data == "copy:result")
async def cb_copy_result(call: CallbackQuery) -> None:
    await call.answer("Long-press the result block, then choose Copy. Telegram does not allow bots to copy automatically.", show_alert=True)


@router.callback_query(F.data == "menu:profile")
async def cb_profile(call: CallbackQuery, bot: Bot, store: MongoStore, settings: Settings) -> None:
    user = await _ensure_user_access(call, bot, store, settings)
    if not user:
        return
    saved_tasks = await store.count_saved_tasks(call.from_user.id)
    config = await store.runtime_config()
    await _send_or_edit(
        call,
        profile_screen(user, saved_tasks, int(config.get("free_daily_limit", settings.free_daily_limit)), int(config.get("premium_daily_limit", settings.premium_daily_limit))),
        profile_keyboard(),
    )


@router.callback_query(F.data == "menu:premium")
async def cb_premium(call: CallbackQuery, bot: Bot, store: MongoStore, settings: Settings) -> None:
    user = await _ensure_user_access(call, bot, store, settings)
    if not user:
        return
    config = await store.runtime_config()
    await _send_or_edit(call, premium_screen(user, int(config.get("premium_daily_limit", settings.premium_daily_limit))), premium_keyboard())


@router.callback_query(F.data.startswith("premium:"))
async def cb_premium_action(call: CallbackQuery, store: MongoStore, settings: Settings) -> None:
    user = await store.upsert_user(call.from_user)
    action = call.data.split(":")
    if len(action) == 3 and action[1] == "buy":
        days = int(action[2])
        if days not in {30, 90, 365}:
            await call.answer("Unknown premium plan.", show_alert=True)
            return
        stars = {30: 250, 90: 650, 365: 1900}.get(days, 250)
        await call.answer()
        await call.message.answer_invoice(
            title=f"{days} Days Premium",
            description="Premium access for higher daily limits and priority text processing.",
            payload=f"premium:{days}:{call.from_user.id}",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label=f"{days} Days Premium", amount=stars)],
        )
        return
    config = await store.runtime_config()
    await _send_or_edit(call, premium_screen(user, int(config.get("premium_daily_limit", settings.premium_daily_limit))), premium_keyboard())


@router.pre_checkout_query()
async def pre_checkout(pre_checkout_query: PreCheckoutQuery) -> None:
    payload = pre_checkout_query.invoice_payload or ""
    ok = _parse_premium_payload(payload) is not None
    await pre_checkout_query.answer(ok=ok, error_message=None if ok else "Invalid premium payment request.")


@router.message(F.successful_payment)
async def successful_payment(message: Message, store: MongoStore) -> None:
    payment = message.successful_payment
    payload = payment.invoice_payload if payment else ""
    try:
        parsed = _parse_premium_payload(payload)
        if not parsed:
            raise ValueError("invalid premium payload")
        days, user_id = parsed
        if int(user_id) != message.from_user.id:
            raise ValueError("payment user mismatch")
        premium_until = await store.activate_premium(message.from_user.id, days, source="telegram_stars")
        await message.answer(
            f"💎 {bold_unicode('PREMIUM ACTIVE')}\n\nYour premium is active until {premium_until.strftime('%d %b %Y')}."
        )
    except Exception:
        await store.add_log("payment", f"Could not activate payment payload {payload}", user_id=message.from_user.id)
        await message.answer(f"⚠️ {bold_unicode('ACTIVATION FAILED')}\n\nPayment was received, but premium activation failed. Please contact support.")


@router.callback_query(F.data == "menu:referral")
async def cb_referral(call: CallbackQuery, bot: Bot, store: MongoStore, settings: Settings) -> None:
    user = await _ensure_user_access(call, bot, store, settings)
    if not user:
        return
    bot_username = None
    try:
        me = await bot.get_me()
        bot_username = me.username
    except Exception:
        bot_username = None
    config = await store.runtime_config()
    await _send_or_edit(
        call,
        referral_screen(
            user,
            bot_username,
            bool(config.get("referral_rewards_enabled", False)),
            int(config.get("referral_required_joins", 3)),
            int(config.get("referral_reward_days", 7)),
        ),
        referral_keyboard(),
    )


@router.callback_query(F.data.startswith("referral:"))
async def cb_referral_action(call: CallbackQuery, bot: Bot, store: MongoStore) -> None:
    user = await store.upsert_user(call.from_user)
    bot_username = None
    try:
        bot_username = (await bot.get_me()).username
    except Exception:
        pass
    config = await store.runtime_config()
    await _send_or_edit(
        call,
        referral_screen(
            user,
            bot_username,
            bool(config.get("referral_rewards_enabled", False)),
            int(config.get("referral_required_joins", 3)),
            int(config.get("referral_reward_days", 7)),
        ),
        referral_keyboard(),
    )


@router.callback_query(F.data == "menu:settings")
async def cb_settings(call: CallbackQuery, bot: Bot, store: MongoStore, settings: Settings) -> None:
    user = await _ensure_user_access(call, bot, store, settings)
    if not user:
        return
    user_settings = user.get("settings", {})
    await _send_or_edit(
        call,
        settings_screen(user),
        settings_keyboard(
            user_settings.get("save_results", True),
            user_settings.get("notifications", True),
            user_settings.get("privacy_mode", False),
        ),
    )


@router.callback_query(F.data.startswith("settings:"))
async def cb_settings_action(call: CallbackQuery, bot: Bot, store: MongoStore, settings: Settings) -> None:
    user = await _ensure_user_access(call, bot, store, settings)
    if not user:
        return
    action = call.data.split(":", 1)[1]
    user_settings = user.get("settings", {})
    if action == "toggle_save":
        await store.set_user_setting(call.from_user.id, "save_results", not user_settings.get("save_results", True))
    elif action == "toggle_notify":
        await store.set_user_setting(call.from_user.id, "notifications", not user_settings.get("notifications", True))
    elif action == "toggle_privacy":
        await store.set_user_setting(call.from_user.id, "privacy_mode", not user_settings.get("privacy_mode", False))
    elif action == "confirm_clear_tasks":
        await _send_or_edit(call, f"🧹 {bold_unicode('CONFIRM CLEAR HISTORY')}\n\nThis will delete all saved tasks.", confirm_keyboard("settings:clear_tasks", "menu:tasks"))
        return
    elif action == "clear_tasks":
        deleted = await store.clear_tasks(call.from_user.id)
        await call.answer(f"Cleared {deleted} task(s).")
    elif action == "confirm_clear_data":
        await _send_or_edit(call, f"🧹 {bold_unicode('CONFIRM CLEAR DATA')}\n\nThis will delete task history and recent result data.", confirm_keyboard("settings:clear_data", "menu:settings"))
        return
    elif action == "clear_data":
        deleted = await store.clear_tasks(call.from_user.id)
        await store.set_user_fields(call.from_user.id, {"last_result": None, "pending_tool": None})
        await call.answer(f"Cleared {deleted} task(s) and recent result data.")
    elif action == "confirm_reset":
        await _send_or_edit(call, f"♻️ {bold_unicode('CONFIRM RESET SETTINGS')}\n\nThis will restore default user preferences.", confirm_keyboard("settings:reset_defaults", "menu:settings"))
        return
    elif action == "reset_defaults":
        await store.set_user_fields(
            call.from_user.id,
            {
                "settings": {
                    "language": "English",
                    "save_results": True,
                    "notifications": True,
                    "privacy_mode": False,
                    "default_output_style": "Clean",
                }
            },
        )
        await call.answer("Settings reset.")
    elif action == "terms":
        await _send_or_edit(call, terms_screen(), settings_keyboard())
        return
    elif action == "language":
        await _send_or_edit(call, f"🌐 {bold_unicode('LANGUAGE')}\n\nSelect your preferred language.", language_keyboard())
        return
    elif action == "style":
        await _send_or_edit(call, f"🎨 {bold_unicode('DEFAULT OUTPUT STYLE')}\n\nSelect how results should be presented.", output_style_keyboard())
        return
    elif action.startswith("lang:"):
        language = action.split(":", 1)[1]
        await store.set_user_setting(call.from_user.id, "language", language)
        await call.answer(f"Language set to {language}.")
    elif action.startswith("style:set:"):
        style = action.rsplit(":", 1)[1]
        await store.set_user_setting(call.from_user.id, "default_output_style", style)
        await call.answer(f"Default output style set to {style}.")
    user = await store.get_user(call.from_user.id) or user
    user_settings = user.get("settings", {})
    await _send_or_edit(
        call,
        settings_screen(user),
        settings_keyboard(
            user_settings.get("save_results", True),
            user_settings.get("notifications", True),
            user_settings.get("privacy_mode", False),
        ),
    )


@router.callback_query(F.data == "menu:help")
async def cb_help(call: CallbackQuery, bot: Bot, store: MongoStore, settings: Settings) -> None:
    if not await _ensure_user_access(call, bot, store, settings):
        return
    await _send_or_edit(call, help_screen(), main_menu_keyboard())


@router.callback_query(F.data == "menu:support")
async def cb_support(call: CallbackQuery, bot: Bot, store: MongoStore, settings: Settings) -> None:
    if not await _ensure_user_access(call, bot, store, settings):
        return
    config = await store.runtime_config()
    support_username = str(config.get("support_username") or "").lstrip("@")
    update_channel = str(config.get("update_channel") or "").lstrip("@")
    await _send_or_edit(call, support_screen(support_username, update_channel), support_keyboard(support_username, update_channel))


@router.callback_query(F.data == "menu:status")
async def cb_status(call: CallbackQuery, bot: Bot, store: MongoStore, settings: Settings) -> None:
    if not await _ensure_user_access(call, bot, store, settings):
        return
    counts = await store.counts()
    maintenance = await store.is_maintenance()
    config = await store.runtime_config()
    await _send_or_edit(call, system_status_screen(counts, _uptime(), maintenance, int(config.get("cooldown_seconds", 2))), main_menu_keyboard())


@router.callback_query(F.data == "menu:tasks")
async def cb_tasks(call: CallbackQuery, bot: Bot, store: MongoStore, settings: Settings) -> None:
    if not await _ensure_user_access(call, bot, store, settings):
        return
    tasks = await store.recent_tasks(call.from_user.id)
    await _send_or_edit(call, tasks_screen(tasks), tasks_keyboard(tasks))


@router.callback_query(F.data == "task:save_latest")
async def cb_save_latest(call: CallbackQuery, store: MongoStore) -> None:
    last = await store.get_last_result(call.from_user.id)
    if not last:
        await call.answer("No recent result to save.", show_alert=True)
        return
    if last.get("task_id"):
        await call.answer("This result is already saved in My Tasks.")
        return
    task_id = await store.add_task(
        call.from_user.id,
        last["tool_key"],
        last["tool_title"],
        last["original"],
        last["result"],
    )
    last["task_id"] = task_id
    await store.set_last_result(call.from_user.id, last)
    await call.answer("Saved to My Tasks.")
    tool = TOOLS.get(last["tool_key"])
    if tool:
        await _send_or_edit(
            call,
            result_screen(last["tool_key"], last["original"], last["result"]),
            result_keyboard(tool, saved=True),
        )


@router.callback_query(F.data.startswith("task:open:"))
async def cb_task_open(call: CallbackQuery, bot: Bot, store: MongoStore, settings: Settings) -> None:
    if not await _ensure_user_access(call, bot, store, settings):
        return
    task_id = call.data.rsplit(":", 1)[1]
    task = await store.get_task(call.from_user.id, task_id)
    if not task:
        await call.answer("Task not found.", show_alert=True)
        return
    await _send_or_edit(call, task_detail_screen(task), task_detail_keyboard(task_id))


@router.callback_query(F.data.startswith("task:delete_ask:"))
async def cb_task_delete_ask(call: CallbackQuery, bot: Bot, store: MongoStore, settings: Settings) -> None:
    if not await _ensure_user_access(call, bot, store, settings):
        return
    task_id = call.data.rsplit(":", 1)[1]
    task = await store.get_task(call.from_user.id, task_id)
    if not task:
        await call.answer("Task not found.", show_alert=True)
        return
    await _send_or_edit(
        call,
        f"🗑️ {bold_unicode('CONFIRM DELETE TASK')}\n\nThis saved result will be removed from My Tasks.",
        confirm_keyboard(f"task:delete_confirm:{task_id}", f"task:open:{task_id}"),
    )


@router.callback_query(F.data.startswith("task:delete_confirm:"))
async def cb_task_delete(call: CallbackQuery, bot: Bot, store: MongoStore, settings: Settings) -> None:
    if not await _ensure_user_access(call, bot, store, settings):
        return
    task_id = call.data.rsplit(":", 1)[1]
    deleted = await store.delete_task(call.from_user.id, task_id)
    await call.answer("Deleted." if deleted else "Task not found.")
    tasks = await store.recent_tasks(call.from_user.id)
    await _send_or_edit(call, tasks_screen(tasks), tasks_keyboard(tasks))


@router.callback_query(F.data.startswith("admin:"))
async def cb_admin(call: CallbackQuery, bot: Bot, store: MongoStore, settings: Settings) -> None:
    if not settings.is_admin(call.from_user.id):
        await _send_or_edit(call, unauthorized_screen(), main_menu_keyboard())
        return
    data = call.data
    if data == "admin:home":
        await _show_admin_home(call, store)
    elif data == "admin:stats":
        await _send_or_edit(call, admin_stats_screen(await store.counts()), admin_back_keyboard())
    elif data == "admin:broadcast":
        await _send_or_edit(call, admin_broadcast_screen(), admin_broadcast_keyboard())
    elif data == "admin:broadcast:start":
        await store.set_admin_action(call.from_user.id, "broadcast_waiting")
        await _send_or_edit(call, f"📣 {bold_unicode('BROADCAST')}\n\nSend the broadcast message now. Use /cancel to stop.", admin_back_keyboard())
    elif data == "admin:premium":
        await _send_or_edit(call, f"💎 {bold_unicode('PREMIUM MANAGEMENT')}\n\nAdd or remove premium access by Telegram ID.", admin_premium_keyboard())
    elif data == "admin:premium:add":
        await store.set_admin_action(call.from_user.id, "premium_add")
        await _send_or_edit(call, f"➕ {bold_unicode('ADD PREMIUM')}\n\nSend: <code>user_id days</code>\nExample: <code>123456789 30</code>", admin_back_keyboard())
    elif data == "admin:premium:remove":
        await store.set_admin_action(call.from_user.id, "premium_remove")
        await _send_or_edit(call, f"➖ {bold_unicode('REMOVE PREMIUM')}\n\nSend the Telegram user ID to remove premium.", admin_back_keyboard())
    elif data == "admin:force":
        channels = await store.list_force_channels(enabled_only=False)
        config = await store.runtime_config()
        enabled = bool(config.get("force_subscription_enabled", True))
        await _send_or_edit(call, admin_force_screen(channels, enabled), admin_force_keyboard(channels, enabled))
    elif data == "admin:force:toggle":
        enabled = await store.toggle_config_bool("force_subscription_enabled", True)
        channels = await store.list_force_channels(enabled_only=False)
        await _send_or_edit(call, admin_force_screen(channels, enabled), admin_force_keyboard(channels, enabled))
    elif data.startswith("admin:force:channel_toggle:"):
        channel_id = data.rsplit(":", 1)[1]
        channels = await store.list_force_channels(enabled_only=False)
        target = next((channel for channel in channels if str(channel.get("_id")) == channel_id), None)
        if not target:
            await call.answer("Force channel not found.", show_alert=True)
            return
        await store.set_force_channel_enabled(channel_id, not bool(target.get("enabled", True)))
        config = await store.runtime_config()
        channels = await store.list_force_channels(enabled_only=False)
        enabled = bool(config.get("force_subscription_enabled", True))
        await _send_or_edit(call, admin_force_screen(channels, enabled), admin_force_keyboard(channels, enabled))
    elif data == "admin:force:add":
        await store.set_admin_action(call.from_user.id, "force_add")
        await _send_or_edit(
            call,
            f"➕ {bold_unicode('ADD FORCE CHANNEL')}\n\nSend channel username, ID, invite link, or forward a channel post.\n\nOptional: add <code>join</code> or <code>request</code> after it.",
            admin_back_keyboard(),
        )
    elif data.startswith("admin:force:delete_ask:"):
        channel_id = data.rsplit(":", 1)[1]
        await _send_or_edit(
            call,
            f"🗑️ {bold_unicode('CONFIRM DELETE CHANNEL')}\n\nThis force-subscription target will be removed.",
            confirm_keyboard(f"admin:force:delete_confirm:{channel_id}", "admin:force"),
        )
    elif data.startswith("admin:force:delete_confirm:"):
        channel_id = data.rsplit(":", 1)[1]
        await store.delete_force_channel(channel_id)
        channels = await store.list_force_channels(enabled_only=False)
        config = await store.runtime_config()
        enabled = bool(config.get("force_subscription_enabled", True))
        await _send_or_edit(call, admin_force_screen(channels, enabled), admin_force_keyboard(channels, enabled))
    elif data == "admin:referrals":
        config = await store.runtime_config()
        await _send_or_edit(call, admin_referral_screen(config), admin_referral_keyboard(bool(config.get("referral_rewards_enabled", False))))
    elif data == "admin:referrals:toggle":
        enabled = await store.toggle_config_bool("referral_rewards_enabled", False)
        config = await store.runtime_config()
        await _send_or_edit(call, admin_referral_screen(config), admin_referral_keyboard(enabled))
    elif data == "admin:referrals:required":
        await store.set_admin_action(call.from_user.id, "referral_required")
        await _send_or_edit(call, f"🎯 {bold_unicode('REQUIRED REFERRALS')}\n\nSend the required valid referral count.\nExample: <code>3</code>", admin_back_keyboard())
    elif data == "admin:referrals:days":
        await store.set_admin_action(call.from_user.id, "referral_days")
        await _send_or_edit(call, f"💎 {bold_unicode('REWARD DURATION')}\n\nSend the premium reward duration in days.\nExample: <code>7</code>", admin_back_keyboard())
    elif data == "admin:referrals:leaderboard":
        await _send_or_edit(call, referral_leaderboard_screen(await store.referral_leaderboard()), admin_back_keyboard())
    elif data == "admin:ban":
        await _send_or_edit(call, f"{bold_unicode('BAN / UNBAN USERS')}\n\nChoose an action.", admin_ban_keyboard())
    elif data == "admin:ban:add":
        await store.set_admin_action(call.from_user.id, "ban_add")
        await _send_or_edit(call, f"🚫 {bold_unicode('BAN USER')}\n\nSend the Telegram user ID to ban.", admin_back_keyboard())
    elif data == "admin:ban:remove":
        await store.set_admin_action(call.from_user.id, "ban_remove")
        await _send_or_edit(call, f"✅ {bold_unicode('UNBAN USER')}\n\nSend the Telegram user ID to unban.", admin_back_keyboard())
    elif data == "admin:maintenance":
        new_value = await store.toggle_maintenance()
        await _send_or_edit(call, f"🛠️ {bold_unicode('MAINTENANCE MODE')}\n\nStatus: {'On ✅' if new_value else 'Off ⭕'}", admin_back_keyboard())
    elif data == "admin:settings":
        config = await store.runtime_config()
        await _send_or_edit(call, admin_bot_settings_screen(config), admin_bot_settings_keyboard())
    elif data.startswith("admin:settings:set:"):
        key = data.rsplit(":", 1)[1]
        await store.set_admin_action(call.from_user.id, f"bot_setting:{key}")
        await _send_or_edit(call, _bot_setting_prompt(key), admin_back_keyboard())
    elif data == "admin:logs":
        await _send_or_edit(call, logs_screen(await store.recent_logs()), admin_back_keyboard())
    else:
        await call.answer("Unknown admin action.", show_alert=True)


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, store: MongoStore, settings: Settings) -> None:
    if message.from_user and settings.is_admin(message.from_user.id):
        await store.set_admin_action(message.from_user.id, None)
    if message.from_user:
        await store.set_pending_tool(message.from_user.id, None)
    await message.answer(cancelled_screen(), reply_markup=main_menu_keyboard())


@router.message()
async def incoming_message(message: Message, bot: Bot, store: MongoStore, settings: Settings) -> None:
    if not message.from_user:
        return
    await store.upsert_user(message.from_user)
    if settings.is_admin(message.from_user.id):
        handled = await _handle_admin_action(message, bot, store)
        if handled:
            return

    user = await _ensure_user_access(message, bot, store, settings)
    if not user:
        return
    text = message.text or message.caption or ""
    tool_key = await store.get_pending_tool(message.from_user.id)
    if not tool_key:
        await message.answer(
            choose_tool_first_screen(),
            reply_markup=main_menu_keyboard(),
        )
        return
    if not text.strip():
        await message.answer(empty_input_screen())
        return
    config = await store.runtime_config()
    max_text_chars = int(config.get("max_text_chars", settings.max_text_chars))
    if len(text) > max_text_chars:
        await message.answer(too_long_screen(max_text_chars))
        return
    usage_allowed, usage_message = await _usage_guard(message, user, store, settings, config)
    if not usage_allowed:
        await message.answer(usage_message, reply_markup=premium_keyboard() if "LIMIT" in usage_message else main_menu_keyboard())
        return

    tool = TOOLS[tool_key]
    processing_message = await message.answer(processing_screen(tool_key))
    started = utcnow()
    try:
        result = process_tool(tool_key, text)
    except Exception as exc:
        logger.exception("tool processing failed for %s", tool_key)
        await store.add_log("error", f"Tool processing failed for {tool_key}: {type(exc).__name__}", user_id=message.from_user.id)
        await _safe_edit_or_answer(processing_message, processing_error_screen())
        return
    if not result:
        await _safe_edit_or_answer(processing_message, empty_input_screen())
        return

    task_id = None
    current_user = await store.get_user(message.from_user.id) or user
    user_preferences = current_user.get("settings", {})
    privacy_mode = bool(user_preferences.get("privacy_mode", False))
    if user_preferences.get("save_results", True) and not privacy_mode:
        task_id = await store.add_task(message.from_user.id, tool_key, tool.title, text, result)
    if privacy_mode:
        await store.set_last_result(message.from_user.id, None)
    else:
        await store.set_last_result(
            message.from_user.id,
            {"tool_key": tool_key, "tool_title": tool.title, "original": text, "result": result, "task_id": task_id},
        )
    duration_ms = int((utcnow() - started).total_seconds() * 1000)
    await store.add_log("tool", f"{tool.title} completed in {duration_ms}ms", user_id=message.from_user.id)
    await _safe_edit_or_answer(processing_message, result_screen(tool_key, text, result), reply_markup=result_keyboard(tool, saved=bool(task_id)))


async def _handle_admin_action(message: Message, bot: Bot, store: MongoStore) -> bool:
    session = await store.get_admin_action(message.from_user.id)
    if not session:
        return False
    action = session.get("action")
    if action == "broadcast_waiting":
        await store.set_admin_action(message.from_user.id, None)
        await _run_broadcast(message, bot, store)
        return True
    if not message.text:
        await message.answer(empty_input_screen(), reply_markup=admin_back_keyboard())
        return True
    text = message.text.strip()
    try:
        if action == "premium_add":
            user_id, days = _parse_user_days(text)
            until = await store.activate_premium(user_id, days, source=f"admin:{message.from_user.id}")
            await message.answer(f"💎 {bold_unicode('PREMIUM ACTIVATED')}\n\nUser {user_id} is premium until {until.strftime('%d %b %Y')}.", reply_markup=admin_premium_keyboard())
        elif action == "premium_remove":
            await store.remove_premium(int(text))
            await message.answer(f"✅ {bold_unicode('PREMIUM REMOVED')}\n\nPremium access removed for {text}.", reply_markup=admin_premium_keyboard())
        elif action == "force_add":
            target, label, invite_link, mode = _parse_force_channel(message)
            await store.add_force_channel(target, label, invite_link=invite_link, mode=mode)
            channels = await store.list_force_channels(enabled_only=False)
            config = await store.runtime_config()
            enabled = bool(config.get("force_subscription_enabled", True))
            await message.answer(admin_force_screen(channels, enabled), reply_markup=admin_force_keyboard(channels, enabled))
        elif action == "referral_required":
            value = _parse_positive_int(text, "required joins")
            await store.set_config("referral_required_joins", value)
            config = await store.runtime_config()
            await message.answer(admin_referral_screen(config), reply_markup=admin_referral_keyboard(bool(config.get("referral_rewards_enabled", False))))
        elif action == "referral_days":
            value = _parse_positive_int(text, "reward days")
            await store.set_config("referral_reward_days", value)
            config = await store.runtime_config()
            await message.answer(admin_referral_screen(config), reply_markup=admin_referral_keyboard(bool(config.get("referral_rewards_enabled", False))))
        elif action and action.startswith("bot_setting:"):
            key = action.split(":", 1)[1]
            value = _parse_bot_setting_value(key, text)
            await store.set_config(key, value)
            config = await store.runtime_config()
            await message.answer(admin_bot_settings_screen(config), reply_markup=admin_bot_settings_keyboard())
        elif action == "ban_add":
            await store.set_ban(int(text), True)
            await message.answer(f"🚫 {bold_unicode('USER BANNED')}\n\nUser {text} is now banned.", reply_markup=admin_ban_keyboard())
        elif action == "ban_remove":
            await store.set_ban(int(text), False)
            await message.answer(f"✅ {bold_unicode('USER UNBANNED')}\n\nUser {text} can use the bot again.", reply_markup=admin_ban_keyboard())
        else:
            await message.answer(f"⚠️ {bold_unicode('UNKNOWN ADMIN ACTION')}", reply_markup=admin_back_keyboard())
    except Exception as exc:
        await message.answer(f"⚠️ {bold_unicode('INVALID INPUT')}\n\n{type(exc).__name__}. Please try again.", reply_markup=admin_back_keyboard())
        return True
    await store.set_admin_action(message.from_user.id, None)
    return True


async def _run_broadcast(message: Message, bot: Bot, store: MongoStore) -> None:
    user_ids = await store.all_user_ids()
    total = len(user_ids)
    sent = 0
    failed = 0
    progress = await message.answer(f"📣 {bold_unicode('BROADCAST STARTED')}\n\nTotal users: {total}\nSent: 0\nFailed: 0")
    for idx, user_id in enumerate(user_ids, start=1):
        try:
            await bot.copy_message(
                chat_id=user_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
                reply_markup=message.reply_markup,
            )
            sent += 1
        except TelegramRetryAfter as exc:
            await asyncio.sleep(exc.retry_after)
            failed += 1
        except (TelegramForbiddenError, TelegramBadRequest):
            failed += 1
        except Exception:
            failed += 1
        if idx % 25 == 0 or idx == total:
            try:
                await progress.edit_text(
                    f"📣 {bold_unicode('BROADCAST PROGRESS')}\n\nTotal users: {total}\nSent: {sent}\nFailed: {failed}\nStatus: Running"
                )
            except TelegramBadRequest:
                pass
        await asyncio.sleep(0.03)
    await store.record_broadcast(message.from_user.id, total, sent, failed)
    await progress.edit_text(
        f"✅ {bold_unicode('BROADCAST COMPLETED')}\n\nTotal users: {total}\nSent: {sent}\nFailed: {failed}\nStatus: Completed",
        reply_markup=admin_back_keyboard(),
    )


async def _ensure_user_access(
    event: Message | CallbackQuery,
    bot: Bot,
    store: MongoStore,
    settings: Settings,
    referral_arg: str | None = None,
) -> dict[str, Any] | None:
    user = await store.upsert_user(event.from_user, referral_arg=referral_arg)
    if user.get("is_banned"):
        await _send_or_edit(event, f"🔒 {bold_unicode('ACCESS RESTRICTED')}\n\nYour account is restricted from using this bot.")
        return None
    if await store.is_maintenance() and not settings.is_admin(event.from_user.id):
        await _send_or_edit(event, f"🛠️ {bold_unicode('MAINTENANCE MODE')}\n\nThe bot is temporarily under maintenance. Please try again later.")
        return None
    missing = await _missing_force_channels(bot, store, event.from_user.id)
    if missing and not settings.is_admin(event.from_user.id):
        await _send_or_edit(event, force_subscription_screen(missing), force_gate_keyboard(missing))
        return None
    return user


async def _missing_force_channels(bot: Bot, store: MongoStore, user_id: int) -> list[dict[str, Any]]:
    if not bool(await store.get_config("force_subscription_enabled", True)):
        return []
    channels = await store.list_force_channels(enabled_only=True)
    missing: list[dict[str, Any]] = []
    for channel in channels:
        target = channel.get("target", "")
        check_target = _checkable_target(target)
        if not check_target:
            missing.append(channel)
            continue
        try:
            member = await bot.get_chat_member(check_target, user_id)
            status = getattr(member.status, "value", str(member.status))
            is_restricted_member = status == "restricted" and bool(getattr(member, "is_member", False))
            if status not in {"member", "administrator", "creator"} and not is_restricted_member:
                if channel.get("mode") == "request" and await store.has_force_request(user_id, target):
                    continue
                missing.append(channel)
        except Exception:
            if channel.get("mode") == "request" and await store.has_force_request(user_id, target):
                continue
            missing.append(channel)
    return missing


def _checkable_target(target: str) -> str:
    if target.startswith("@") or target.startswith("-100") or target.lstrip("-").isdigit():
        return target
    if target.startswith("https://t.me/"):
        suffix = target.removeprefix("https://t.me/").strip("/")
        if suffix and "/" not in suffix and not suffix.startswith("+"):
            return "@" + suffix
    return ""


async def _usage_guard(
    message: Message,
    user: dict[str, Any],
    store: MongoStore,
    settings: Settings,
    config: dict[str, Any],
) -> tuple[bool, str]:
    active_premium = _premium_active(user)
    if user.get("is_premium") and not active_premium:
        await store.remove_premium(message.from_user.id)
    now = utcnow()
    restricted_until = user.get("restricted_until")
    if isinstance(restricted_until, datetime):
        if restricted_until.tzinfo is None:
            restricted_until = restricted_until.replace(tzinfo=UTC)
        if restricted_until > now:
            return False, f"⏳ {bold_unicode('TEMPORARILY RESTRICTED')}\n\nPlease wait before using another tool."

    cooldown_seconds = max(0, int(config.get("cooldown_seconds", 2)))
    last_tool_at = user.get("last_tool_at")
    if not active_premium and cooldown_seconds and isinstance(last_tool_at, datetime):
        if last_tool_at.tzinfo is None:
            last_tool_at = last_tool_at.replace(tzinfo=UTC)
        elapsed = (now - last_tool_at).total_seconds()
        if elapsed < cooldown_seconds:
            hits = int(user.get("rate_limit_hits", 0)) + 1
            fields: dict[str, Any] = {"rate_limit_hits": hits}
            if hits >= 3:
                fields["restricted_until"] = now + timedelta(seconds=60)
                fields["rate_limit_hits"] = 0
            await store.set_user_fields(message.from_user.id, fields)
            remaining = max(1, int(cooldown_seconds - elapsed))
            return False, f"⏱️ {bold_unicode('COOLDOWN ACTIVE')}\n\nPlease wait {remaining}s before sending another text."

    limit = int(config.get("premium_daily_limit", settings.premium_daily_limit)) if active_premium else int(config.get("free_daily_limit", settings.free_daily_limit))
    if user.get("usage_date") == today_key() and int(user.get("daily_usage", 0)) >= limit:
        return False, f"💎 {bold_unicode('DAILY LIMIT REACHED')}\n\nUpgrade to Premium for higher daily usage limits."
    await store.increment_usage(message.from_user.id)
    await store.set_user_fields(message.from_user.id, {"last_tool_at": now, "rate_limit_hits": 0})
    return True, ""


def _premium_active(user: dict[str, Any]) -> bool:
    premium_until = user.get("premium_until")
    if not user.get("is_premium") or not isinstance(premium_until, datetime):
        return False
    if premium_until.tzinfo is None:
        premium_until = premium_until.replace(tzinfo=UTC)
    return premium_until > datetime.now(UTC)


async def _show_admin_home(target: Message | CallbackQuery, store: MongoStore) -> None:
    await _send_or_edit(target, admin_home_screen(await store.counts(), await store.is_maintenance()), admin_keyboard())


async def _safe_edit_or_answer(message: Message, text: str, reply_markup: Any = None) -> None:
    try:
        await message.edit_text(text, reply_markup=reply_markup, disable_web_page_preview=True)
    except TelegramBadRequest:
        await message.answer(text, reply_markup=reply_markup, disable_web_page_preview=True)


async def _send_or_edit(
    target: Message | CallbackQuery,
    text: str,
    reply_markup: Any = None,
    photo_url: str = "",
) -> None:
    if isinstance(target, CallbackQuery):
        try:
            await target.answer()
        except TelegramBadRequest:
            pass
        if not target.message:
            return
        try:
            if getattr(target.message, "photo", None):
                await target.message.edit_caption(caption=text, reply_markup=reply_markup)
            else:
                await target.message.edit_text(text, reply_markup=reply_markup, disable_web_page_preview=True)
            return
        except TelegramBadRequest:
            await target.message.answer(text, reply_markup=reply_markup, disable_web_page_preview=True)
            return

    if photo_url:
        try:
            await target.answer_photo(photo=photo_url, caption=text, reply_markup=reply_markup)
            return
        except TelegramBadRequest:
            pass
    await target.answer(text, reply_markup=reply_markup, disable_web_page_preview=True)


def _parse_user_days(text: str) -> tuple[int, int]:
    parts = text.replace(",", " ").split()
    if len(parts) < 2:
        raise ValueError("expected user_id days")
    days = _parse_positive_int(parts[1], "days")
    return int(parts[0]), days


def _parse_premium_payload(payload: str) -> tuple[int, int] | None:
    try:
        prefix, days_raw, user_id_raw = payload.split(":", 2)
        days = int(days_raw)
        user_id = int(user_id_raw)
    except (TypeError, ValueError):
        return None
    if prefix != "premium" or days not in {30, 90, 365} or user_id <= 0:
        return None
    return days, user_id


def _parse_positive_int(text: str, field: str) -> int:
    value = int(text.strip())
    if value <= 0:
        raise ValueError(f"{field} must be positive")
    return value


def _bot_setting_prompt(key: str) -> str:
    prompts = {
        "start_caption": f"📝 {bold_unicode('START CAPTION')}\n\nSend the new /start caption text. Send <code>default</code> to clear it.",
        "start_photo_url": f"🖼️ {bold_unicode('START PHOTO')}\n\nSend the start photo URL. Send <code>default</code> to clear it.",
        "support_username": f"🛟 {bold_unicode('SUPPORT USERNAME')}\n\nSend support username without @. Send <code>default</code> to clear it.",
        "update_channel": f"📣 {bold_unicode('UPDATE CHANNEL')}\n\nSend update channel username without @. Send <code>default</code> to clear it.",
        "free_daily_limit": f"📉 {bold_unicode('FREE DAILY LIMIT')}\n\nSend the free user daily limit as a number.",
        "premium_daily_limit": f"📈 {bold_unicode('PREMIUM DAILY LIMIT')}\n\nSend the premium user daily limit as a number.",
        "cooldown_seconds": f"⏱️ {bold_unicode('COOLDOWN SECONDS')}\n\nSend cooldown seconds as a number. Use <code>0</code> to disable cooldown.",
        "max_text_chars": f"✍️ {bold_unicode('MAX TEXT LENGTH')}\n\nSend maximum accepted text length as a number.",
    }
    return prompts.get(key, f"⚙️ {bold_unicode('BOT SETTING')}\n\nSend the new value.")


def _parse_bot_setting_value(key: str, text: str) -> str | int:
    value = text.strip()
    if value.casefold() in {"default", "none", "clear"}:
        numeric_defaults = {
            "free_daily_limit": 50,
            "premium_daily_limit": 500,
            "max_text_chars": 3000,
            "cooldown_seconds": 2,
        }
        if key in numeric_defaults:
            return numeric_defaults[key]
        return "" if key in {"start_caption", "start_photo_url", "support_username", "update_channel"} else 0
    if key in {"free_daily_limit", "premium_daily_limit", "max_text_chars"}:
        return _parse_positive_int(value, key)
    if key == "cooldown_seconds":
        parsed = int(value)
        if parsed < 0:
            raise ValueError("cooldown_seconds must not be negative")
        return parsed
    if key in {"support_username", "update_channel"}:
        return value.lstrip("@")
    if key == "start_photo_url" and value and not value.startswith(("http://", "https://")):
        raise ValueError("start_photo_url must be a URL")
    return value


def _parse_force_channel(message: Message) -> tuple[str, str, str, str]:
    forward_chat = getattr(message, "forward_from_chat", None)
    origin = getattr(message, "forward_origin", None)
    if not forward_chat and origin and hasattr(origin, "chat"):
        forward_chat = origin.chat
    mode = "request" if message.text and "request" in message.text.lower() else "join"
    if forward_chat:
        username = getattr(forward_chat, "username", None)
        target = f"@{username}" if username else str(forward_chat.id)
        label = getattr(forward_chat, "title", None) or target
        return target, label, "", mode
    text = (message.text or "").strip()
    if not text:
        raise ValueError("missing channel target")
    parts = text.split()
    target = parts[0]
    if any(part.lower() == "request" for part in parts[1:]):
        mode = "request"
    invite_link = target if target.startswith("https://t.me/") else ""
    label = target.replace("https://t.me/", "@") if target.startswith("https://t.me/") else target
    return target, label, invite_link, mode


def _uptime() -> str:
    seconds = int((utcnow() - STARTED_AT).total_seconds())
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    if days:
        return f"{days}d {hours}h {minutes}m"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"
