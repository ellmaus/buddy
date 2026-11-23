import asyncio
import logging

from aiogram import Bot, Dispatcher

import config
from db import DB
from handlers import router
from scheduler import run_scheduler


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    if not config.BOT_TOKEN:
        raise SystemExit("Не задан BOT_TOKEN (см. .env.example)")

    db = DB(config.DB_PATH)
    await db.connect()

    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher(db=db)  # db попадёт в хендлеры как аргумент
    dp.include_router(router)

    scheduler_task = asyncio.create_task(run_scheduler(bot, db))
    try:
        await dp.start_polling(bot)
    finally:
        scheduler_task.cancel()
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
