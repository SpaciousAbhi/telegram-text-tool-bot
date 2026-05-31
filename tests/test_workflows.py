from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from bson import ObjectId

from app.config import Settings
from app import handlers
from app.text_style import bold_unicode


def make_settings() -> Settings:
    return Settings(
        bot_token="123:test",
        mongo_url="mongodb://localhost",
        mongo_db_name="test",
        admin_ids={999},
        owner_ids={999},
        support_username="support",
        update_channel="updates",
        start_photo_url="",
        free_daily_limit=2,
        premium_daily_limit=20,
        max_text_chars=3000,
    )


class FakeStore:
    def __init__(self, state: dict | None = None, settings: Settings | None = None):
        self.state = state if state is not None else {}
        self.settings = settings or make_settings()
        self.state.setdefault("users", {})
        self.state.setdefault("tasks", {})
        self.state.setdefault("logs", [])
        self.state.setdefault("config", {})
        self.state.setdefault("admin_sessions", {})
        self.state.setdefault("force_channels", {})
        self.state.setdefault("broadcasts", [])

    async def runtime_config(self):
        defaults = {
            "start_caption": "",
            "start_photo_url": self.settings.start_photo_url,
            "support_username": self.settings.support_username,
            "update_channel": self.settings.update_channel,
            "free_daily_limit": self.settings.free_daily_limit,
            "premium_daily_limit": self.settings.premium_daily_limit,
            "max_text_chars": self.settings.max_text_chars,
            "cooldown_seconds": 0,
            "force_subscription_enabled": True,
            "referral_rewards_enabled": False,
            "referral_required_joins": 3,
            "referral_reward_days": 7,
        }
        defaults.update(self.state["config"])
        return defaults

    async def upsert_user(self, tg_user, referral_arg=None):
        user_id = int(tg_user.id)
        inserted = user_id not in self.state["users"]
        user = self.state["users"].setdefault(
            user_id,
            {
                "user_id": user_id,
                "joined_at": datetime.now(UTC),
                "is_banned": False,
                "is_premium": False,
                "premium_until": None,
                "referral_count": 0,
                "valid_referrals": 0,
                "settings": {
                    "language": "English",
                    "save_results": True,
                    "notifications": True,
                    "privacy_mode": False,
                    "default_output_style": "Clean",
                },
                "daily_usage": 0,
                "usage_date": datetime.now(UTC).date().isoformat(),
            },
        )
        user.update(
            {
                "first_name": getattr(tg_user, "first_name", "") or "",
                "last_name": getattr(tg_user, "last_name", "") or "",
                "username": getattr(tg_user, "username", "") or "",
                "last_seen_at": datetime.now(UTC),
            }
        )
        referrer_id = _parse_ref(referral_arg)
        if inserted and referrer_id and referrer_id != user_id and referrer_id in self.state["users"]:
            referrer = self.state["users"][referrer_id]
            referrer["referral_count"] = referrer.get("referral_count", 0) + 1
            referrer["valid_referrals"] = referrer.get("valid_referrals", 0) + 1
            if self.state["config"].get("referral_rewards_enabled"):
                required = int(self.state["config"].get("referral_required_joins", 3))
                days = int(self.state["config"].get("referral_reward_days", 7))
                if required > 0 and referrer["valid_referrals"] % required == 0:
                    await self.activate_premium(referrer_id, days, source="referral")
        return dict(user)

    async def get_user(self, user_id):
        user = self.state["users"].get(int(user_id))
        return dict(user) if user else None

    async def set_pending_tool(self, user_id, tool_key):
        self.state["users"].setdefault(int(user_id), {"user_id": int(user_id)})["pending_tool"] = tool_key

    async def get_pending_tool(self, user_id):
        return self.state["users"].get(int(user_id), {}).get("pending_tool")

    async def set_user_setting(self, user_id, key, value):
        self.state["users"][int(user_id)].setdefault("settings", {})[key] = value

    async def set_user_fields(self, user_id, fields):
        self.state["users"].setdefault(int(user_id), {"user_id": int(user_id)}).update(fields)

    async def set_last_result(self, user_id, data):
        self.state["users"][int(user_id)]["last_result"] = data

    async def get_last_result(self, user_id):
        return self.state["users"].get(int(user_id), {}).get("last_result")

    async def increment_usage(self, user_id):
        user = self.state["users"][int(user_id)]
        key = datetime.now(UTC).date().isoformat()
        if user.get("usage_date") != key:
            user["usage_date"] = key
            user["daily_usage"] = 1
        else:
            user["daily_usage"] = user.get("daily_usage", 0) + 1
        return user["daily_usage"]

    async def add_task(self, user_id, tool_key, tool_title, original, result):
        task_id = str(ObjectId())
        self.state["tasks"][task_id] = {
            "_id": ObjectId(task_id),
            "user_id": int(user_id),
            "tool_key": tool_key,
            "tool_title": tool_title,
            "original": original,
            "result": result,
            "status": "Completed",
            "created_at": datetime.now(UTC),
        }
        return task_id

    async def recent_tasks(self, user_id, limit=8):
        tasks = [task for task in self.state["tasks"].values() if task["user_id"] == int(user_id)]
        return sorted(tasks, key=lambda task: task["created_at"], reverse=True)[:limit]

    async def get_task(self, user_id, task_id):
        task = self.state["tasks"].get(task_id)
        return task if task and task["user_id"] == int(user_id) else None

    async def delete_task(self, user_id, task_id):
        task = self.state["tasks"].get(task_id)
        if task and task["user_id"] == int(user_id):
            del self.state["tasks"][task_id]
            return True
        return False

    async def clear_tasks(self, user_id):
        ids = [task_id for task_id, task in self.state["tasks"].items() if task["user_id"] == int(user_id)]
        for task_id in ids:
            del self.state["tasks"][task_id]
        return len(ids)

    async def count_saved_tasks(self, user_id):
        return len([task for task in self.state["tasks"].values() if task["user_id"] == int(user_id)])

    async def counts(self):
        users = self.state["users"].values()
        return {
            "users": len(self.state["users"]),
            "banned": len([u for u in users if u.get("is_banned")]),
            "premium": len([u for u in users if u.get("is_premium")]),
            "tasks": len(self.state["tasks"]),
            "force_channels": len([c for c in self.state["force_channels"].values() if c.get("enabled")]),
        }

    async def all_user_ids(self):
        return [user_id for user_id, user in self.state["users"].items() if not user.get("is_banned")]

    async def set_admin_action(self, user_id, action, data=None):
        if action is None:
            self.state["admin_sessions"].pop(int(user_id), None)
        else:
            self.state["admin_sessions"][int(user_id)] = {"user_id": int(user_id), "action": action, "data": data or {}}

    async def get_admin_action(self, user_id):
        return self.state["admin_sessions"].get(int(user_id))

    async def add_log(self, kind, message, user_id=None, meta=None):
        self.state["logs"].append({"kind": kind, "message": message, "user_id": user_id, "meta": meta or {}, "created_at": datetime.now(UTC)})

    async def recent_logs(self, limit=10):
        return list(reversed(self.state["logs"]))[:limit]

    async def get_config(self, key, default=None):
        return self.state["config"].get(key, default)

    async def set_config(self, key, value):
        self.state["config"][key] = value

    async def is_maintenance(self):
        return bool(self.state["config"].get("maintenance_mode", False))

    async def toggle_maintenance(self):
        self.state["config"]["maintenance_mode"] = not bool(self.state["config"].get("maintenance_mode", False))
        return self.state["config"]["maintenance_mode"]

    async def toggle_config_bool(self, key, default=False):
        self.state["config"][key] = not bool(self.state["config"].get(key, default))
        return self.state["config"][key]

    async def set_ban(self, user_id, banned):
        self.state["users"].setdefault(int(user_id), {"user_id": int(user_id)})["is_banned"] = banned

    async def activate_premium(self, user_id, days, source="admin"):
        until = datetime.now(UTC) + timedelta(days=days)
        user = self.state["users"].setdefault(int(user_id), {"user_id": int(user_id)})
        user["is_premium"] = True
        user["premium_until"] = until
        return until

    async def remove_premium(self, user_id):
        user = self.state["users"].setdefault(int(user_id), {"user_id": int(user_id)})
        user["is_premium"] = False
        user["premium_until"] = None

    async def add_force_channel(self, target, label, invite_link="", mode="join"):
        channel_id = str(ObjectId())
        self.state["force_channels"][channel_id] = {
            "_id": ObjectId(channel_id),
            "target": target,
            "label": label,
            "invite_link": invite_link,
            "mode": mode,
            "enabled": True,
            "created_at": datetime.now(UTC),
        }
        return channel_id

    async def list_force_channels(self, enabled_only=True):
        channels = list(self.state["force_channels"].values())
        if enabled_only:
            channels = [channel for channel in channels if channel.get("enabled")]
        return channels

    async def set_force_channel_enabled(self, channel_id, enabled):
        if channel_id not in self.state["force_channels"]:
            return False
        self.state["force_channels"][channel_id]["enabled"] = bool(enabled)
        return True

    async def delete_force_channel(self, channel_id):
        return self.state["force_channels"].pop(channel_id, None) is not None

    async def record_force_request(self, user_id, chat_id, username=None, title=None):
        requests = self.state.setdefault("force_requests", set())
        requests.add((int(user_id), str(chat_id)))
        if username:
            requests.add((int(user_id), f"@{username.lstrip('@')}"))

    async def has_force_request(self, user_id, target):
        target = str(target)
        candidates = {target}
        if target.startswith("https://t.me/"):
            suffix = target.removeprefix("https://t.me/").strip("/")
            if suffix:
                candidates.add(f"@{suffix}")
        return any((int(user_id), candidate) in self.state.get("force_requests", set()) for candidate in candidates)


    async def record_broadcast(self, admin_id, total, sent, failed):
        self.state["broadcasts"].append({"admin_id": admin_id, "total": total, "sent": sent, "failed": failed, "status": "Completed"})

    async def referral_leaderboard(self, limit=10):
        users = [user for user in self.state["users"].values() if user.get("valid_referrals", 0) > 0]
        return sorted(users, key=lambda user: user.get("valid_referrals", 0), reverse=True)[:limit]


