from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

BTN_START = "🌱 Запусти меня"
BTN_RESTART = "🔄 Перезапуск дня"


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_START)], [KeyboardButton(text=BTN_RESTART)]],
        resize_keyboard=True,
    )


def _btn(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)


def propose(sid: int, minutes: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn(f"Погнали ({minutes} мин)", f"go:{sid}")],
            [_btn("Ещё меньше", f"smaller:{sid}"), _btn("Не сейчас", f"later:{sid}")],
        ]
    )


def checkin(sid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn("Продолжаю", f"more:{sid}"), _btn("Сделано", f"done:{sid}")],
            [_btn("Застрял(а)", f"stuck:{sid}")],
        ]
    )


def after_step(sid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn("Дальше", f"next:{sid}")],
            [_btn("На сегодня хватит", f"enough:{sid}")],
        ]
    )
