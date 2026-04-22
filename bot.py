"""Телеграм-бот: 25 вопросов → график по 7 уровням + текстовый результат."""

from __future__ import annotations

import logging
import os

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from chart import render_chart
from questions import QUESTIONS, score_by_level
from results import build_result_text

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

ANSWER_EMOJI = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]


def question_keyboard(index: int) -> InlineKeyboardMarkup:
    row = [
        InlineKeyboardButton(ANSWER_EMOJI[i], callback_data=f"ans:{index}:{i + 1}")
        for i in range(4)
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
    await update.message.reply_text(
        "Привет! Это диагностика из 25 вопросов по 7 уровням.\n\n"
        "В каждом вопросе выбери один из четырёх вариантов кнопкой. "
        "После последнего вопроса я пришлю график и расшифровку результата.\n\n"
        "Чтобы начать заново в любой момент — /start.",
    )
    await send_question(update, context, 0)


async def send_question(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    index: int,
) -> None:
    text = format_question(index)
    keyboard = question_keyboard(index)
    if update.callback_query:
        await update.callback_query.message.reply_text(
            text, reply_markup=keyboard, parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(
            text, reply_markup=keyboard, parse_mode=ParseMode.HTML
        )


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
        "Чтобы пройти тест ещё раз — отправьте /start.",
    )

    context.user_data["answers"] = []


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit(
            "Переменная окружения TELEGRAM_BOT_TOKEN не задана. "
            "Положите токен в .env или экспортируйте перед запуском."
        )

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(on_answer, pattern=r"^ans:\d+:[1-4]$"))

    logger.info("Бот запускается…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