class FakeBot:
    def __init__(self, member_status="member", is_member=False):
        self.member_status = member_status
        self.is_member = is_member
        self.copied_to = []

    async def get_me(self):
        return SimpleNamespace(username="TextToolBot")

    async def get_chat_member(self, chat_id, user_id):
        return SimpleNamespace(status=SimpleNamespace(value=self.member_status), is_member=self.is_member)

    async def copy_message(self, chat_id, from_chat_id, message_id, reply_markup=None):
        self.copied_to.append(chat_id)


class FakeMessage:
    def __init__(self, user_id=111, text="", username="user", first_name="User"):
        self.from_user = SimpleNamespace(id=user_id, username=username, first_name=first_name, last_name="")
        self.chat = SimpleNamespace(id=user_id)
        self.text = text
        self.caption = None
        self.message_id = 10
        self.reply_markup = None
        self.photo = None
        self.responses = []
        self.invoices = []

    async def answer(self, text, reply_markup=None, disable_web_page_preview=None):
        sent = FakeSentMessage(self, text, reply_markup)
        self.responses.append(("answer", text, reply_markup))
        return sent

    async def answer_photo(self, photo, caption, reply_markup=None):
        self.responses.append(("photo", caption, reply_markup))
        return FakeSentMessage(self, caption, reply_markup)

    async def answer_invoice(self, **kwargs):
        self.invoices.append(kwargs)

    async def edit_text(self, text, reply_markup=None, disable_web_page_preview=None):
        self.responses.append(("edit", text, reply_markup))

    async def edit_caption(self, caption, reply_markup=None):
        self.responses.append(("edit_caption", caption, reply_markup))


