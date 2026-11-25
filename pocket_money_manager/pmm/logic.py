"""Core business logic: balances, summaries, search, trends and warnings."""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from .models import TYPE_RECEIVED, TYPE_SPENT, Transaction
from .validation import validate_record


# ----------------------------------------------------------------- CRUD helpers
def add_transaction(transactions: list[Transaction], raw: dict) -> Transaction:
    """Validate and append a new record. Raises ValidationError on bad input."""
    tx = validate_record(raw)
    transactions.append(tx)
    transactions.sort(key=lambda t: t.date)
    return tx


def delete_transaction(transactions: list[Transaction], tx_id: str) -> bool:
    for i, t in enumerate(transactions):
        if t.id == tx_id:
            del transactions[i]
            return True
    return False


# ----------------------------------------------------------------- calculations
def total(transactions: list[Transaction], tx_type: str) -> float:
    return round(sum(t.amount for t in transactions if t.type == tx_type), 2)


def balance(transactions: list[Transaction]) -> float:
    return round(sum(t.signed_amount for t in transactions), 2)


def running_balance(transactions: list[Transaction]) -> list[tuple[str, float]]:
    """Balance after each day, in date order."""
    per_day: dict[str, float] = defaultdict(float)
    for t in transactions:
        per_day[t.date] += t.signed_amount
    out, run = [], 0.0
    for day in sorted(per_day):
        run += per_day[day]
        out.append((day, round(run, 2)))
    return out


def by_category(transactions: list[Transaction], tx_type: str) -> dict[str, float]:
    sums: dict[str, float] = defaultdict(float)
    for t in transactions:
        if t.type == tx_type:
            sums[t.category] += t.amount
    return dict(sorted(((k, round(v, 2)) for k, v in sums.items()), key=lambda kv: -kv[1]))


def monthly(transactions: list[Transaction]) -> list[dict]:
    """Per-month received / spent / net, oldest first."""
    months: dict[str, dict[str, float]] = defaultdict(lambda: {"received": 0.0, "spent": 0.0})
    for t in transactions:
        months[t.date[:7]][t.type] += t.amount
    rows = []
    for m in sorted(months):
        r, s = round(months[m]["received"], 2), round(months[m]["spent"], 2)
        rows.append({"month": m, "received": r, "spent": s, "net": round(r - s, 2)})
    return rows


@dataclass
class Summary:
    count: int
    total_received: float
    total_spent: float
    balance: float
    avg_received: float
    avg_spent: float
    savings_rate: float  # % of received money not spent
    largest_expense: Transaction | None
    top_category: str | None
    spending_by_category: dict[str, float]
    income_by_category: dict[str, float]
    monthly: list[dict]
    spending_trend: str  # "up", "down", "steady" or "n/a"
    status: str  # "Healthy", "Watch", "Overspending" or "No data"


def _avg(values: list[float]) -> float:
    return round(sum(values) / len(values), 2) if values else 0.0


def spending_trend(months: list[dict]) -> str:
    if len(months) < 2:
        return "n/a"
    prev, last = months[-2]["spent"], months[-1]["spent"]
    if prev == 0:
        return "up" if last > 0 else "steady"
    change = (last - prev) / prev
    if change > 0.10:
        return "up"
    if change < -0.10:
        return "down"
    return "steady"


def financial_status(total_received: float, total_spent: float) -> str:
    if total_received == 0 and total_spent == 0:
        return "No data"
    if total_spent > total_received:
        return "Overspending"
    rate = (total_received - total_spent) / total_received * 100
    return "Healthy" if rate >= 20 else "Watch"


def summarize(transactions: list[Transaction]) -> Summary:
    received = [t.amount for t in transactions if t.type == TYPE_RECEIVED]
    spent_tx = [t for t in transactions if t.type == TYPE_SPENT]
    tr, ts = round(sum(received), 2), round(sum(t.amount for t in spent_tx), 2)
    spend_cat = by_category(transactions, TYPE_SPENT)
    months = monthly(transactions)
    return Summary(
        count=len(transactions),
        total_received=tr,
        total_spent=ts,
        balance=round(tr - ts, 2),
        avg_received=_avg(received),
        avg_spent=_avg([t.amount for t in spent_tx]),
        savings_rate=round((tr - ts) / tr * 100, 1) if tr else 0.0,
        largest_expense=max(spent_tx, key=lambda t: t.amount) if spent_tx else None,
        top_category=next(iter(spend_cat), None),
        spending_by_category=spend_cat,
        income_by_category=by_category(transactions, TYPE_RECEIVED),
        monthly=months,
        spending_trend=spending_trend(months),
        status=financial_status(tr, ts),
    )


# ----------------------------------------------------------------- search
def search(
    transactions: list[Transaction],
    keyword: str = "",
    tx_type: str | None = None,
    category: str | None = None,
    start: str | date | None = None,
    end: str | date | None = None,
) -> list[Transaction]:
    kw = (keyword or "").strip().lower()
    start_s = start.isoformat() if isinstance(start, date) else start
    end_s = end.isoformat() if isinstance(end, date) else end
    out = []
    for t in transactions:
        if kw and kw not in t.note.lower() and kw not in t.category.lower():
            continue
        if tx_type and t.type != tx_type:
            continue
        if category and t.category != category:
            continue
        if start_s and t.date < start_s:
            continue
        if end_s and t.date > end_s:
            continue
        out.append(t)
    return out


# ----------------------------------------------------------------- warnings
@dataclass
class Warning_:
    level: str  # "critical" or "warning"
    message: str


def find_anomalies(transactions: list[Transaction]) -> list[Transaction]:
    """Expenses unusually large compared with the rest (mean + 2 std-devs, min 5 entries)."""
    spent = [t.amount for t in transactions if t.type == TYPE_SPENT]
    if len(spent) < 5:
        return []
    mean = sum(spent) / len(spent)
    std = math.sqrt(sum((x - mean) ** 2 for x in spent) / len(spent))
    limit = mean + 2 * std
    return [t for t in transactions if t.type == TYPE_SPENT and t.amount > limit]


def check_warnings(
    transactions: list[Transaction],
    monthly_budget: float,
    low_balance_threshold: float,
    today: date | None = None,
) -> list[Warning_]:
    today = today or date.today()
    warnings: list[Warning_] = []
    bal = balance(transactions)
    if bal < 0:
        warnings.append(Warning_("critical", f"Balance is negative ({bal:,.2f}). You have spent more than you received."))
    elif transactions and bal < low_balance_threshold:
        warnings.append(Warning_("warning", f"Low balance: only {bal:,.2f} left (alert below {low_balance_threshold:,.2f})."))

    this_month = today.isoformat()[:7]
    spent_now = sum(t.amount for t in transactions if t.type == TYPE_SPENT and t.date.startswith(this_month))
    if monthly_budget > 0:
        if spent_now > monthly_budget:
            warnings.append(Warning_("critical", f"Monthly budget exceeded: spent {spent_now:,.2f} of {monthly_budget:,.2f} this month."))
        elif spent_now >= 0.8 * monthly_budget:
            warnings.append(Warning_("warning", f"Close to budget: {spent_now / monthly_budget:.0%} of this month's budget used."))

    for t in find_anomalies(transactions):
        warnings.append(Warning_("warning", f"Unusually large expense on {t.date}: {t.amount:,.2f} for {t.category} ({t.note or 'no note'})."))
    return warnings
