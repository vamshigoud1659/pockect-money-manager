"""Multi-format summary export: Markdown, plain-text audit log and CSV."""
from __future__ import annotations

import csv
import io
from datetime import datetime
from pathlib import Path

from . import APP_NAME
from .logic import Summary, check_warnings, summarize
from .models import Transaction, fmt_money


def markdown_report(transactions: list[Transaction], settings: dict) -> str:
    s = summarize(transactions)
    warns = check_warnings(transactions, settings["monthly_budget"], settings["low_balance_threshold"])
    lines = [
        f"# {APP_NAME} - Summary Report",
        "",
        f"*Prepared for {settings.get('student_name', 'Student')} on {datetime.now():%d %b %Y, %H:%M}*",
        "",
        "## Overview",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Entries | {s.count} |",
        f"| Total received | {fmt_money(s.total_received)} |",
        f"| Total spent | {fmt_money(s.total_spent)} |",
        f"| Balance | {fmt_money(s.balance)} |",
        f"| Savings rate | {s.savings_rate}% |",
        f"| Average expense | {fmt_money(s.avg_spent)} |",
        f"| Top spending category | {s.top_category or '-'} |",
        f"| Spending trend (last month) | {s.spending_trend} |",
        f"| Status | **{s.status}** |",
        "",
        "## Monthly breakdown",
        "",
        "| Month | Received | Spent | Net |",
        "|---|---|---|---|",
    ]
    lines += [f"| {m['month']} | {fmt_money(m['received'])} | {fmt_money(m['spent'])} | {fmt_money(m['net'])} |" for m in s.monthly]
    lines += ["", "## Spending by category", "", "| Category | Amount | Share |", "|---|---|---|"]
    for cat, amt in s.spending_by_category.items():
        share = amt / s.total_spent * 100 if s.total_spent else 0
        lines.append(f"| {cat} | {fmt_money(amt)} | {share:.1f}% |")
    lines += ["", "## Warnings", ""]
    lines += [f"- **{w.level.upper()}**: {w.message}" for w in warns] or ["- None. All good!"]
    return "\n".join(lines) + "\n"


def text_audit_log(transactions: list[Transaction]) -> str:
    s: Summary = summarize(transactions)
    out = [f"{APP_NAME} AUDIT LOG  generated {datetime.now():%Y-%m-%d %H:%M:%S}", "=" * 78]
    out.append(f"{'DATE':<12}{'ID':<10}{'TYPE':<10}{'CATEGORY':<20}{'AMOUNT':>12}{'BALANCE':>14}")
    out.append("-" * 78)
    run = 0.0
    for t in transactions:
        run += t.signed_amount
        sign = "+" if t.type == "received" else "-"
        out.append(f"{t.date:<12}{t.id:<10}{t.type:<10}{t.category[:19]:<20}{sign + format(t.amount, ',.2f'):>12}{run:>14,.2f}")
    out.append("-" * 78)
    out.append(f"TOTAL RECEIVED {s.total_received:>14,.2f}   TOTAL SPENT {s.total_spent:>14,.2f}   BALANCE {s.balance:>12,.2f}")
    return "\n".join(out) + "\n"


def csv_report(transactions: list[Transaction]) -> str:
    s = summarize(transactions)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["section", "label", "received", "spent", "net"])
    for m in s.monthly:
        w.writerow(["month", m["month"], m["received"], m["spent"], m["net"]])
    for cat, amt in s.spending_by_category.items():
        w.writerow(["category_spent", cat, "", amt, ""])
    w.writerow(["total", "all", s.total_received, s.total_spent, s.balance])
    return buf.getvalue()


def export_all(transactions: list[Transaction], settings: dict, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "summary_report.md": markdown_report(transactions, settings),
        "audit_log.txt": text_audit_log(transactions),
        "summary_report.csv": csv_report(transactions),
    }
    paths = []
    for name, content in files.items():
        p = out_dir / name
        p.write_text(content, encoding="utf-8")
        paths.append(p)
    return paths