class FakeSentMessage:
    def __init__(self, parent, text="", reply_markup=None):
        self.parent = parent
        self.text = text
        self.reply_markup = reply_markup

    async def edit_text(self, text, reply_markup=None, disable_web_page_preview=None):
        self.text = text
        self.reply_markup = reply_markup
        self.parent.responses.append(("edit", text, reply_markup))

    async def answer(self, text, reply_markup=None, disable_web_page_preview=None):
        return await self.parent.answer(text, reply_markup=reply_markup, disable_web_page_preview=disable_web_page_preview)


class FakeCall:
    def __init__(self, user_id=111, data="menu:home", message=None):
        self.from_user = SimpleNamespace(id=user_id, username="user", first_name="User", last_name="")
        self.data = data
        self.message = message or FakeMessage(user_id=user_id)
        self.responses = []

    async def answer(self, text=None, show_alert=False, **kwargs):
        self.responses.append(("answer", text, show_alert, kwargs))
        if text is not None:
            self.message.responses.append(("answer", text, kwargs.get("reply_markup")))
        return FakeSentMessage(self.message, text or "", kwargs.get("reply_markup"))

    async def answer_photo(self, photo, caption, reply_markup=None):
        self.message.responses.append(("photo", caption, reply_markup))


def _parse_ref(value):
    if not value:
        return None
    value = str(value)
    if value.startswith("ref_"):
        value = value[4:]
    try:
        return int(value)
    except ValueError:
        return None


