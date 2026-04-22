"""Формирование текста с результатами после графика."""

from __future__ import annotations

from questions import LEVEL_INCOME

DIGITS = {1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣", 7: "7️⃣"}

RED_THRESHOLD = 100  # любой уровень ниже 100 считается «красной зоной»


def build_result_text(scores: dict[int, int]) -> str:
    red_levels = [lvl for lvl in range(1, 8) if scores[lvl] < RED_THRESHOLD]

    if red_levels:
        attention = " _ ".join(DIGITS[lvl] for lvl in red_levels)
    else:
        attention = "Все уровни прокачаны до 100 — красных зон нет. 🎉"

    income_lines = "\n".join(
        f"{DIGITS[lvl]} {LEVEL_INCOME[lvl]}" for lvl in range(1, 8)
    )

    scores_lines = "\n".join(
        f"{DIGITS[lvl]} Уровень {lvl}: {scores[lvl]}/100" for lvl in range(1, 8)
    )

    return (
        "📊 <b>Результаты теста по уровням</b> вы можете видеть на графике выше ⬆️\n\n"
        f"<b>Ваши баллы:</b>\n{scores_lines}\n\n"
        "⚠️ <b>Важно понимать:</b> все уровни проходят параллельно.\n\n"
        "Например, если у вас полностью заполнен 6–7 уровень зелёным цветом, "
        "а 1 уровень отмечен красным — вы всё ещё находитесь на 1 уровне, "
        "так как не прокачали его до конца.\n\n"
        "Вы не сможете вырасти в доходе, пока не прокачаете все уровни "
        "и не уберёте красные зоны.\n\n"
        "💰 <b>Каждому уровню соответствует определённый уровень дохода:</b>\n"
        f"{income_lines}\n\n"
        "🔴 Красным выделены уровни, где не хватало вашего внимания.\n\n"
        "Если говорить ещё конкретнее, то по результатам диагностики "
        "вам стоит обратить внимание на:\n"
        f"{attention}"
    )
