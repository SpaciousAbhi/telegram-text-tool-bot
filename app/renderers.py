from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.catalog import TOOLS, category_description, category_title
from app.text_style import bold_unicode, escape_html


IST = ZoneInfo("Asia/Kolkata")


def compact_dt(value: Any) -> str:
    if not isinstance(value, datetime):
        return "Not available"
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(IST).strftime("%d %b %Y, %I:%M %p")


def main_caption(custom_caption: str = "") -> str:
    if custom_caption.strip():
        body = custom_caption.strip()
    else:
        body = "Create stylish text, clean messy messages, count words, extract links, and format Telegram-ready content."
    return (
        f"{bold_unicode('TEXT TOOL BOT')}\n\n"
        f"{escape_html(body)}\n\n"
        f"{bold_unicode('Choose a category to continue.')}"
    )


def category_screen(category: str) -> str:
    return f"{category_title(category)}\n\n{category_description(category)}\n\n{bold_unicode('Select a tool to continue.')}"


def tool_prompt(tool_key: str) -> str:
    tool = TOOLS[tool_key]
    return (
        f"{bold_unicode('CURRENT CATEGORY')}: {category_title(tool.category)}\n"
        f"{bold_unicode('SELECTED TOOL')}: {tool.display_title}\n\n"
        f"{bold_unicode('What to send next')}: {tool.instruction}\n"
        f"{bold_unicode('Result')}: You will receive {tool.result_hint}."
    )


def result_screen(tool_key: str, original: str, result: str) -> str:
    tool = TOOLS[tool_key]
    result = clamp(result, 3200)
    return (
        f"{bold_unicode('RESULT READY')}\n\n"
        f"{bold_unicode('Tool')}: {tool.display_title}\n"
        f"{bold_unicode('Input Preview')}: {escape_html(preview(original, 120))}\n\n"
        f"{bold_unicode('Result')}\n"
        f"<code>{escape_html(result)}</code>\n\n"
        "The result is formatted for easy manual copy."
    )


def profile_screen(user: dict[str, Any], saved_tasks: int, free_daily_limit: int, premium_daily_limit: int) -> str:
    premium_until = user.get("premium_until")
    is_premium = _is_premium_active(user)
    name = " ".join(part for part in [user.get("first_name"), user.get("last_name")] if part).strip() or "Telegram User"
    username = f"@{user.get('username')}" if user.get("username") else "Not set"
    limit = premium_daily_limit if is_premium else free_daily_limit
    return (
        f"{bold_unicode('MY PROFILE')}\n\n"
        f"Name: {escape_html(name)}\n"
        f"Telegram ID: <code>{user.get('user_id')}</code>\n"
        f"Username: {escape_html(username)}\n"
        f"Account Status: {'Premium' if is_premium else 'Free'}\n"
        f"Premium Until: {compact_dt(premium_until) if is_premium else 'Not active'}\n"
        f"Referrals: {int(user.get('valid_referrals', 0))}\n"
        f"Daily Usage: {int(user.get('daily_usage', 0))}/{limit}\n"
        f"Saved Tasks: {saved_tasks}\n"
        f"Join Date: {compact_dt(user.get('joined_at'))}"
    )


def premium_screen(user: dict[str, Any], premium_daily_limit: int) -> str:
    is_premium = _is_premium_active(user)
    return (
        f"{bold_unicode('PREMIUM')}\n\n"
        f"Status: {'Active' if is_premium else 'Not active'}\n"
        f"Premium Until: {compact_dt(user.get('premium_until')) if is_premium else 'Not active'}\n\n"
        f"{bold_unicode('Benefits')}\n"
        f"• More daily tool usage: {premium_daily_limit}/day\n"
        "• Priority processing\n"
        "• More saved task capacity\n"
        "• Advanced formatting features\n"
        "• No cooldown while premium is active\n\n"
        "Premium uses Telegram Stars only."
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
        f"{bold_unicode('REFERRAL')}\n\n"
        f"Referral Link:\n<code>{escape_html(link)}</code>\n\n"
        f"Total Invited Users: {int(user.get('referral_count', 0))}\n"
        f"Valid Referrals: {int(user.get('valid_referrals', 0))}\n"
        f"Reward Status: {'Active' if rewards_enabled else 'Not active'}\n"
        f"Required Joins: {required_joins if rewards_enabled else 'Not active'}\n"
        f"Reward Duration: {reward_days if rewards_enabled else 'Not active'} day(s)\n\n"
        "Share your link with friends and ask them to start the bot from it."
    )