def last_text(message):
    assert message.responses
    return message.responses[-1][1]


@pytest.mark.asyncio
async def test_user_tool_flow_saves_task_and_survives_restart():
    settings = make_settings()
    state = {}
    store = FakeStore(state, settings)
    bot = FakeBot()

    start = FakeMessage(user_id=111)
    await handlers.cmd_start(start, SimpleNamespace(args=None), bot, store, settings)
    assert bold_unicode("TEXT TOOL BOT") in last_text(start)
    assert "ADMIN" not in " ".join(button.text for row in start.responses[-1][2].inline_keyboard for button in row)

    await handlers.cb_tool(FakeCall(user_id=111, data="tool:stylish_text"), bot, store, settings)
    assert state["users"][111]["pending_tool"] == "stylish_text"

    restarted_store = FakeStore(state, settings)
    text = FakeMessage(user_id=111, text="Your Text")
    await handlers.incoming_message(text, bot, restarted_store, settings)

    assert state["users"][111]["daily_usage"] == 1
    assert len(state["tasks"]) == 1
    assert state["users"][111]["pending_tool"] is None
    assert bold_unicode("RESULT READY") in last_text(text)
    assert bold_unicode("Saved") in last_text(text)
    assert "My Tasks" in last_text(text)
    assert "𝐘𝐨𝐮𝐫" in last_text(text)

    after_restart = FakeStore(state, settings)
    tasks = await after_restart.recent_tasks(111)
    assert tasks[0]["tool_title"] == "Stylish Text Generator"

    task_id = str(tasks[0]["_id"])
    delete_prompt = FakeCall(user_id=111, data=f"task:delete_ask:{task_id}")
    await handlers.cb_task_delete_ask(delete_prompt, bot, after_restart, settings)
    assert bold_unicode("CONFIRM DELETE TASK") in last_text(delete_prompt.message)
    await handlers.cb_task_delete(FakeCall(user_id=111, data=f"task:delete_confirm:{task_id}"), bot, after_restart, settings)
    assert await after_restart.recent_tasks(111) == []


@pytest.mark.asyncio
async def test_settings_flow_saves_preferences_and_manual_task_save():
    settings = make_settings()
    store = FakeStore(settings=settings)
    bot = FakeBot()
    await store.upsert_user(SimpleNamespace(id=111, username="user", first_name="User", last_name=""))

    await handlers.cb_settings_action(FakeCall(user_id=111, data="settings:lang:Hindi"), bot, store, settings)
    await handlers.cb_settings_action(FakeCall(user_id=111, data="settings:style:set:Detailed"), bot, store, settings)
    await handlers.cb_settings_action(FakeCall(user_id=111, data="settings:toggle_save"), bot, store, settings)

    user = await store.get_user(111)
    assert user["settings"]["language"] == "Hindi"
    assert user["settings"]["default_output_style"] == "Detailed"
    assert user["settings"]["save_results"] is False

    await store.set_pending_tool(111, "text_cleaner")
    msg = FakeMessage(user_id=111, text="  hello     world  ")
    await handlers.incoming_message(msg, bot, store, settings)
    assert len(store.state["tasks"]) == 0

    call = FakeCall(user_id=111, data="task:save_latest")
    await handlers.cb_save_latest(call, store)
    assert len(store.state["tasks"]) == 1

    await handlers.cb_settings_action(FakeCall(user_id=111, data="settings:toggle_privacy"), bot, store, settings)
    assert (await store.get_user(111))["settings"]["privacy_mode"] is True
    await store.set_pending_tool(111, "word_counter")
    private_msg = FakeMessage(user_id=111, text="private text")
    await handlers.incoming_message(private_msg, bot, store, settings)
    assert len(store.state["tasks"]) == 1
    assert store.state["users"][111]["last_result"] is None

    terms = FakeCall(user_id=111, data="settings:terms")
    await handlers.cb_settings_action(terms, bot, store, settings)
    assert bold_unicode("TERMS & INFORMATION") in last_text(terms.message)

    await handlers.cb_settings_action(FakeCall(user_id=111, data="settings:clear_data"), bot, store, settings)
    assert len(store.state["tasks"]) == 0
    assert store.state["users"][111]["last_result"] is None

    await handlers.cb_settings_action(FakeCall(user_id=111, data="settings:reset_defaults"), bot, store, settings)
    reset_user = await store.get_user(111)
    assert reset_user["settings"]["save_results"] is True
    assert reset_user["settings"]["privacy_mode"] is False


