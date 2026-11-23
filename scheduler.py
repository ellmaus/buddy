import asyncio
import logging
import time

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

import config
import keyboards as kb
import texts
from db import DB

log = logging.getLogger(__name__)


async def run_scheduler(bot: Bot, db: DB) -> None:
    """Раз в несколько секунд ищет сработавшие таймеры и шлёт чек-ин.

    Таймеры лежат в БД, поэтому перезапуск бота их не теряет:
    просроченные сработают сразу после старта.
    """
    while True:
        try:
            for s in await db.due_sessions(int(time.time())):
                # Сначала меняем статус, чтобы не отправить чек-ин дважды
                await db.update_session(s["id"], status="awaiting")
                try:
                    await bot.send_message(
                        s["user_id"],
                        texts.checkin(s["minutes"]),
                        reply_markup=kb.checkin(s["id"]),
                    )
                except TelegramAPIError:
                    log.warning("Не удалось отправить чек-ин сессии %s", s["id"])
        except Exception:
            log.exception("Ошибка в планировщике")
        await asyncio.sleep(config.SCHEDULER_INTERVAL)
