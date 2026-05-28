from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeDefault

from app.config import load_settings
from app.db import MongoStore
from app.handlers import router


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = load_settings()
    missing = settings.missing_required()
    if missing:
        raise RuntimeError(f"Missing required config vars: {', '.join(missing)}")

    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    store = MongoStore(settings)
    await store.init()

    dp = Dispatcher(storage=MemoryStorage())
    dp["settings"] = settings
    dp["store"] = store
    dp.include_router(router)

    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Open main menu"),
            BotCommand(command="help", description="How to use the bot"),
        ],
        scope=BotCommandScopeDefault(),
    )

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await store.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
