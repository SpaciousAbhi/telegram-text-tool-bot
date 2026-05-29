from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.catalog import TOOLS, category_description, category_emoji, category_title
from app.text_style import bold_unicode, escape_html


IST = ZoneInfo("Asia/Kolkata")


def compact_dt(value: Any) -> str:
    if not isinstance(value, datetime):
        return "Not available"
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(IST).strftime("%d %b %Y, %I:%M %p")


def main_caption(custom_caption: str = "", user: dict[str, Any] | None = None) -> str:
    name = _display_name(user)
    if custom_caption.strip():
        body = custom_caption.strip()
    else:
        body = "Style text, clean messy messages, count words, extract links, and format Telegram-ready content."
    greeting = f"{bold_unicode('Welcome')}, {escape_html(name)}." if name else bold_unicode("Welcome.")
    return (
        f"🧰 {bold_unicode('TEXT TOOL BOT')}\n\n"
        f"{greeting}\n"
        f"{escape_html(body)}\n\n"
        f"{bold_unicode('Start with one section below.')}\n"
        "Tools stay inside categories so the menu stays clean."
    )


def category_screen(category: str) -> str:
    tools = [tool for tool in TOOLS.values() if tool.category == category]
    return (
        f"{category_emoji(category)} {category_title(category)}\n\n"
        f"{category_description(category)}\n\n"
        f"{bold_unicode('Available tools')}: {len(tools)}\n"
        f"{bold_unicode('Next step')}: Choose one tool, then send your text."
    )


def tool_prompt(tool_key: str) -> str:
    tool = TOOLS[tool_key]
    return (
        f"{tool.emoji} {tool.display_title}\n\n"
        f"{bold_unicode('Current Category')}: {category_emoji(tool.category)} {category_title(tool.category)}\n"
        f"{bold_unicode('Selected Tool')}: {tool.display_title}\n\n"
        f"{bold_unicode('Send next')}: {tool.instruction}\n"
        f"{bold_unicode('Output')}: You will receive {tool.result_hint}.\n\n"
        "Send your text as the next message. Use /cancel anytime to leave this tool."
    )


def processing_screen(tool_key: str) -> str:
    tool = TOOLS[tool_key]
    return (
        f"⏳ {bold_unicode('PROCESSING')}\n\n"
        f"{bold_unicode('Tool')}: {tool.emoji} {tool.display_title}\n"
        "Preparing a clean copy-friendly result..."
    )


def result_screen(tool_key: str, original: str, result: str) -> str:
    tool = TOOLS[tool_key]
    result = clamp(result, 3200)
    return (
        f"✅ {bold_unicode('RESULT READY')}\n\n"
        f"{bold_unicode('Tool')}: {tool.emoji} {tool.display_title}\n"
        f"{bold_unicode('Input')}: {escape_html(preview(original, 120))}\n\n"
        f"{bold_unicode('Copy-Friendly Result')}\n"
        f"<code>{escape_html(result)}</code>\n\n"
        "Use the buttons below to retry, copy, save, or return."
    )


def choose_tool_first_screen() -> str:
    return (
        f"🧭 {bold_unicode('CHOOSE A TOOL FIRST')}\n\n"
        "Open a category, select the exact feature you need, then send your text."
    )


def empty_input_screen() -> str:
    return (
        f"✍️ {bold_unicode('TEXT REQUIRED')}\n\n"
        "Please send valid text so I can process it."
    )


def too_long_screen(max_text_chars: int) -> str:
    return (
        f"📏 {bold_unicode('TEXT TOO LONG')}\n\n"
        f"Please send {max_text_chars} characters or less, or split the text into smaller parts."
    )


def processing_error_screen() -> str:
    return (
        f"⚠️ {bold_unicode('PROCESSING FAILED')}\n\n"
        "Something went wrong while processing your text. Please try again."
    )


def cancelled_screen() -> str:
    return (
        f"✅ {bold_unicode('ACTION CANCELLED')}\n\n"
        "You are back at the main menu."
    )


