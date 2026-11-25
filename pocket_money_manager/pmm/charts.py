"""Matplotlib charts. Falls back gracefully if matplotlib is not installed."""
from __future__ import annotations

from pathlib import Path

from .logic import by_category, monthly, running_balance
from .models import TYPE_SPENT, Transaction

try:
    import matplotlib

    matplotlib.use("Agg")  # no display needed - works in terminal and web app
    import matplotlib.pyplot as plt

    HAS_MPL = True
    plt.rcParams.update({
        "figure.facecolor": "#16241d", "axes.facecolor": "#16241d", "savefig.facecolor": "#16241d",
        "axes.edgecolor": "#5b6e62", "axes.labelcolor": "#eef3ea", "text.color": "#eef3ea",
        "xtick.color": "#eef3ea", "ytick.color": "#eef3ea", "grid.color": "#5b6e62",
        "legend.facecolor": "#16241d", "legend.edgecolor": "#2a3d32",
    })
except ImportError:  # pragma: no cover
    plt = None
    HAS_MPL = False

GREEN = "#3fb27a"
RED = "#e5604f"
INK = "#eef3ea"
PALETTE = ["#3fb27a", "#e0a526", "#c0392b", "#3a7ca5", "#8e6c8a", "#d9734e", "#5a9e8f", "#7a7a7a"]


def _style(ax, title: str):
    ax.set_title(title, fontsize=13, fontweight="bold", color=INK, loc="left")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.tick_params(colors=INK, labelsize=9)
    ax.grid(axis="y", alpha=0.25)


def monthly_chart(transactions: list[Transaction]):
    rows = monthly(transactions)
    fig, ax = plt.subplots(figsize=(8, 4))
    labels = [r["month"] for r in rows]
    x = range(len(rows))
    ax.bar([i - 0.2 for i in x], [r["received"] for r in rows], width=0.4, label="Received", color=GREEN)
    ax.bar([i + 0.2 for i in x], [r["spent"] for r in rows], width=0.4, label="Spent", color=RED)
    ax.set_xticks(list(x), labels)
    ax.legend(frameon=False)
    _style(ax, "Money received vs spent per month")
    fig.tight_layout()
    return fig


def category_chart(transactions: list[Transaction]):
    cats = by_category(transactions, TYPE_SPENT)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    if cats:
        wedges, _texts, _pcts = ax.pie(
            list(cats.values()),
            autopct=lambda pct: f"{pct:.0f}%" if pct >= 5 else "",
            pctdistance=0.78,
            startangle=90,
            counterclock=False,
            colors=PALETTE[: len(cats)] + PALETTE[: max(0, len(cats) - len(PALETTE))],
            wedgeprops={"width": 0.45, "edgecolor": "white"},
            textprops={"fontsize": 9, "color": "white", "fontweight": "bold"},
        )
        ax.legend(wedges, list(cats.keys()), loc="center left", bbox_to_anchor=(1, 0.5), frameon=False, fontsize=9)
    ax.set_title("Where the money goes", fontsize=13, fontweight="bold", color=INK, loc="left")
    fig.tight_layout()
    return fig


def balance_chart(transactions: list[Transaction]):
    series = running_balance(transactions)
    fig, ax = plt.subplots(figsize=(11, 3.6))
    if series:
        days = [d for d, _ in series]
        vals = [v for _, v in series]
        ax.plot(days, vals, color=GREEN, linewidth=2, marker="o", markersize=3)
        ax.fill_between(days, vals, 0, color=GREEN, alpha=0.12)
        ax.axhline(0, color=RED, linewidth=1, linestyle="--")
        step = max(1, len(days) // 8)
        ax.set_xticks(days[::step])
        ax.tick_params(axis="x", rotation=30)
    _style(ax, "Balance over time")
    fig.tight_layout()
    return fig


def save_all_charts(transactions: list[Transaction], out_dir: Path) -> list[Path]:
    """Save all charts as PNG files. Returns the list of saved paths (empty if matplotlib missing)."""
    if not HAS_MPL:
        return []
    out_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    for name, maker in (("monthly", monthly_chart), ("categories", category_chart), ("balance", balance_chart)):
        fig = maker(transactions)
        path = out_dir / f"chart_{name}.png"
        fig.savefig(path, dpi=130)
        plt.close(fig)
        saved.append(path)
    return saved
