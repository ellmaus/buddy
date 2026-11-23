import time

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

import config
import keyboards as kb
import splitter
import texts
from db import DB

router = Router()

# Какой статус сессии нужен для каждого действия (защита от старых кнопок и двойных нажатий)
REQUIRED_STATUS = {
    "go": "proposed",
    "smaller": "proposed",
    "later": "proposed",
    "more": "awaiting",
    "done": "awaiting",
    "stuck": "awaiting",
    "next": "step_done",
    "enough": "step_done",
}


@router.message(CommandStart())
async def cmd_start(m: Message):
    await m.answer(texts.WELCOME, reply_markup=kb.main_menu())


@router.message(Command("stop"))
async def cmd_stop(m: Message, db: DB):
    n = await db.cancel_active(m.from_user.id)
    await m.answer(texts.STOPPED if n else texts.NOTHING_TO_STOP)


@router.message(F.text == kb.BTN_START)
async def ask_task(m: Message):
    await m.answer(texts.ASK_TASK)


@router.message(F.text == kb.BTN_RESTART)
async def restart_day(m: Message, db: DB):
    await db.cancel_active(m.from_user.id)
    await m.answer(texts.RESTART)


@router.message(F.text & ~F.text.startswith("/"))
async def new_task(m: Message, db: DB):
    title = m.text.strip()[:200]
    steps = splitter.steps_for(title)
    await db.cancel_active(m.from_user.id)
    sid = await db.create_session(
        m.from_user.id, title, 0, steps[0], config.STEP_MINUTES
    )
    await m.answer(
        texts.propose(steps[0], config.STEP_MINUTES),
        reply_markup=kb.propose(sid, config.STEP_MINUTES),
    )


@router.callback_query(F.data.regexp(r"^(go|smaller|later|more|done|stuck|next|enough):\d+$"))
async def on_action(cb: CallbackQuery, db: DB):
    action, raw_sid = cb.data.split(":")
    sid = int(raw_sid)
    s = await db.get_session(sid)

    if (
        not s
        or s["user_id"] != cb.from_user.id
        or s["status"] != REQUIRED_STATUS[action]
    ):
        await cb.answer(texts.STALE, show_alert=False)
        return

    await cb.answer()
    msg = cb.message
    now = int(time.time())
    steps = splitter.steps_for(s["task_title"])

    if action == "go":
        await db.update_session(sid, status="running", fire_at=now + s["minutes"] * 60)
        await msg.edit_text(texts.started(s["step_text"], s["minutes"]))

    elif action == "smaller":
        step = splitter.tiny_step()
        await db.update_session(sid, step_text=step, minutes=config.TINY_MINUTES, tiny=1)
        await msg.edit_text(
            texts.propose(step, config.TINY_MINUTES),
            reply_markup=kb.propose(sid, config.TINY_MINUTES),
        )

    elif action == "later":
        await db.update_session(sid, status="closed")
        await msg.edit_text(texts.LATER)

    elif action == "more":
        await db.update_session(
            sid, status="running", minutes=config.STEP_MINUTES,
            fire_at=now + config.STEP_MINUTES * 60,
        )
        await msg.edit_text(texts.MORE)

    elif action == "done":
        if s["tiny"]:
            await db.update_session(sid, status="step_done")
            await msg.edit_text(texts.tiny_done(), reply_markup=kb.after_step(sid))
        elif s["step_idx"] + 1 < len(steps):
            await db.update_session(sid, status="step_done")
            await msg.edit_text(texts.step_done(), reply_markup=kb.after_step(sid))
        else:
            await db.update_session(sid, status="closed")
            await msg.edit_text(texts.all_done())

    elif action == "stuck":
        step = splitter.tiny_step()
        await db.update_session(
            sid, step_text=step, minutes=config.TINY_MINUTES, tiny=1, status="proposed"
        )
        await msg.edit_text(
            texts.stuck_then(step, config.TINY_MINUTES),
            reply_markup=kb.propose(sid, config.TINY_MINUTES),
        )

    elif action == "next":
        # После крошечного шага возвращаемся к обычному шагу того же номера,
        # после обычного идём к следующему.
        idx = s["step_idx"] if s["tiny"] else s["step_idx"] + 1
        idx = min(idx, len(steps) - 1)
        await db.update_session(
            sid, step_idx=idx, step_text=steps[idx], minutes=config.STEP_MINUTES,
            tiny=0, status="proposed",
        )
        await msg.edit_text(
            texts.propose(steps[idx], config.STEP_MINUTES),
            reply_markup=kb.propose(sid, config.STEP_MINUTES),
        )

    elif action == "enough":
        await db.update_session(sid, status="closed")
        await msg.edit_text(texts.enough())