def settings_screen(user: dict[str, Any]) -> str:
    settings = user.get("settings", {})
    return (
        f"{bold_unicode('SETTINGS')}\n\n"
        f"Language: {settings.get('language', 'English')}\n"
        f"Default Output Style: {settings.get('default_output_style', 'Clean')}\n"
        f"Result Saving: {'On' if settings.get('save_results', True) else 'Off'}\n"
        f"Notifications: {'On' if settings.get('notifications', True) else 'Off'}\n"
        f"Privacy Mode: {'On' if settings.get('privacy_mode', False) else 'Off'}"
    )


def help_screen() -> str:
    return (
        f"{bold_unicode('HELP')}\n\n"
        "1. Choose a main category.\n"
        "2. Select the text tool you need.\n"
        "3. Send your text.\n"
        "4. Copy the clean result from the reply.\n"
        "5. Open My Tasks to view recent results.\n\n"
        "If a tool does not respond, return to Main Menu and select the tool again."
    )


def terms_screen() -> str:
    return (
        f"{bold_unicode('TERMS & INFORMATION')}\n\n"
        "Use the bot for text you have the right to process. Do not send private secrets, passwords, tokens, or illegal content.\n\n"
        "Saved task history can be cleared from Settings. Admins may use logs for reliability, abuse protection, and support."
    )


def support_screen(support_username: str, update_channel: str) -> str:
    support_label = f"@{support_username}" if support_username else "Not configured"
    channel_label = f"@{update_channel}" if update_channel else "Not configured"
    return (
        f"{bold_unicode('SUPPORT')}\n\n"
        f"Support: {escape_html(support_label)}\n"
        f"Updates: {escape_html(channel_label)}\n\n"
        "For issues, send a short message with what you selected and what happened."
    )


def system_status_screen(counts: dict[str, int], uptime: str, maintenance: bool, cooldown_seconds: int = 0) -> str:
    return (
        f"{bold_unicode('SYSTEM STATUS')}\n\n"
        f"Status: {'Maintenance' if maintenance else 'Online'}\n"
        "Text Tools: Working\n"
        "Processing: Normal\n"
        f"Maintenance: {'Active' if maintenance else 'No active maintenance'}\n"
        f"Current Mode: {'Maintenance' if maintenance else 'Normal'}\n"
        f"Bot Uptime: {uptime}\n\n"
        f"Cooldown: {cooldown_seconds}s\n"
        f"Users: {counts.get('users', 0)}\n"
        f"Saved Tasks: {counts.get('tasks', 0)}"
    )


def tasks_screen(tasks: list[dict[str, Any]]) -> str:
    if not tasks:
        return f"{bold_unicode('MY TASKS')}\n\nNo saved text tasks yet."
    lines = [f"{bold_unicode('MY TASKS')}\n"]
    for idx, task in enumerate(tasks, start=1):
        lines.append(
            f"{idx}. {escape_html(task.get('tool_title', 'Text Task'))} — {task.get('status', 'Completed')}\n"
            f"Input: {escape_html(preview(task.get('original', ''), 55))}\n"
            f"Result: {escape_html(preview(task.get('result', ''), 55))}\n"
            f"Time: {compact_dt(task.get('created_at'))}"
        )
    return "\n\n".join(lines)


def task_detail_screen(task: dict[str, Any]) -> str:
    return (
        f"{bold_unicode('TASK RESULT')}\n\n"
        f"Task Type: {escape_html(task.get('tool_title', 'Text Task'))}\n"
        f"Status: {task.get('status', 'Completed')}\n"
        f"Date: {compact_dt(task.get('created_at'))}\n\n"
        f"{bold_unicode('Original')}\n<code>{escape_html(clamp(task.get('original', ''), 1000))}</code>\n\n"
        f"{bold_unicode('Result')}\n<code>{escape_html(clamp(task.get('result', ''), 1800))}</code>"
    )


def force_subscription_screen(channels: list[dict[str, Any]]) -> str:
    lines = [
        bold_unicode("JOIN REQUIRED"),
        "",
        "Please join the required channel(s), then press CHECK ACCESS.",
        "",
    ]
    for channel in channels:
        lines.append(f"• {escape_html(channel.get('label') or channel.get('target'))}")
    return "\n".join(lines)


def unauthorized_screen() -> str:
    return f"{bold_unicode('UNAUTHORIZED')}\n\nYou are not authorized to access this section."


