from __future__ import annotations

import os
from dataclasses import dataclass


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _int_env(name: str, default: int) -> int:
    value = _env(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _id_set(value: str) -> set[int]:
    ids: set[int] = set()
    for item in value.replace(" ", ",").split(","):
        item = item.strip()
        if not item:
            continue
        try:
            ids.add(int(item))
        except ValueError:
            continue
    return ids


@dataclass(frozen=True)
class Settings:
    bot_token: str
    mongo_url: str
    mongo_db_name: str
    admin_ids: set[int]
    owner_ids: set[int]
    support_username: str
    update_channel: str
    start_photo_url: str
    free_daily_limit: int
    premium_daily_limit: int
    max_text_chars: int

    @property
    def all_admin_ids(self) -> set[int]:
        return self.admin_ids | self.owner_ids

    def is_admin(self, user_id: int | None) -> bool:
        return bool(user_id and user_id in self.all_admin_ids)

    @property
    def support_label(self) -> str:
        return f"@{self.support_username}" if self.support_username else "Not configured"

    @property
    def update_channel_label(self) -> str:
        return f"@{self.update_channel}" if self.update_channel else "Not configured"

    def missing_required(self) -> list[str]:
        missing = []
        if not self.bot_token:
            missing.append("BOT_TOKEN")
        if not self.mongo_url:
            missing.append("MONGO_URL")
        if not self.admin_ids:
            missing.append("ADMIN_IDS")
        if not self.owner_ids:
            missing.append("OWNER_IDS")
        if not self.support_username:
            missing.append("SUPPORT_USERNAME")
        if not self.update_channel:
            missing.append("UPDATE_CHANNEL")
        return missing


def load_settings() -> Settings:
    mongo_url = _env("MONGO_URL") or _env("MONGO_URI") or _env("MONGO_DB_URI")
    return Settings(
        bot_token=_env("BOT_TOKEN"),
        mongo_url=mongo_url,
        mongo_db_name=_env("MONGO_DB_NAME", "text_tool_bot"),
        admin_ids=_id_set(_env("ADMIN_IDS")),
        owner_ids=_id_set(_env("OWNER_IDS") or _env("OWNER_ID")),
        support_username=_env("SUPPORT_USERNAME").lstrip("@"),
        update_channel=_env("UPDATE_CHANNEL").lstrip("@"),
        start_photo_url=_env("START_PHOTO_URL"),
        free_daily_limit=_int_env("FREE_DAILY_LIMIT", 50),
        premium_daily_limit=_int_env("PREMIUM_DAILY_LIMIT", 500),
        max_text_chars=_int_env("MAX_TEXT_CHARS", 3000),
    )