def profile_screen(user: dict[str, Any], saved_tasks: int, free_daily_limit: int, premium_daily_limit: int) -> str:
    premium_until = user.get("premium_until")
    is_premium = _is_premium_active(user)
    name = " ".join(part for part in [user.get("first_name"), user.get("last_name")] if part).strip() or "Telegram User"
    username = f"@{user.get('username')}" if user.get("username") else "Not set"
    limit = premium_daily_limit if is_premium else free_daily_limit
    return (
        f"👤 {bold_unicode('MY PROFILE')}\n\n"
        f"{bold_unicode('Name')}: {escape_html(name)}\n"
        f"{bold_unicode('Telegram ID')}: <code>{user.get('user_id')}</code>\n"
        f"{bold_unicode('Username')}: {escape_html(username)}\n"
        f"{bold_unicode('Plan')}: {'💎 Premium' if is_premium else 'Free'}\n"
        f"{bold_unicode('Premium Until')}: {compact_dt(premium_until) if is_premium else 'Not active'}\n"
        f"{bold_unicode('Referrals')}: {int(user.get('valid_referrals', 0))}\n"
        f"{bold_unicode('Daily Usage')}: {int(user.get('daily_usage', 0))}/{limit}\n"
        f"{bold_unicode('Saved Tasks')}: {saved_tasks}\n"
        f"{bold_unicode('Joined')}: {compact_dt(user.get('joined_at'))}"
    )


def premium_screen(user: dict[str, Any], premium_daily_limit: int) -> str:
    is_premium = _is_premium_active(user)
    return (
        f"💎 {bold_unicode('PREMIUM')}\n\n"
        f"{bold_unicode('Status')}: {'Active' if is_premium else 'Not active'}\n"
        f"{bold_unicode('Premium Until')}: {compact_dt(user.get('premium_until')) if is_premium else 'Not active'}\n\n"
        f"{bold_unicode('Benefits')}\n"
        f"• {premium_daily_limit} tool uses per day\n"
        "• Priority processing\n"
        "• More saved task capacity\n"
        "• Advanced formatting features\n"
        "• No cooldown while premium is active\n\n"
        "Payments are handled with Telegram Stars."
    )


def referral_screen(
    user: dict[str, Any],
    bot_username: str | None = None,
    rewards_enabled: bool = False,
    required_joins: int = 0,
    reward_days: int = 0,
) -> str:
    user_id = user.get("user_id")
    if bot_username:
        link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    else:
        link = f"Your referral code: ref_{user_id}"
    return (
        f"🎁 {bold_unicode('REFERRAL')}\n\n"
        f"{bold_unicode('Your Link')}\n<code>{escape_html(link)}</code>\n\n"
        f"{bold_unicode('Total Invited')}: {int(user.get('referral_count', 0))}\n"
        f"{bold_unicode('Valid Referrals')}: {int(user.get('valid_referrals', 0))}\n"
        f"{bold_unicode('Rewards')}: {'Active' if rewards_enabled else 'Not active'}\n"
        f"{bold_unicode('Required Joins')}: {required_joins if rewards_enabled else 'Not active'}\n"
        f"{bold_unicode('Reward Duration')}: {reward_days if rewards_enabled else 'Not active'} day(s)\n\n"
        "Share the link and ask friends to start the bot from it."
    )


def settings_screen(user: dict[str, Any]) -> str:
    settings = user.get("settings", {})
    return (
        f"⚙️ {bold_unicode('SETTINGS')}\n\n"
        f"{bold_unicode('Language')}: {settings.get('language', 'English')}\n"
        f"{bold_unicode('Output Style')}: {settings.get('default_output_style', 'Clean')}\n"
        f"{bold_unicode('Result Saving')}: {_toggle(settings.get('save_results', True))}\n"
        f"{bold_unicode('Notifications')}: {_toggle(settings.get('notifications', True))}\n"
        f"{bold_unicode('Privacy Mode')}: {_toggle(settings.get('privacy_mode', False))}"
    )


def help_screen() -> str:
    return (
        f"❓ {bold_unicode('HELP')}\n\n"
        "1. Choose a category from the main menu.\n"
        "2. Select one text tool.\n"
        "3. Send the text you want processed.\n"
        "4. Copy or save the result from the reply.\n"
        "5. Open My Tasks for recent saved results.\n\n"
        "If anything feels stuck, use Main Menu and select the tool again."
    )


def terms_screen() -> str:
    return (
        f"📄 {bold_unicode('TERMS & INFORMATION')}\n\n"
        "Use the bot for text you have the right to process. Do not send private secrets, passwords, tokens, or illegal content.\n\n"
        "Saved task history can be cleared from Settings. Admins may use logs for reliability, abuse protection, and support."
    )


def support_screen(support_username: str, update_channel: str) -> str:
    support_label = f"@{support_username}" if support_username else "Not configured"
    channel_label = f"@{update_channel}" if update_channel else "Not configured"
    return (
        f"🛟 {bold_unicode('SUPPORT')}\n\n"
        f"{bold_unicode('Support')}: {escape_html(support_label)}\n"
        f"{bold_unicode('Updates')}: {escape_html(channel_label)}\n\n"
        "Send the selected tool name, your input type, and what happened."
    )


