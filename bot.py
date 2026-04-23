"""Телеграм-бот: 25 вопросов → график по 7 уровням + текстовый результат."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from chart import render_chart
from level_descriptions import LEVEL_DESCRIPTIONS, LEVEL_TITLES
from questions import QUESTIONS, score_by_level
from results import build_result_text

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

ANSWER_EMOJI = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
LEVEL_EMOJI = {1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣", 7: "7️⃣"}

# Разрядка между Q11 и Q12: показываем картинку и кнопку «Продолжить тест».
BREAK_AFTER_INDEX = 10  # индекс последнего вопроса перед разрядкой (Q11)
BREAK_IMAGE_PATH = Path(__file__).parent / "assets" / "break.jpg"

WELCOME_TEXT = (
    "Рада вас видеть на первой неделе <b>TRANSFORMATION FIELD</b> 🤍\n\n"
    "Чтобы определить свой денежный уровень, нажимайте кнопку "
    "«Пройти тест».\n\n"
    "Постарайтесь убрать все отвлекающие факторы и отвечайте "
    "максимально честно."
)


def question_keyboard(index: int) -> InlineKeyboardMarkup:
    row = [
        InlineKeyboardButton(ANSWER_EMOJI[i], callback_data=f"ans:{index}:{i + 1}")
        for i in range(4)
    ]
    return InlineKeyboardMarkup([row])


def level_nav_keyboard() -> InlineKeyboardMarkup:
    row = [
        InlineKeyboardButton(LEVEL_EMOJI[i], callback_data=f"level:{i}")
        for i in range(1, 8)
    ]
    return InlineKeyboardMarkup([row])


def format_question(index: int) -> str:
    q = QUESTIONS[index]
    options = "\n".join(
        f"{ANSWER_EMOJI[i]} {opt}" for i, opt in enumerate(q["options"])
    )
    return (
        f"<b>Вопрос {index + 1} из {len(QUESTIONS)}</b>\n\n"
        f"{q['text']}\n\n"
        f"{options}"
    )


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["answers"] = []
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Пройти тест ⬇️", callback_data="start_test")]]
    )
    await update.message.reply_text(
        WELCOME_TEXT,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML,
    )


async def on_start_test(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_reply_markup(reply_markup=None)
    context.user_data["answers"] = []
    await send_question(update, context, 0)


async def send_question(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    index: int,
) -> None:
    text = format_question(index)
    keyboard = question_keyboard(index)
    chat = update.effective_chat
    await chat.send_message(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)


async def send_break(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Продолжить тест ➡️", callback_data="continue_test")]]
    )
    if BREAK_IMAGE_PATH.exists():
        with BREAK_IMAGE_PATH.open("rb") as f:
            await chat.send_photo(photo=f, reply_markup=keyboard)
    else:
        await chat.send_message(
            "Вы большой(ая) молодец! Вы уже прошли половину теста! 🤍\n\n"
            "Осталось ещё немного, и вы узнаете, на каком финансовом "
            "уровне вы находитесь сейчас.\n"
            "Продолжайте в том же духе.",
            reply_markup=keyboard,
        )


async def on_continue_test(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_reply_markup(reply_markup=None)
    answers: list[int] = context.user_data.get("answers", [])
    next_index = len(answers)
    if next_index < len(QUESTIONS):
        await send_question(update, context, next_index)


async def on_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    try:
        _, idx_str, ans_str = query.data.split(":")
        index = int(idx_str)
        answer = int(ans_str)
    except (ValueError, AttributeError):
        return

    answers: list[int] = context.user_data.setdefault("answers", [])

    if index != len(answers):
        await query.edit_message_reply_markup(reply_markup=None)
        return

    answers.append(answer)

    q = QUESTIONS[index]
    chosen_text = q["options"][answer - 1]
    await query.edit_message_text(
        text=(
            f"<b>Вопрос {index + 1} из {len(QUESTIONS)}</b>\n\n"
            f"{q['text']}\n\n"
            f"✅ {ANSWER_EMOJI[answer - 1]} {chosen_text}"
        ),
        parse_mode=ParseMode.HTML,
    )

    if index == BREAK_AFTER_INDEX:
        await send_break(update, context)
        return

    next_index = index + 1
    if next_index < len(QUESTIONS):
        await send_question(update, context, next_index)
    else:
        await finish(update, context, answers)


async def finish(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    answers: list[int],
) -> None:
    scores = score_by_level(answers)
    png = render_chart(scores)
    chat = update.effective_chat

    await chat.send_photo(photo=png, caption="Ваш результат по 7 уровням")
    await chat.send_message(
        build_result_text(scores),
        parse_mode=ParseMode.HTML,
    )
    await chat.send_message(
        "📖 Нажмите на номер уровня, чтобы прочитать расшифровку:",
        reply_markup=level_nav_keyboard(),
    )
    await chat.send_message(
        "Чтобы пройти тест ещё раз — отправьте /start.",
    )

    context.user_data["answers"] = []


async def on_level_click(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()
    try:
        _, lvl_str = query.data.split(":")
        lvl = int(lvl_str)
    except (ValueError, AttributeError):
        return

    text = f"<b>{LEVEL_TITLES[lvl]}</b>\n\n{LEVEL_DESCRIPTIONS[lvl]}"
    await query.message.reply_text(
        text,
        reply_markup=level_nav_keyboard(),
        parse_mode=ParseMode.HTML,
    )


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit(
            "Переменная окружения TELEGRAM_BOT_TOKEN не задана. "
            "Положите токен в .env или экспортируйте перед запуском."
        )

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(on_start_test, pattern=r"^start_test$"))
    app.add_handler(CallbackQueryHandler(on_continue_test, pattern=r"^continue_test$"))
    app.add_handler(CallbackQueryHandler(on_answer, pattern=r"^ans:\d+:[1-4]$"))
    app.add_handler(CallbackQueryHandler(on_level_click, pattern=r"^level:[1-7]$"))

    logger.info("Бот запускается…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