@pytest.mark.asyncio
async def test_navigation_and_cancel_clear_pending_tool_state():
    settings = make_settings()
    store = FakeStore(settings=settings)
    bot = FakeBot()
    await store.upsert_user(SimpleNamespace(id=111, username="user", first_name="User", last_name=""))

    await handlers.cb_tool(FakeCall(user_id=111, data="tool:stylish_text"), bot, store, settings)
    assert store.state["users"][111]["pending_tool"] == "stylish_text"

    await handlers.cb_home(FakeCall(user_id=111, data="menu:home"), bot, store, settings)
    assert store.state["users"][111]["pending_tool"] is None

    await handlers.cb_tool(FakeCall(user_id=111, data="tool:word_counter"), bot, store, settings)
    await handlers.cb_category(FakeCall(user_id=111, data="cat:utility"), bot, store, settings)
    assert store.state["users"][111]["pending_tool"] is None

    await handlers.cb_tool(FakeCall(user_id=111, data="tool:text_cleaner"), bot, store, settings)
    cancel = FakeCall(user_id=111, data="tool:cancel")
    await handlers.cb_tool(cancel, bot, store, settings)

    assert store.state["users"][111]["pending_tool"] is None
    assert bold_unicode("TOOL CANCELLED") in last_text(cancel.message)


@pytest.mark.asyncio
async def test_admin_management_flows_save_to_database_and_gate_users():
    settings = make_settings()
    store = FakeStore(settings=settings)
    bot = FakeBot(member_status="left")
    await store.upsert_user(SimpleNamespace(id=999, username="admin", first_name="Admin", last_name=""))
    await store.upsert_user(SimpleNamespace(id=111, username="user", first_name="User", last_name=""))

    await handlers.cb_admin(FakeCall(user_id=999, data="admin:premium:add"), bot, store, settings)
    store = FakeStore(store.state, settings)
    await handlers.incoming_message(FakeMessage(user_id=999, text="111 30"), bot, store, settings)
    assert store.state["users"][111]["is_premium"] is True

    await handlers.cb_admin(FakeCall(user_id=999, data="admin:force:add"), bot, store, settings)
    await handlers.incoming_message(FakeMessage(user_id=999, text="@updates request"), bot, store, settings)
    assert len(store.state["force_channels"]) == 1
    channel_id = next(iter(store.state["force_channels"]))

    gated = FakeMessage(user_id=111)
    await handlers.cmd_start(gated, SimpleNamespace(args=None), bot, store, settings)
    assert bold_unicode("JOIN REQUIRED") in last_text(gated)

    await handlers.cb_admin(FakeCall(user_id=999, data=f"admin:force:channel_toggle:{channel_id}"), bot, store, settings)
    disabled = FakeMessage(user_id=111)
    await handlers.cmd_start(disabled, SimpleNamespace(args=None), bot, store, settings)
    assert bold_unicode("TEXT TOOL BOT") in last_text(disabled)
    await handlers.cb_admin(FakeCall(user_id=999, data=f"admin:force:channel_toggle:{channel_id}"), bot, store, settings)
    await store.record_force_request(111, -100123, username="updates")
    requested = FakeMessage(user_id=111)
    await handlers.cmd_start(requested, SimpleNamespace(args=None), bot, store, settings)
    assert bold_unicode("TEXT TOOL BOT") in last_text(requested)

    await handlers.cb_admin(FakeCall(user_id=999, data="admin:force:toggle"), bot, store, settings)
    ungated = FakeMessage(user_id=111)
    await handlers.cmd_start(ungated, SimpleNamespace(args=None), bot, store, settings)
    assert bold_unicode("TEXT TOOL BOT") in last_text(ungated)

    await handlers.cb_admin(FakeCall(user_id=999, data="admin:referrals:toggle"), bot, store, settings)
    await handlers.cb_admin(FakeCall(user_id=999, data="admin:referrals:required"), bot, store, settings)
    await handlers.incoming_message(FakeMessage(user_id=999, text="1"), bot, store, settings)
    await handlers.cb_admin(FakeCall(user_id=999, data="admin:referrals:days"), bot, store, settings)
    await handlers.incoming_message(FakeMessage(user_id=999, text="5"), bot, store, settings)

    await store.upsert_user(SimpleNamespace(id=222, username="new", first_name="New", last_name=""), referral_arg="ref_111")
    assert store.state["users"][111]["valid_referrals"] == 1
    assert store.state["users"][111]["is_premium"] is True

    await handlers.cb_admin(FakeCall(user_id=999, data="admin:settings:set:support_username"), bot, store, settings)
    await handlers.incoming_message(FakeMessage(user_id=999, text="@new_support"), bot, store, settings)
    assert store.state["config"]["support_username"] == "new_support"

    await handlers.cb_admin(FakeCall(user_id=999, data="admin:maintenance"), bot, store, settings)
    blocked = FakeMessage(user_id=111)
    await handlers.cmd_start(blocked, SimpleNamespace(args=None), bot, store, settings)
    assert bold_unicode("MAINTENANCE MODE") in last_text(blocked)

    delete_force = FakeCall(user_id=999, data=f"admin:force:delete_ask:{channel_id}")
    await handlers.cb_admin(delete_force, bot, store, settings)
    assert bold_unicode("CONFIRM DELETE CHANNEL") in last_text(delete_force.message)
    await handlers.cb_admin(FakeCall(user_id=999, data=f"admin:force:delete_confirm:{channel_id}"), bot, store, settings)
    assert channel_id not in store.state["force_channels"]