def admin_home_screen(counts: dict[str, int], maintenance: bool) -> str:
    return (
        f"{bold_unicode('ADMIN PANEL')}\n\n"
        f"Users: {counts.get('users', 0)}\n"
        f"Premium Users: {counts.get('premium', 0)}\n"
        f"Banned Users: {counts.get('banned', 0)}\n"
        f"Saved Tasks: {counts.get('tasks', 0)}\n"
        f"Force Channels: {counts.get('force_channels', 0)}\n"
        f"Maintenance: {'On' if maintenance else 'Off'}\n\n"
        "Choose an admin section."
    )


def admin_stats_screen(counts: dict[str, int]) -> str:
    return (
        f"{bold_unicode('USER STATS')}\n\n"
        f"Total Users: {counts.get('users', 0)}\n"
        f"Premium Users: {counts.get('premium', 0)}\n"
        f"Banned Users: {counts.get('banned', 0)}\n"
        f"Saved Tasks: {counts.get('tasks', 0)}\n"
        f"Active Force Channels: {counts.get('force_channels', 0)}"
    )


def admin_broadcast_screen() -> str:
    return (
        f"{bold_unicode('BROADCAST')}\n\n"
        "Press START BROADCAST, then send the message, photo, video, file, or forwarded message you want delivered to users.\n\n"
        "Progress will show total users, sent count, failed count, and completion status."
    )


def admin_force_screen(channels: list[dict[str, Any]], enabled: bool = True) -> str:
    lines = [bold_unicode("FORCE SUBSCRIPTION"), ""]
    lines.append(f"Status: {'On' if enabled else 'Off'}")
    lines.append("")
    if not channels:
        lines.append("No force-subscription channels added yet.")
    else:
        for idx, channel in enumerate(channels, start=1):
            lines.append(
                f"{idx}. {escape_html(channel.get('label') or channel.get('target'))} "
                f"— {channel.get('mode', 'join')} — {'On' if channel.get('enabled') else 'Off'}"
            )
    lines.append("\nSend channel username, ID, invite link, or a forwarded channel message when adding.")
    return "\n".join(lines)


def admin_referral_screen(config: dict[str, Any]) -> str:
    enabled = bool(config.get("referral_rewards_enabled", False))
    required = int(config.get("referral_required_joins", 3))
    days = int(config.get("referral_reward_days", 7))
    return (
        f"{bold_unicode('REFERRAL SETTINGS')}\n\n"
        f"Rewards: {'On' if enabled else 'Off'}\n"
        f"Required Joins: {required}\n"
        f"Reward Days: {days}\n\n"
        "Referral links are active for all users. Reward settings are saved in MongoDB and survive restart."
    )


def referral_leaderboard_screen(users: list[dict[str, Any]]) -> str:
    lines = [bold_unicode("REFERRAL LEADERBOARD"), ""]
    if not users:
        lines.append("No referral activity yet.")
        return "\n".join(lines)
    for idx, user in enumerate(users, start=1):
        name = user.get("username") or user.get("first_name") or str(user.get("user_id"))
        lines.append(f"{idx}. {escape_html(name)} — {int(user.get('valid_referrals', 0))} referral(s)")
    return "\n".join(lines)


def admin_bot_settings_screen(config: dict[str, Any]) -> str:
    return (
        f"{bold_unicode('BOT SETTINGS')}\n\n"
        f"Start Caption: {escape_html(preview(config.get('start_caption') or 'Default', 80))}\n"
        f"Start Photo: {escape_html(preview(config.get('start_photo_url') or 'Not configured', 80))}\n"
        f"Support Username: {escape_html(config.get('support_username') or 'Not configured')}\n"
        f"Update Channel: {escape_html(config.get('update_channel') or 'Not configured')}\n"
        f"Free Daily Limit: {int(config.get('free_daily_limit', 50))}\n"
        f"Premium Daily Limit: {int(config.get('premium_daily_limit', 500))}\n"
        f"Cooldown Seconds: {int(config.get('cooldown_seconds', 2))}\n"
        f"Max Text Length: {int(config.get('max_text_chars', 3000))}\n\n"
        "These values are runtime settings stored in MongoDB."
    )


def logs_screen(logs: list[dict[str, Any]]) -> str:
    if not logs:
        return f"{bold_unicode('LOGS & ERROR MONITORING')}\n\nNo logs recorded yet."
    lines = [bold_unicode("LOGS & ERROR MONITORING"), ""]
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


def _is_premium_active(user: dict[str, Any]) -> bool:
    premium_until = user.get("premium_until")
    if not user.get("is_premium") or not isinstance(premium_until, datetime):
        return False
    if premium_until.tzinfo is None:
        premium_until = premium_until.replace(tzinfo=UTC)
    return premium_until > datetime.now(UTC)
