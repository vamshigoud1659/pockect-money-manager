"""Defensive input validation.

Every function either returns a clean, normalised value or raises
ValidationError with a friendly message explaining what is wrong.
"""
from __future__ import annotations

import re
from datetime import date, datetime

from .models import CATEGORIES, TYPES, Transaction, new_id

MIN_AMOUNT = 0.01
MAX_AMOUNT = 100_000.00  # a single pocket-money entry above this is rejected
MAX_NOTE_LENGTH = 100
EARLIEST_DATE = date(2000, 1, 1)
_AMOUNT_RE = re.compile(r"^\d+(\.\d{1,2})?$")


class ValidationError(ValueError):
    """Raised when a user-supplied value breaks a domain rule."""


def validate_amount(value) -> float:
    text = str(value).strip().replace(",", "").lstrip("₹").strip() if value is not None else ""
    if not text:
        raise ValidationError("Amount cannot be empty.")
    if text.startswith("-"):
        raise ValidationError("Amount must be positive. Choose 'spent' to record money going out.")
    if not _AMOUNT_RE.match(text):
        raise ValidationError(f"'{value}' is not a valid amount. Use numbers like 250 or 99.50 (max 2 decimals).")
    amount = float(text)
    if amount < MIN_AMOUNT:
        raise ValidationError("Amount must be greater than zero.")
    if amount > MAX_AMOUNT:
        raise ValidationError(f"Amount is too large. The maximum for one entry is {MAX_AMOUNT:,.0f}.")
    return round(amount, 2)


def validate_date(value, today: date | None = None) -> str:
    today = today or date.today()
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        parsed = value
    else:
        text = str(value or "").strip()
        if not text:
            return today.isoformat()  # blank date means "today"
        try:
            parsed = datetime.strptime(text, "%Y-%m-%d").date()
        except ValueError:
            raise ValidationError(f"'{text}' is not a valid date. Use the format YYYY-MM-DD, e.g. 2026-11-22.")
    if parsed > today:
        raise ValidationError("Date cannot be in the future.")
    if parsed < EARLIEST_DATE:
        raise ValidationError(f"Date must be on or after {EARLIEST_DATE.isoformat()}.")
    return parsed.isoformat()


def validate_type(value) -> str:
    text = str(value or "").strip().lower()
    aliases = {"r": "received", "in": "received", "income": "received", "s": "spent", "out": "spent", "expense": "spent"}
    text = aliases.get(text, text)
    if text not in TYPES:
        raise ValidationError(f"Type must be 'received' or 'spent' (got '{value}').")
    return text


def validate_category(tx_type: str, value) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValidationError("Category cannot be empty.")
    for cat in CATEGORIES[tx_type]:
        if cat.lower() == text.lower():
            return cat
    allowed = ", ".join(CATEGORIES[tx_type])
    raise ValidationError(f"'{text}' is not a valid category for '{tx_type}'. Choose one of: {allowed}.")


def validate_note(value) -> str:
    text = " ".join(str(value or "").split())  # collapse whitespace / newlines
    if len(text) > MAX_NOTE_LENGTH:
        raise ValidationError(f"Note is too long ({len(text)} characters). Keep it under {MAX_NOTE_LENGTH}.")
    return text


def validate_record(raw: dict, today: date | None = None) -> Transaction:
    """Validate a whole record (from a form, CSV row or JSON file)."""
    if not isinstance(raw, dict):
        raise ValidationError("Record must be an object with fields.")
    tx_type = validate_type(raw.get("type"))
    if not str(raw.get("date") or "").strip():
        raise ValidationError("Date is missing.")
    rid = str(raw.get("id") or "").strip() or new_id()
    return Transaction(
        id=rid,
        date=validate_date(raw.get("date"), today=today),
        type=tx_type,
        category=validate_category(tx_type, raw.get("category")),
        amount=validate_amount(raw.get("amount")),
        note=validate_note(raw.get("note")),
    )
