"""Data structures used across the application."""
from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field

TYPE_RECEIVED = "received"
TYPE_SPENT = "spent"
TYPES = (TYPE_RECEIVED, TYPE_SPENT)

CATEGORIES: dict[str, list[str]] = {
    TYPE_RECEIVED: ["Allowance", "Gift", "Part-time Job", "Prize", "Refund", "Other"],
    TYPE_SPENT: [
        "Food",
        "Transport",
        "Books & Stationery",
        "Entertainment",
        "Shopping",
        "Mobile Recharge",
        "Health",
        "Other",
    ],
}

CURRENCY = "₹"


def new_id() -> str:
    return uuid.uuid4().hex[:8]


@dataclass
class Transaction:
    """A single pocket-money entry (money received or money spent)."""

    date: str  # ISO format YYYY-MM-DD
    type: str  # "received" or "spent"
    category: str
    amount: float
    note: str = ""
    id: str = field(default_factory=new_id)

    @property
    def signed_amount(self) -> float:
        """Positive for money received, negative for money spent."""
        return self.amount if self.type == TYPE_RECEIVED else -self.amount

    def to_dict(self) -> dict:
        return asdict(self)


def fmt_money(value: float) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}{CURRENCY}{abs(value):,.2f}"
