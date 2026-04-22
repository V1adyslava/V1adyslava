"""Генерация графика результатов: 7 столбиков, зелёное — набранные баллы,
красное сверху — сколько не хватает до 100."""

from __future__ import annotations

import io

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from questions import LEVELS

GREEN = "#28d47a"
RED = "#ef4035"
EDGE = "#1f3a5f"


def render_chart(scores: dict[int, int]) -> bytes:
    """Возвращает PNG-картинку с графиком по 7 уровням."""
    labels = LEVELS
    values = [scores[i] for i in range(1, 8)]
    remainders = [max(0, 100 - v) for v in values]

    fig, ax = plt.subplots(figsize=(10, 6), dpi=140)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    ax.bar(
        labels,
        values,
        color=GREEN,
        edgecolor=EDGE,
        linewidth=2.2,
        width=0.78,
        zorder=3,
    )
    ax.bar(
        labels,
        remainders,
        bottom=values,
        color=RED,
        edgecolor=EDGE,
        linewidth=2.2,
        width=0.78,
        zorder=3,
    )

    ax.set_ylim(0, 105)
    ax.set_yticks(range(0, 101, 10))
    ax.yaxis.grid(True, linestyle="-", color="#d0d7de", alpha=0.7, zorder=0)
    ax.set_axisbelow(True)

    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color("#b0b7bf")
    ax.spines["bottom"].set_color("#b0b7bf")

    ax.tick_params(axis="x", labelsize=12, colors="#1f2328")
    ax.tick_params(axis="y", labelsize=11, colors="#1f2328")

    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()
