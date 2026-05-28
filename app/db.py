from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, ReturnDocument

from app.config import Settings


def utcnow() -> datetime:
    return datetime.now(UTC)


def today_key() -> str:
    return utcnow().date().isoformat()


class MongoStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = AsyncIOMotorClient(
            settings.mongo_url,
            serverSelectionTimeoutMS=8000,
            connectTimeoutMS=8000,
            retryWrites=True,
        )
        self.db: AsyncIOMotorDatabase = self.client[settings.mongo_db_name]

    async def init(self) -> None:
        await self.client.admin.command("ping")
        await self.db.users.create_index([("user_id", ASCENDING)], unique=True)
        await self.db.users.create_index([("is_banned", ASCENDING)])
        await self.db.users.create_index([("valid_referrals", DESCENDING)])
        await self.db.tasks.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
        await self.db.force_channels.create_index([("enabled", ASCENDING)])
        await self.db.logs.create_index([("created_at", DESCENDING)])
        await self.db.admin_sessions.create_index([("user_id", ASCENDING)], unique=True)

    async def close(self) -> None:
        self.client.close()

    async def upsert_user(self, tg_user: Any, referral_arg: str | None = None) -> dict[str, Any]:
        user_id = int(tg_user.id)
        now = utcnow()
        referrer_id = _parse_referral(referral_arg)
        set_on_insert: dict[str, Any] = {
            "user_id": user_id,
            "joined_at": now,
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
            "usage_date": today_key(),
        }
        if referrer_id and referrer_id != user_id:
            set_on_insert["referred_by"] = referrer_id
        result = await self.db.users.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "first_name": getattr(tg_user, "first_name", "") or "",
                    "last_name": getattr(tg_user, "last_name", "") or "",
                    "username": getattr(tg_user, "username", "") or "",
                    "last_seen_at": now,
                },
                "$setOnInsert": set_on_insert,
            },
            upsert=True,
        )
        if result.upserted_id and referrer_id and referrer_id != user_id:
            await self.db.users.update_one(
                {"user_id": referrer_id},
                {"$inc": {"referral_count": 1, "valid_referrals": 1}},
                upsert=False,
            )
            await self._maybe_apply_referral_reward(referrer_id)
            await self.add_log("referral", f"{referrer_id} invited {user_id}", user_id=user_id)
        user = await self.get_user(user_id)
        return user or {}

    async def get_user(self, user_id: int) -> dict[str, Any] | None:
        return await self.db.users.find_one({"user_id": int(user_id)})

    async def set_pending_tool(self, user_id: int, tool_key: str | None) -> None:
        await self.db.users.update_one({"user_id": int(user_id)}, {"$set": {"pending_tool": tool_key}}, upsert=True)

    async def get_pending_tool(self, user_id: int) -> str | None:
        user = await self.get_user(user_id)
        return user.get("pending_tool") if user else None

    async def set_user_setting(self, user_id: int, key: str, value: Any) -> None:
        await self.db.users.update_one({"user_id": int(user_id)}, {"$set": {f"settings.{key}": value}}, upsert=True)

    async def set_user_fields(self, user_id: int, fields: dict[str, Any]) -> None:
        await self.db.users.update_one({"user_id": int(user_id)}, {"$set": fields}, upsert=True)

    async def set_last_result(self, user_id: int, data: dict[str, Any] | None) -> None:
        await self.db.users.update_one({"user_id": int(user_id)}, {"$set": {"last_result": data}}, upsert=True)

    async def get_last_result(self, user_id: int) -> dict[str, Any] | None:
        user = await self.get_user(user_id)
        return user.get("last_result") if user else None

    async def increment_usage(self, user_id: int) -> int:
        user = await self.get_user(user_id)
        key = today_key()
        if not user or user.get("usage_date") != key:
            await self.db.users.update_one({"user_id": int(user_id)}, {"$set": {"usage_date": key, "daily_usage": 1}})
            return 1
        result = await self.db.users.find_one_and_update(
            {"user_id": int(user_id)},
            {"$inc": {"daily_usage": 1}},
            return_document=ReturnDocument.AFTER,
        )
        return int(result.get("daily_usage", 1)) if result else 1

    async def add_task(self, user_id: int, tool_key: str, tool_title: str, original: str, result: str) -> str:
        doc = {
            "user_id": int(user_id),
            "tool_key": tool_key,
            "tool_title": tool_title,
            "original": original[:4000],
            "result": result[:4000],
            "status": "Completed",
            "created_at": utcnow(),
        }
        inserted = await self.db.tasks.insert_one(doc)
        return str(inserted.inserted_id)

    async def recent_tasks(self, user_id: int, limit: int = 8) -> list[dict[str, Any]]:
        cursor = self.db.tasks.find({"user_id": int(user_id)}).sort("created_at", DESCENDING).limit(limit)
        return await cursor.to_list(length=limit)

    async def get_task(self, user_id: int, task_id: str) -> dict[str, Any] | None:
        if not ObjectId.is_valid(task_id):
            return None
        return await self.db.tasks.find_one({"_id": ObjectId(task_id), "user_id": int(user_id)})

    async def delete_task(self, user_id: int, task_id: str) -> bool:
        if not ObjectId.is_valid(task_id):
            return False
        result = await self.db.tasks.delete_one({"_id": ObjectId(task_id), "user_id": int(user_id)})
        return result.deleted_count > 0

    async def clear_tasks(self, user_id: int) -> int:
        result = await self.db.tasks.delete_many({"user_id": int(user_id)})
        return result.deleted_count

    async def count_saved_tasks(self, user_id: int) -> int:
        return await self.db.tasks.count_documents({"user_id": int(user_id)})

    async def counts(self) -> dict[str, int]:
        await self.expire_due_premium()
        total = await self.db.users.count_documents({})
        banned = await self.db.users.count_documents({"is_banned": True})
        premium = await self.db.users.count_documents({"is_premium": True})
        tasks = await self.db.tasks.count_documents({})
        force_channels = await self.db.force_channels.count_documents({"enabled": True})
        return {"users": total, "banned": banned, "premium": premium, "tasks": tasks, "force_channels": force_channels}

    async def all_user_ids(self) -> list[int]:
        cursor = self.db.users.find({"is_banned": {"$ne": True}}, {"user_id": 1})
        return [int(doc["user_id"]) for doc in await cursor.to_list(length=None)]

    async def set_admin_action(self, user_id: int, action: str | None, data: dict[str, Any] | None = None) -> None:
        if action is None:
            await self.db.admin_sessions.delete_one({"user_id": int(user_id)})
            return
        await self.db.admin_sessions.update_one(
            {"user_id": int(user_id)},
            {"$set": {"user_id": int(user_id), "action": action, "data": data or {}, "updated_at": utcnow()}},
            upsert=True,
        )

    async def get_admin_action(self, user_id: int) -> dict[str, Any] | None:
        return await self.db.admin_sessions.find_one({"user_id": int(user_id)})

    async def add_log(self, kind: str, message: str, user_id: int | None = None, meta: dict[str, Any] | None = None) -> None:
        await self.db.logs.insert_one(
            {"kind": kind, "message": message[:1000], "user_id": user_id, "meta": meta or {}, "created_at": utcnow()}
        )

    async def recent_logs(self, limit: int = 10) -> list[dict[str, Any]]:
        cursor = self.db.logs.find({}).sort("created_at", DESCENDING).limit(limit)
        return await cursor.to_list(length=limit)

    async def get_config(self, key: str, default: Any = None) -> Any:
        doc = await self.db.config.find_one({"key": key})
        return doc.get("value") if doc else default

    async def set_config(self, key: str, value: Any) -> None:
        await self.db.config.update_one({"key": key}, {"$set": {"key": key, "value": value, "updated_at": utcnow()}}, upsert=True)

    async def runtime_config(self) -> dict[str, Any]:
        defaults = {
            "start_caption": "",
            "start_photo_url": self.settings.start_photo_url,
            "support_username": self.settings.support_username,
            "update_channel": self.settings.update_channel,
            "free_daily_limit": self.settings.free_daily_limit,
            "premium_daily_limit": self.settings.premium_daily_limit,
            "max_text_chars": self.settings.max_text_chars,
            "cooldown_seconds": 2,
            "force_subscription_enabled": True,
            "referral_rewards_enabled": False,
            "referral_required_joins": 3,
            "referral_reward_days": 7,
        }
        cursor = self.db.config.find({})
        async for doc in cursor:
            defaults[doc["key"]] = doc.get("value")
        return defaults

    async def is_maintenance(self) -> bool:
        return bool(await self.get_config("maintenance_mode", False))

    async def toggle_maintenance(self) -> bool:
        current = await self.is_maintenance()
        new_value = not current
        await self.set_config("maintenance_mode", new_value)
        await self.add_log("admin", f"Maintenance mode set to {new_value}")
        return new_value

    async def toggle_config_bool(self, key: str, default: bool = False) -> bool:
        current = bool(await self.get_config(key, default))
        new_value = not current
        await self.set_config(key, new_value)
        await self.add_log("admin", f"{key} set to {new_value}")
        return new_value

    async def set_ban(self, user_id: int, banned: bool) -> None:
        await self.db.users.update_one({"user_id": int(user_id)}, {"$set": {"is_banned": banned}}, upsert=True)
        await self.add_log("admin", f"User {user_id} banned={banned}", user_id=int(user_id))

    async def activate_premium(self, user_id: int, days: int, source: str = "admin") -> datetime:
        user = await self.get_user(user_id)
        now = utcnow()
        current_until = user.get("premium_until") if user else None
        base = current_until if isinstance(current_until, datetime) and current_until > now else now
        premium_until = base + timedelta(days=days)
        await self.db.users.update_one(
            {"user_id": int(user_id)},
            {"$set": {"is_premium": True, "premium_until": premium_until}},
            upsert=True,
        )
        await self.add_log("premium", f"Premium activated for {user_id} until {premium_until.isoformat()} via {source}", user_id=user_id)
        return premium_until

    async def remove_premium(self, user_id: int) -> None:
        await self.db.users.update_one({"user_id": int(user_id)}, {"$set": {"is_premium": False, "premium_until": None}}, upsert=True)
        await self.add_log("premium", f"Premium removed for {user_id}", user_id=user_id)

    async def expire_due_premium(self) -> int:
        result = await self.db.users.update_many(
            {"is_premium": True, "premium_until": {"$lte": utcnow()}},
            {"$set": {"is_premium": False, "premium_until": None}},
        )
        if result.modified_count:
            await self.add_log("premium", f"Expired {result.modified_count} premium user(s)")
        return result.modified_count

    async def add_force_channel(self, target: str, label: str, invite_link: str = "", mode: str = "join") -> str:
        doc = {
            "target": target,
            "label": label,
            "invite_link": invite_link,
            "mode": mode if mode in {"join", "request"} else "join",
            "enabled": True,
            "created_at": utcnow(),
        }
        inserted = await self.db.force_channels.insert_one(doc)
        await self.add_log("force_subscription", f"Added force channel {label} ({target})")
        return str(inserted.inserted_id)

    async def set_force_channel_enabled(self, channel_id: str, enabled: bool) -> bool:
        if not ObjectId.is_valid(channel_id):
            return False
        result = await self.db.force_channels.update_one(
            {"_id": ObjectId(channel_id)},
            {"$set": {"enabled": bool(enabled), "updated_at": utcnow()}},
        )
        if result.modified_count:
            await self.add_log("force_subscription", f"Force channel {channel_id} enabled={enabled}")
        return result.matched_count > 0

    async def list_force_channels(self, enabled_only: bool = True) -> list[dict[str, Any]]:
        query = {"enabled": True} if enabled_only else {}
        cursor = self.db.force_channels.find(query).sort("created_at", DESCENDING)
        return await cursor.to_list(length=None)

    async def delete_force_channel(self, channel_id: str) -> bool:
        if not ObjectId.is_valid(channel_id):
            return False
        result = await self.db.force_channels.delete_one({"_id": ObjectId(channel_id)})
        await self.add_log("force_subscription", f"Deleted force channel {channel_id}")
        return result.deleted_count > 0

    async def record_force_request(self, user_id: int, chat_id: int, username: str | None = None, title: str | None = None) -> None:
        now = utcnow()
        identifiers = [str(chat_id)]
        if username:
            identifiers.append(f"@{username.lstrip('@')}")
        await self.db.force_subscription_requests.update_one(
            {"user_id": int(user_id), "chat_id": int(chat_id)},
            {
                "$set": {
                    "user_id": int(user_id),
                    "chat_id": int(chat_id),
                    "username": username.lstrip("@") if username else "",
                    "title": title or "",
                    "identifiers": identifiers,
                    "updated_at": now,
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )
        await self.add_log("force_subscription", f"Join request recorded for {user_id} in {chat_id}", user_id=int(user_id))

    async def has_force_request(self, user_id: int, target: str) -> bool:
        target = str(target).strip()
        candidates = {target}
        if target.startswith("https://t.me/"):
            suffix = target.removeprefix("https://t.me/").strip("/")
            if suffix and "/" not in suffix and not suffix.startswith("+"):
                candidates.add(f"@{suffix}")
        if target.startswith("@"):
            candidates.add(target)
            candidates.add(target[1:])
        query = {
            "user_id": int(user_id),
            "$or": [
                {"identifiers": {"$in": list(candidates)}},
                {"username": {"$in": [candidate.lstrip("@") for candidate in candidates]}},
            ],
        }
        return bool(await self.db.force_subscription_requests.find_one(query))

    async def record_broadcast(self, admin_id: int, total: int, sent: int, failed: int) -> None:
        await self.db.broadcasts.insert_one(
            {
                "admin_id": int(admin_id),
                "total": total,
                "sent": sent,
                "failed": failed,
                "created_at": utcnow(),
                "status": "Completed",
            }
        )
        await self.add_log("broadcast", f"Broadcast completed: {sent}/{total} sent, {failed} failed", user_id=int(admin_id))

    async def referral_leaderboard(self, limit: int = 10) -> list[dict[str, Any]]:
        cursor = self.db.users.find({"valid_referrals": {"$gt": 0}}).sort("valid_referrals", DESCENDING).limit(limit)
        return await cursor.to_list(length=limit)

    async def _maybe_apply_referral_reward(self, referrer_id: int) -> None:
        if not bool(await self.get_config("referral_rewards_enabled", False)):
            return
        required = int(await self.get_config("referral_required_joins", 3) or 3)
        reward_days = int(await self.get_config("referral_reward_days", 7) or 7)
        referrer = await self.get_user(referrer_id)
        if not referrer:
            return
        valid_referrals = int(referrer.get("valid_referrals", 0))
        if required > 0 and valid_referrals > 0 and valid_referrals % required == 0:
            await self.activate_premium(referrer_id, reward_days, source="referral")


def _parse_referral(value: str | None) -> int | None:
    if not value:
        return None
    cleaned = value.strip()
    if cleaned.startswith("ref_"):
        cleaned = cleaned[4:]
    try:
        return int(cleaned)
    except ValueError:
        return None