def system_status_screen(counts: dict[str, int], uptime: str, maintenance: bool, cooldown_seconds: int = 0) -> str:
    return (
        f"📊 {bold_unicode('SYSTEM STATUS')}\n\n"
        f"{bold_unicode('Status')}: {'Maintenance' if maintenance else 'Online'}\n"
        f"{bold_unicode('Text Tools')}: Working\n"
        f"{bold_unicode('Processing')}: Normal\n"
        f"{bold_unicode('Maintenance')}: {'Active' if maintenance else 'No active maintenance'}\n"
        f"{bold_unicode('Current Mode')}: {'Maintenance' if maintenance else 'Normal'}\n"
        f"{bold_unicode('Uptime')}: {uptime}\n\n"
        f"{bold_unicode('Cooldown')}: {cooldown_seconds}s\n"
        f"{bold_unicode('Users')}: {counts.get('users', 0)}\n"
        f"{bold_unicode('Saved Tasks')}: {counts.get('tasks', 0)}"
    )


def tasks_screen(tasks: list[dict[str, Any]]) -> str:
    if not tasks:
        return f"📂 {bold_unicode('MY TASKS')}\n\nNo saved text tasks yet. Run a tool and tap Save to My Tasks."
    lines = [f"📂 {bold_unicode('MY TASKS')}\n"]
    for idx, task in enumerate(tasks, start=1):
        lines.append(
            f"{idx}. {escape_html(task.get('tool_title', 'Text Task'))} — {task.get('status', 'Completed')}\n"
            f"{bold_unicode('Input')}: {escape_html(preview(task.get('original', ''), 55))}\n"
            f"{bold_unicode('Result')}: {escape_html(preview(task.get('result', ''), 55))}\n"
            f"{bold_unicode('Time')}: {compact_dt(task.get('created_at'))}"
        )
    return "\n\n".join(lines)


def task_detail_screen(task: dict[str, Any]) -> str:
    return (
        f"📄 {bold_unicode('TASK RESULT')}\n\n"
        f"{bold_unicode('Task Type')}: {escape_html(task.get('tool_title', 'Text Task'))}\n"
        f"{bold_unicode('Status')}: {task.get('status', 'Completed')}\n"
        f"{bold_unicode('Date')}: {compact_dt(task.get('created_at'))}\n\n"
        f"{bold_unicode('Original')}\n<code>{escape_html(clamp(task.get('original', ''), 1000))}</code>\n\n"
        f"{bold_unicode('Result')}\n<code>{escape_html(clamp(task.get('result', ''), 1800))}</code>"
    )


def force_subscription_screen(channels: list[dict[str, Any]]) -> str:
    lines = [
        f"🔐 {bold_unicode('JOIN REQUIRED')}",
        "",
        "Join the required channel(s), then press Check Access.",
        "",
    ]
    for channel in channels:
        lines.append(f"• {escape_html(channel.get('label') or channel.get('target'))}")
    return "\n".join(lines)


def unauthorized_screen() -> str:
    return f"🔒 {bold_unicode('UNAUTHORIZED')}\n\nYou are not authorized to access this section."


def admin_home_screen(counts: dict[str, int], maintenance: bool) -> str:
    return (
        f"🛠️ {bold_unicode('ADMIN PANEL')}\n\n"
        f"{bold_unicode('Users')}: {counts.get('users', 0)}\n"
        f"{bold_unicode('Premium Users')}: {counts.get('premium', 0)}\n"
        f"{bold_unicode('Banned Users')}: {counts.get('banned', 0)}\n"
        f"{bold_unicode('Saved Tasks')}: {counts.get('tasks', 0)}\n"
        f"{bold_unicode('Force Channels')}: {counts.get('force_channels', 0)}\n"
        f"{bold_unicode('Maintenance')}: {_toggle(maintenance)}\n\n"
        "Choose one management section."
    )


def admin_stats_screen(counts: dict[str, int]) -> str:
    return (
        f"📈 {bold_unicode('USER STATS')}\n\n"
        f"{bold_unicode('Total Users')}: {counts.get('users', 0)}\n"
        f"{bold_unicode('Premium Users')}: {counts.get('premium', 0)}\n"
        f"{bold_unicode('Banned Users')}: {counts.get('banned', 0)}\n"
        f"{bold_unicode('Saved Tasks')}: {counts.get('tasks', 0)}\n"
        f"{bold_unicode('Active Force Channels')}: {counts.get('force_channels', 0)}"
    )


def admin_broadcast_screen() -> str:
    return (
        f"📣 {bold_unicode('BROADCAST')}\n\n"
        "Start broadcast, then send the text, media, file, or forwarded message to deliver.\n\n"
        "Progress shows total users, sent count, failed count, and completion status."
    )