@pytest.mark.asyncio
async def test_broadcast_records_progress_and_excludes_banned_users(monkeypatch):
    settings = make_settings()
    store = FakeStore(settings=settings)
    bot = FakeBot()
    for user_id in [999, 111, 222]:
        await store.upsert_user(SimpleNamespace(id=user_id, username=str(user_id), first_name="User", last_name=""))
    await store.set_ban(222, True)

    async def no_sleep(_seconds):
        return None

    monkeypatch.setattr(handlers.asyncio, "sleep", no_sleep)
    await handlers.cb_admin(FakeCall(user_id=999, data="admin:broadcast:start"), bot, store, settings)
    await handlers.incoming_message(FakeMessage(user_id=999, text="Broadcast message"), bot, store, settings)

    assert set(bot.copied_to) == {999, 111}
    assert store.state["broadcasts"][-1]["sent"] == 2
    assert store.state["broadcasts"][-1]["failed"] == 0


@pytest.mark.asyncio
async def test_limits_cooldown_and_expired_premium_are_enforced():
    settings = make_settings()
    store = FakeStore(settings=settings)
    bot = FakeBot()
    await store.upsert_user(SimpleNamespace(id=111, username="user", first_name="User", last_name=""))
    await store.set_config("cooldown_seconds", 10)
    await store.set_pending_tool(111, "word_counter")

    first = FakeMessage(user_id=111, text="one two")
    await handlers.incoming_message(first, bot, store, settings)
    assert bold_unicode("RESULT READY") in last_text(first)

    await store.set_pending_tool(111, "word_counter")
    second = FakeMessage(user_id=111, text="three four")
    await handlers.incoming_message(second, bot, store, settings)
    assert bold_unicode("COOLDOWN ACTIVE") in last_text(second)

    user = store.state["users"][111]
    user["is_premium"] = True
    user["premium_until"] = datetime.now(UTC) - timedelta(days=1)
    user["daily_usage"] = settings.free_daily_limit
    user["last_tool_at"] = datetime.now(UTC) - timedelta(seconds=30)
    await store.set_pending_tool(111, "word_counter")
    third = FakeMessage(user_id=111, text="five six")
    await handlers.incoming_message(third, bot, store, settings)
    assert bold_unicode("DAILY LIMIT REACHED") in last_text(third)
    assert store.state["users"][111]["is_premium"] is False


def test_premium_payload_validation_is_strict():
    assert handlers._parse_premium_payload("premium:30:111") == (30, 111)
    assert handlers._parse_premium_payload("premium:365:111") == (365, 111)
    assert handlers._parse_premium_payload("premium:7:111") is None
    assert handlers._parse_premium_payload("bad:30:111") is None
    assert handlers._parse_premium_payload("premium:30:abc") is None


@pytest.mark.asyncio
async def test_force_subscription_treats_restricted_member_as_joined():
    settings = make_settings()
    store = FakeStore(settings=settings)
    await store.upsert_user(SimpleNamespace(id=111, username="user", first_name="User", last_name=""))
    await store.add_force_channel("@updates", "@updates", mode="join")

    missing = await handlers._missing_force_channels(FakeBot(member_status="restricted", is_member=True), store, 111)

    assert missing == []
