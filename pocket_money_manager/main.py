"""Pocket Money Manager - interactive terminal version.

Run:  python main.py
(For the web interface run:  streamlit run app.py)
"""
from __future__ import annotations

import os
import sys

from pmm import APP_NAME, VERSION
from pmm.charts import HAS_MPL, save_all_charts
from pmm.logic import add_transaction, check_warnings, delete_transaction, search, summarize
from pmm.models import CATEGORIES, TYPE_RECEIVED, TYPE_SPENT, Transaction, fmt_money
from pmm.reports import export_all
from pmm.storage import (
    EXPORT_DIR,
    import_csv_file,
    load_sample,
    load_settings,
    load_transactions,
    merge,
    save_settings,
    save_transactions,
)
from pmm.validation import ValidationError, validate_amount, validate_category, validate_date, validate_note

if os.name == "nt":
    os.system("")  # enables ANSI colours on Windows terminals

USE_COLOR = sys.stdout.isatty()


def c(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else text


GREEN, RED, YELLOW, CYAN, BOLD, DIM = "32", "31", "33", "36", "1", "2"
PAGE_SIZE = 15


# ----------------------------------------------------------------- input helpers
def ask(prompt: str, validator, allow_blank: bool = False):
    """Keep asking until the validator accepts the input. Ctrl+C returns to the menu."""
    while True:
        try:
            raw = input(c(f"  {prompt}: ", CYAN))
        except EOFError:
            raise KeyboardInterrupt
        if allow_blank and not raw.strip():
            return None
        try:
            return validator(raw)
        except ValidationError as exc:
            print(c(f"  ✗ {exc}", RED))


def choose(prompt: str, options: list[str]) -> str:
    for i, opt in enumerate(options, start=1):
        print(f"    {i}. {opt}")

    def pick(raw: str) -> str:
        raw = raw.strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        for opt in options:
            if opt.lower() == raw.lower():
                return opt
        raise ValidationError(f"Enter a number from 1 to {len(options)}.")

    return ask(prompt, pick)


def pause():
    try:
        input(c("\n  Press Enter to continue...", DIM))
    except EOFError:
        pass


# ----------------------------------------------------------------- display
def banner():
    line = "═" * 58
    print(c(f"\n  ╔{line}╗", GREEN))
    print(c(f"  ║{'💰  ' + APP_NAME.upper():^57}║", GREEN))
    print(c(f"  ║{'Track pocket money received & spent  ·  v' + VERSION:^58}║", GREEN))
    print(c(f"  ╚{line}╝", GREEN))


def print_table(rows: list[Transaction]):
    if not rows:
        print(c("  (no records)", DIM))
        return
    header = f"  {'#':>3}  {'ID':<9}{'DATE':<12}{'TYPE':<10}{'CATEGORY':<20}{'AMOUNT':>12}  NOTE"
    for start in range(0, len(rows), PAGE_SIZE):
        print(c(header, BOLD))
        print("  " + "─" * 92)
        for i, t in enumerate(rows[start : start + PAGE_SIZE], start=start + 1):
            amt = ("+" if t.type == TYPE_RECEIVED else "-") + f"{t.amount:,.2f}"
            amt = c(f"{amt:>12}", GREEN if t.type == TYPE_RECEIVED else RED)
            print(f"  {i:>3}  {t.id:<9}{t.date:<12}{t.type:<10}{t.category[:19]:<20}{amt}  {t.note[:30]}")
        if start + PAGE_SIZE < len(rows):
            try:
                more = input(c(f"\n  Showing {start + PAGE_SIZE}/{len(rows)}. Enter for more, q to stop: ", DIM))
            except EOFError:
                more = "q"
            if more.strip().lower() == "q":
                return
            print()


def show_warnings(transactions, settings):
    warns = check_warnings(transactions, settings["monthly_budget"], settings["low_balance_threshold"])
    for w in warns:
        colour = RED if w.level == "critical" else YELLOW
        print(c(f"  ⚠ {w.level.upper()}: {w.message}", colour))
    return warns


# ----------------------------------------------------------------- actions
def add_entry(transactions, tx_type: str):
    print(c(f"\n  ➕ Record money {tx_type}", BOLD))
    print(c("  (Leave date blank for today. Ctrl+C cancels.)", DIM))
    date = ask("Date (YYYY-MM-DD)", validate_date)
    print("  Category:")
    category = choose("Pick a category", CATEGORIES[tx_type])
    amount = ask("Amount", validate_amount)
    note = ask("Note (optional)", validate_note)
    tx = add_transaction(transactions, {"date": date, "type": tx_type, "category": validate_category(tx_type, category), "amount": amount, "note": note})
    save_transactions(transactions)
    print(c(f"  ✓ Saved {tx.type} {fmt_money(tx.amount)} for {tx.category} on {tx.date} (id {tx.id}).", GREEN))


def search_entries(transactions):
    print(c("\n  🔎 Search records (leave any filter blank to skip it)", BOLD))
    kw = input(c("  Keyword in note/category: ", CYAN))
    t = input(c("  Type (received/spent): ", CYAN)).strip().lower() or None
    if t not in (None, TYPE_RECEIVED, TYPE_SPENT):
        print(c("  ✗ Unknown type - ignoring that filter.", YELLOW))
        t = None
    start = ask("From date (YYYY-MM-DD)", validate_date, allow_blank=True)
    end = ask("To date (YYYY-MM-DD)", validate_date, allow_blank=True)
    results = search(transactions, keyword=kw, tx_type=t, start=start, end=end)
    print(c(f"\n  {len(results)} matching record(s), total {fmt_money(sum(r.signed_amount for r in results))}", BOLD))
    print_table(results)


def show_summary(transactions, settings):
    s = summarize(transactions)
    status_colour = {"Healthy": GREEN, "Watch": YELLOW, "Overspending": RED}.get(s.status, DIM)
    print(c("\n  📊 EXECUTIVE SUMMARY", BOLD))
    print("  " + "─" * 46)
    rows = [
        ("Entries", str(s.count)),
        ("Total received", fmt_money(s.total_received)),
        ("Total spent", fmt_money(s.total_spent)),
        ("Balance", fmt_money(s.balance)),
        ("Savings rate", f"{s.savings_rate}%"),
        ("Average received", fmt_money(s.avg_received)),
        ("Average expense", fmt_money(s.avg_spent)),
        ("Largest expense", f"{fmt_money(s.largest_expense.amount)} ({s.largest_expense.category})" if s.largest_expense else "-"),
        ("Top category", s.top_category or "-"),
        ("Spending trend", s.spending_trend),
    ]
    for label, value in rows:
        print(f"  {label:<20}│ {value}")
    print(f"  {'Status':<20}│ " + c(s.status, status_colour + ";1"))
    print(c("\n  Monthly breakdown", BOLD))
    print(f"  {'MONTH':<10}{'RECEIVED':>14}{'SPENT':>14}{'NET':>14}")
    for m in s.monthly:
        net = c(f"{m['net']:>14,.2f}", GREEN if m["net"] >= 0 else RED)
        print(f"  {m['month']:<10}{m['received']:>14,.2f}{m['spent']:>14,.2f}{net}")
    print(c("\n  Spending by category", BOLD))
    biggest = max(s.spending_by_category.values(), default=1)
    for cat, amt in s.spending_by_category.items():
        bar = "█" * max(1, int(amt / biggest * 25))
        print(f"  {cat:<20}{amt:>10,.2f}  {c(bar, GREEN)}")
    print()
    if not show_warnings(transactions, settings):
        print(c("  ✓ No warnings - finances look fine.", GREEN))


def export_reports(transactions, settings):
    paths = export_all(transactions, settings, EXPORT_DIR)
    charts = save_all_charts(transactions, EXPORT_DIR)
    print(c("\n  ✓ Exported:", GREEN))
    for p in paths + charts:
        print(f"    • {p}")
    if not HAS_MPL:
        print(c("  ⚠ matplotlib is not installed - charts skipped (pip install matplotlib).", YELLOW))


def bulk_import(transactions):
    path = input(c("\n  CSV file path (Enter for data/sample_import_with_errors.csv): ", CYAN)).strip()
    path = path or "data/sample_import_with_errors.csv"
    valid, errors = import_csv_file(path)
    merged, added = merge(transactions, valid)
    transactions[:] = merged
    save_transactions(transactions)
    print(c(f"  ✓ Imported {added} record(s).", GREEN))
    if errors:
        print(c(f"  ✗ {len(errors)} row(s) rejected:", RED))
        for row, msg in errors:
            print(c(f"    row {row}: {msg}", RED))


def delete_entry(transactions):
    tx_id = input(c("\n  ID of the record to delete: ", CYAN)).strip()
    match = next((t for t in transactions if t.id == tx_id), None)
    if not match:
        print(c("  ✗ No record with that ID.", RED))
        return
    confirm = input(c(f"  Delete {match.type} {fmt_money(match.amount)} on {match.date}? (y/n): ", YELLOW))
    if confirm.strip().lower() == "y":
        delete_transaction(transactions, tx_id)
        save_transactions(transactions)
        print(c("  ✓ Deleted.", GREEN))


def edit_settings(settings):
    print(c("\n  ⚙ Settings (Enter keeps the current value)", BOLD))
    budget = ask(f"Monthly budget [{settings['monthly_budget']}]", validate_amount, allow_blank=True)
    low = ask(f"Low balance alert [{settings['low_balance_threshold']}]", validate_amount, allow_blank=True)
    name = input(c(f"  Your name [{settings['student_name']}]: ", CYAN)).strip()
    if budget:
        settings["monthly_budget"] = budget
    if low:
        settings["low_balance_threshold"] = low
    if name:
        settings["student_name"] = name[:40]
    save_settings(settings)
    print(c("  ✓ Settings saved.", GREEN))


MENU = [
    ("1", "Record money received"),
    ("2", "Record money spent"),
    ("3", "View all records"),
    ("4", "Search records"),
    ("5", "Summary & warnings"),
    ("6", "Export reports & charts"),
    ("7", "Bulk import from CSV"),
    ("8", "Delete a record"),
    ("9", "Settings"),
    ("10", "Load sample data (42 entries)"),
    ("0", "Exit"),
]


def main():
    transactions, notices = load_transactions()
    settings = load_settings()
    banner()
    for n in notices:
        print(c(f"  ℹ {n}", YELLOW))
    while True:
        s = summarize(transactions)
        print(c(f"\n  Hi {settings['student_name']}! Balance: ", BOLD) + c(fmt_money(s.balance), GREEN if s.balance >= 0 else RED) + c(f"   ({s.count} entries)", DIM))
        for key, label in MENU:
            print(f"   {c(key.rjust(2), CYAN)}  {label}")
        choice = input(c("\n  Choose an option: ", BOLD)).strip()
        try:
            if choice == "1":
                add_entry(transactions, TYPE_RECEIVED)
            elif choice == "2":
                add_entry(transactions, TYPE_SPENT)
            elif choice == "3":
                print_table(transactions)
            elif choice == "4":
                search_entries(transactions)
            elif choice == "5":
                show_summary(transactions, settings)
            elif choice == "6":
                export_reports(transactions, settings)
            elif choice == "7":
                bulk_import(transactions)
            elif choice == "8":
                delete_entry(transactions)
            elif choice == "9":
                edit_settings(settings)
            elif choice == "10":
                transactions[:], added = merge(transactions, load_sample())
                save_transactions(transactions)
                print(c(f"  ✓ Added {added} sample entries.", GREEN))
            elif choice == "0":
                print(c("\n  Data saved. Goodbye! 👋\n", GREEN))
                break
            else:
                print(c("  ✗ Please enter a number from the menu.", RED))
                continue
        except KeyboardInterrupt:
            print(c("\n  Cancelled.", YELLOW))
            continue
        pause()


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\n  Goodbye!")