def admin_force_screen(channels: list[dict[str, Any]], enabled: bool = True) -> str:
    lines = [f"🔐 {bold_unicode('FORCE SUBSCRIPTION')}", ""]
    lines.append(f"{bold_unicode('Status')}: {_toggle(enabled)}")
    lines.append("")
    if not channels:
        lines.append("No force-subscription channels added yet.")
    else:
        for idx, channel in enumerate(channels, start=1):
            lines.append(
                f"{idx}. {escape_html(channel.get('label') or channel.get('target'))} "
                f"— {channel.get('mode', 'join')} — {_toggle(bool(channel.get('enabled', True)))}"
            )
    lines.append("\nAdd channels by username, ID, invite link, or forwarded channel post.")
    return "\n".join(lines)


def admin_referral_screen(config: dict[str, Any]) -> str:
    enabled = bool(config.get("referral_rewards_enabled", False))
    required = int(config.get("referral_required_joins", 3))
    days = int(config.get("referral_reward_days", 7))
    return (
        f"🎁 {bold_unicode('REFERRAL SETTINGS')}\n\n"
        f"{bold_unicode('Rewards')}: {_toggle(enabled)}\n"
        f"{bold_unicode('Required Joins')}: {required}\n"
        f"{bold_unicode('Reward Days')}: {days}\n\n"
        "Referral links are active for all users. Reward settings are saved in MongoDB and survive restart."
    )


def referral_leaderboard_screen(users: list[dict[str, Any]]) -> str:
    lines = [f"🏆 {bold_unicode('REFERRAL LEADERBOARD')}", ""]
    if not users:
        lines.append("No referral activity yet.")
        return "\n".join(lines)
    for idx, user in enumerate(users, start=1):
        name = user.get("username") or user.get("first_name") or str(user.get("user_id"))
        lines.append(f"{idx}. {escape_html(name)} — {int(user.get('valid_referrals', 0))} referral(s)")
    return "\n".join(lines)


def admin_bot_settings_screen(config: dict[str, Any]) -> str:
    return (
        f"⚙️ {bold_unicode('BOT SETTINGS')}\n\n"
        f"{bold_unicode('Start Caption')}: {escape_html(preview(config.get('start_caption') or 'Default', 80))}\n"
        f"{bold_unicode('Start Photo')}: {escape_html(preview(config.get('start_photo_url') or 'Not configured', 80))}\n"
        f"{bold_unicode('Support Username')}: {escape_html(config.get('support_username') or 'Not configured')}\n"
        f"{bold_unicode('Update Channel')}: {escape_html(config.get('update_channel') or 'Not configured')}\n"
        f"{bold_unicode('Free Daily Limit')}: {int(config.get('free_daily_limit', 50))}\n"
        f"{bold_unicode('Premium Daily Limit')}: {int(config.get('premium_daily_limit', 500))}\n"
        f"{bold_unicode('Cooldown Seconds')}: {int(config.get('cooldown_seconds', 2))}\n"
        f"{bold_unicode('Max Text Length')}: {int(config.get('max_text_chars', 3000))}\n\n"
        "These values are runtime settings stored in MongoDB."
    )


def logs_screen(logs: list[dict[str, Any]]) -> str:
    if not logs:
        return f"🧾 {bold_unicode('LOGS & ERROR MONITORING')}\n\nNo logs recorded yet."
    lines = [f"🧾 {bold_unicode('LOGS & ERROR MONITORING')}", ""]
    for log in logs:
        lines.append(f"{compact_dt(log.get('created_at'))} | {log.get('kind')}: {escape_html(log.get('message', ''))}")
    return "\n".join(lines)


def clamp(value: str, limit: int) -> str:
    value = str(value)
    if len(value) <= limit:
        return value
    return f"{value[: limit - 80]}\n\n... Result shortened for Telegram message limit."


def preview(value: str, limit: int = 80) -> str:
    value = " ".join(str(value).split())
    if len(value) <= limit:
        return value
    return value[: limit - 1] + "…"


def _display_name(user: dict[str, Any] | None) -> str:
    if not user:
        return ""
    name = " ".join(part for part in [user.get("first_name"), user.get("last_name")] if part).strip()
    return name or str(user.get("username") or "").lstrip("@")


def _toggle(enabled: bool) -> str:
    return "On ✅" if enabled else "Off ⭕"


def _is_premium_active(user: dict[str, Any]) -> bool:
    premium_until = user.get("premium_until")
    if not user.get("is_premium") or not isinstance(premium_until, datetime):
        return False
    if premium_until.tzinfo is None:
        premium_until = premium_until.replace(tzinfo=UTC)
    return premium_until > datetime.now(UTC)
