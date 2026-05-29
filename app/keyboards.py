from __future__ import annotations

from typing import Iterable

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.catalog import CATEGORY_TOOLS, STYLE_CATEGORY, UTILITY_CATEGORY, ToolDefinition
from app.text_style import bold_unicode


def btn(text: str, emoji: str = "") -> str:
    return f"{emoji} {bold_unicode(text)}".strip()


def keyboard(rows: Iterable[Iterable[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[list(row) for row in rows])


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return keyboard(
        [
            [InlineKeyboardButton(text=btn("My Profile", "👤"), callback_data="menu:profile")],
            [
                InlineKeyboardButton(text=btn("Premium", "💎"), callback_data="menu:premium"),
                InlineKeyboardButton(text=btn("Referral", "🎁"), callback_data="menu:referral"),
            ],
            [InlineKeyboardButton(text=btn("Settings", "⚙️"), callback_data="menu:settings")],
            [
                InlineKeyboardButton(text=btn("Help", "❓"), callback_data="menu:help"),
                InlineKeyboardButton(text=btn("Support", "🛟"), callback_data="menu:support"),
            ],
            [InlineKeyboardButton(text=f"1️⃣ {bold_unicode('TEXT STYLE & FONTS')}", callback_data=f"cat:{STYLE_CATEGORY}")],
            [InlineKeyboardButton(text=f"2️⃣ {bold_unicode('TEXT CLEANING & UTILITY')}", callback_data=f"cat:{UTILITY_CATEGORY}")],
            [
                InlineKeyboardButton(text=btn("My Tasks", "📂"), callback_data="menu:tasks"),
                InlineKeyboardButton(text=btn("System Status", "📊"), callback_data="menu:status"),
            ],
        ]
    )


def category_keyboard(category: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for tool in CATEGORY_TOOLS[category]:
        rows.append([InlineKeyboardButton(text=btn(tool.title, tool.emoji), callback_data=f"tool:{tool.key}")])
    rows.append(nav_row())
    return keyboard(rows)


def tool_prompt_keyboard(category: str) -> InlineKeyboardMarkup:
    return keyboard(
        [
            [
                InlineKeyboardButton(text=btn("Back to Tools", "🔙"), callback_data=f"cat:{category}"),
                InlineKeyboardButton(text=btn("Main Menu", "🏠"), callback_data="menu:home"),
            ],
            [
                InlineKeyboardButton(text=btn("My Tasks", "📂"), callback_data="menu:tasks"),
                InlineKeyboardButton(text=btn("Help", "❓"), callback_data="menu:help"),
            ],
        ]
    )


def nav_row(back_to: str = "menu:home") -> list[InlineKeyboardButton]:
    return [
        InlineKeyboardButton(text=btn("Back", "🔙"), callback_data=back_to),
        InlineKeyboardButton(text=btn("Main Menu", "🏠"), callback_data="menu:home"),
    ]


def result_keyboard(tool: ToolDefinition, saved: bool = False) -> InlineKeyboardMarkup:
    save_text = "Open My Tasks" if saved else "Save to My Tasks"
    save_callback = "menu:tasks" if saved else "task:save_latest"
    return keyboard(
        [
            [
                InlineKeyboardButton(text=btn("Try Again", "🔁"), callback_data=f"retry:{tool.key}"),
                InlineKeyboardButton(text=btn("Copy Result", "📋"), callback_data="copy:result"),
            ],
            [InlineKeyboardButton(text=btn(save_text, "📂"), callback_data=save_callback)],
            [
                InlineKeyboardButton(text=btn("Back to Category", "🔙"), callback_data=f"cat:{tool.category}"),
                InlineKeyboardButton(text=btn("Main Menu", "🏠"), callback_data="menu:home"),
            ],
        ]
    )


def profile_keyboard() -> InlineKeyboardMarkup:
    return keyboard([[InlineKeyboardButton(text=btn("My Tasks", "📂"), callback_data="menu:tasks")], nav_row()])


def premium_keyboard() -> InlineKeyboardMarkup:
    return keyboard(
        [
            [InlineKeyboardButton(text=btn("Upgrade", "💎"), callback_data="premium:upgrade")],
            [
                InlineKeyboardButton(text=btn("30 Days", "⭐"), callback_data="premium:buy:30"),
                InlineKeyboardButton(text=btn("90 Days", "⭐"), callback_data="premium:buy:90"),
            ],
            [InlineKeyboardButton(text=btn("Buy With Stars", "🌟"), callback_data="premium:buy:365")],
            [InlineKeyboardButton(text=btn("My Premium", "💎"), callback_data="premium:mine")],
            nav_row(),
        ]
    )


def referral_keyboard() -> InlineKeyboardMarkup:
    return keyboard(
        [
            [InlineKeyboardButton(text=btn("Invite Friends", "🎁"), callback_data="referral:invite")],
            [InlineKeyboardButton(text=btn("My Referrals", "👥"), callback_data="referral:mine")],
            nav_row(),
        ]
    )


def settings_keyboard(save_results: bool = True, notifications: bool = True, privacy_mode: bool = False) -> InlineKeyboardMarkup:
    save_label = btn("Auto Save On" if save_results else "Auto Save Off", "✅" if save_results else "⭕")
    notify_label = btn("Notifications On" if notifications else "Notifications Off", "✅" if notifications else "⭕")
    privacy_label = btn("Privacy Mode On" if privacy_mode else "Privacy Mode Off", "✅" if privacy_mode else "⭕")
    return keyboard(
        [
            [InlineKeyboardButton(text=btn("Language", "🌐"), callback_data="settings:language")],
            [InlineKeyboardButton(text=btn("Default Output Style", "🎨"), callback_data="settings:style")],
            [InlineKeyboardButton(text=save_label, callback_data="settings:toggle_save")],
            [InlineKeyboardButton(text=notify_label, callback_data="settings:toggle_notify")],
            [InlineKeyboardButton(text=privacy_label, callback_data="settings:toggle_privacy")],
            [
                InlineKeyboardButton(text=btn("Clear Data", "🧹"), callback_data="settings:confirm_clear_data"),
                InlineKeyboardButton(text=btn("Reset Settings", "♻️"), callback_data="settings:confirm_reset"),
            ],
            [
                InlineKeyboardButton(text=btn("Terms", "📄"), callback_data="settings:terms"),
                InlineKeyboardButton(text=btn("Support", "🛟"), callback_data="menu:support"),
            ],
            nav_row(),
        ]
    )


def language_keyboard() -> InlineKeyboardMarkup:
    return keyboard(
        [
            [InlineKeyboardButton(text=bold_unicode("English"), callback_data="settings:lang:English")],
            [InlineKeyboardButton(text=bold_unicode("Hindi"), callback_data="settings:lang:Hindi")],
            [InlineKeyboardButton(text=bold_unicode("Spanish"), callback_data="settings:lang:Spanish")],
            [InlineKeyboardButton(text=btn("Back", "🔙"), callback_data="menu:settings")],
        ]
    )


def output_style_keyboard() -> InlineKeyboardMarkup:
    return keyboard(
        [
            [InlineKeyboardButton(text=bold_unicode("Clean"), callback_data="settings:style:set:Clean")],
            [InlineKeyboardButton(text=bold_unicode("Compact"), callback_data="settings:style:set:Compact")],
            [InlineKeyboardButton(text=bold_unicode("Detailed"), callback_data="settings:style:set:Detailed")],
            [InlineKeyboardButton(text=btn("Back", "🔙"), callback_data="menu:settings")],
        ]
    )


def tasks_keyboard(tasks: list[dict]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for idx, task in enumerate(tasks, start=1):
        rows.append([InlineKeyboardButton(text=f"{idx}. {bold_unicode(task.get('tool_title', 'Task'))}", callback_data=f"task:open:{task['_id']}")])
    if tasks:
        rows.append([InlineKeyboardButton(text=btn("Clear History", "🧹"), callback_data="settings:confirm_clear_tasks")])
    rows.append(nav_row())
    return keyboard(rows)


def task_detail_keyboard(task_id: str) -> InlineKeyboardMarkup:
    return keyboard(
        [
            [
                InlineKeyboardButton(text=btn("Delete Task", "🗑️"), callback_data=f"task:delete_ask:{task_id}"),
                InlineKeyboardButton(text=btn("My Tasks", "📂"), callback_data="menu:tasks"),
            ],
            nav_row(),
        ]
    )


def confirm_keyboard(confirm_data: str, cancel_data: str = "menu:home") -> InlineKeyboardMarkup:
    return keyboard(
        [
            [
                InlineKeyboardButton(text=btn("Confirm", "✅"), callback_data=confirm_data),
                InlineKeyboardButton(text=btn("Cancel", "✖️"), callback_data=cancel_data),
            ]
        ]
    )


def support_keyboard(support_username: str, update_channel: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if support_username:
        rows.append([InlineKeyboardButton(text=btn("Contact Support", "🛟"), url=f"https://t.me/{support_username}")])
    if update_channel:
        rows.append([InlineKeyboardButton(text=btn("Update Channel", "📣"), url=f"https://t.me/{update_channel}")])
    rows.append(nav_row())
    return keyboard(rows)


def force_gate_keyboard(channels: list[dict]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for channel in channels:
        invite = channel.get("invite_link") or _target_url(channel.get("target", ""))
        if invite:
            rows.append([InlineKeyboardButton(text=btn("Join Now", "🔗"), url=invite)])
    rows.append([InlineKeyboardButton(text=btn("Check Access", "✅"), callback_data="fs:check")])
    rows.append([InlineKeyboardButton(text=btn("Continue", "➡️"), callback_data="fs:continue")])
    return keyboard(rows)


def admin_keyboard() -> InlineKeyboardMarkup:
    return keyboard(
        [
            [InlineKeyboardButton(text=btn("User Stats", "📈"), callback_data="admin:stats")],
            [InlineKeyboardButton(text=btn("Broadcast", "📣"), callback_data="admin:broadcast")],
            [InlineKeyboardButton(text=btn("Premium Management", "💎"), callback_data="admin:premium")],
            [InlineKeyboardButton(text=btn("Force Subscription", "🔐"), callback_data="admin:force")],
            [InlineKeyboardButton(text=btn("Referral Settings", "🎁"), callback_data="admin:referrals")],
            [InlineKeyboardButton(text=btn("Ban / Unban Users", "🚫"), callback_data="admin:ban")],
            [InlineKeyboardButton(text=btn("Maintenance Mode", "🛠️"), callback_data="admin:maintenance")],
            [InlineKeyboardButton(text=btn("Bot Settings", "⚙️"), callback_data="admin:settings")],
            [InlineKeyboardButton(text=btn("Logs & Error Monitoring", "🧾"), callback_data="admin:logs")],
        ]
    )


def admin_back_keyboard() -> InlineKeyboardMarkup:
    return keyboard([[InlineKeyboardButton(text=btn("Admin Panel", "🛠️"), callback_data="admin:home")]])


def admin_broadcast_keyboard() -> InlineKeyboardMarkup:
    return keyboard(
        [
            [InlineKeyboardButton(text=bold_unicode("START BROADCAST"), callback_data="admin:broadcast:start")],
            [InlineKeyboardButton(text=btn("Cancel", "✖️"), callback_data="admin:home")],
        ]
    )


def admin_referral_keyboard(rewards_enabled: bool) -> InlineKeyboardMarkup:
    toggle_text = "Rewards On" if rewards_enabled else "Rewards Off"
    return keyboard(
        [
            [InlineKeyboardButton(text=btn(toggle_text, "✅" if rewards_enabled else "⭕"), callback_data="admin:referrals:toggle")],
            [InlineKeyboardButton(text=btn("Set Required Joins", "🎯"), callback_data="admin:referrals:required")],
            [InlineKeyboardButton(text=btn("Set Reward Days", "💎"), callback_data="admin:referrals:days")],
            [InlineKeyboardButton(text=btn("Leaderboard", "🏆"), callback_data="admin:referrals:leaderboard")],
            [InlineKeyboardButton(text=btn("Admin Panel", "🔙"), callback_data="admin:home")],
        ]
    )


def admin_premium_keyboard() -> InlineKeyboardMarkup:
    return keyboard(
        [
            [InlineKeyboardButton(text=btn("Add Premium", "➕"), callback_data="admin:premium:add")],
            [InlineKeyboardButton(text=btn("Remove Premium", "➖"), callback_data="admin:premium:remove")],
            [InlineKeyboardButton(text=btn("Admin Panel", "🔙"), callback_data="admin:home")],
        ]
    )


def admin_force_keyboard(channels: list[dict], enabled: bool = True) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text=btn("Force Subscription On" if enabled else "Force Subscription Off", "✅" if enabled else "⭕"),
                callback_data="admin:force:toggle",
            )
        ],
        [InlineKeyboardButton(text=btn("Add Channel", "➕"), callback_data="admin:force:add")]
    ]
    for channel in channels[:12]:
        channel_id = str(channel["_id"])
        toggle_label = "Disable" if channel.get("enabled", True) else "Enable"
        rows.append(
            [
                InlineKeyboardButton(
                    text=btn(toggle_label, "✅" if channel.get("enabled", True) else "⭕"),
                    callback_data=f"admin:force:channel_toggle:{channel_id}",
                ),
                InlineKeyboardButton(
                    text=f"🗑️ {bold_unicode(str(channel.get('label') or channel.get('target'))[:18])}",
                    callback_data=f"admin:force:delete_ask:{channel_id}",
                ),
            ]
        )
    rows.append([InlineKeyboardButton(text=btn("Admin Panel", "🔙"), callback_data="admin:home")])
    return keyboard(rows)


def admin_ban_keyboard() -> InlineKeyboardMarkup:
    return keyboard(
        [
            [InlineKeyboardButton(text=btn("Ban User", "🚫"), callback_data="admin:ban:add")],
            [InlineKeyboardButton(text=btn("Unban User", "✅"), callback_data="admin:ban:remove")],
            [InlineKeyboardButton(text=btn("Admin Panel", "🔙"), callback_data="admin:home")],
        ]
    )


def admin_bot_settings_keyboard() -> InlineKeyboardMarkup:
    return keyboard(
        [
            [InlineKeyboardButton(text=btn("Start Caption", "📝"), callback_data="admin:settings:set:start_caption")],
            [InlineKeyboardButton(text=btn("Start Photo", "🖼️"), callback_data="admin:settings:set:start_photo_url")],
            [InlineKeyboardButton(text=btn("Support Username", "🛟"), callback_data="admin:settings:set:support_username")],
            [InlineKeyboardButton(text=btn("Update Channel", "📣"), callback_data="admin:settings:set:update_channel")],
            [InlineKeyboardButton(text=btn("Free Daily Limit", "📉"), callback_data="admin:settings:set:free_daily_limit")],
            [InlineKeyboardButton(text=btn("Premium Daily Limit", "📈"), callback_data="admin:settings:set:premium_daily_limit")],
            [InlineKeyboardButton(text=btn("Cooldown Seconds", "⏱️"), callback_data="admin:settings:set:cooldown_seconds")],
            [InlineKeyboardButton(text=btn("Max Text Length", "✍️"), callback_data="admin:settings:set:max_text_chars")],
            [InlineKeyboardButton(text=btn("Admin Panel", "🔙"), callback_data="admin:home")],
        ]
    )


def _target_url(target: str) -> str:
    if target.startswith("@"):
        return f"https://t.me/{target[1:]}"
    if target.startswith("https://t.me/"):
        return target
    return ""
