"""Local persistence: JSON for app state, CSV for import/export.

Handles missing or corrupted files gracefully so the app never crashes on start-up.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

from .models import Transaction
from .validation import ValidationError, validate_record

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
EXPORT_DIR = BASE_DIR / "exports"
DATA_FILE = DATA_DIR / "transactions.json"
SETTINGS_FILE = DATA_DIR / "settings.json"
SAMPLE_JSON = DATA_DIR / "sample_transactions.json"
SAMPLE_CSV = DATA_DIR / "sample_transactions.csv"

SCHEMA_VERSION = 1
CSV_FIELDS = ["id", "date", "type", "category", "amount", "note"]
DEFAULT_SETTINGS = {"monthly_budget": 3000.0, "low_balance_threshold": 500.0, "student_name": "Student"}


def _atomic_write(path: Path, text: str) -> None:
    """Write to a temp file first, then swap - a crash never leaves a half-written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.replace(tmp, path)


def _backup_corrupt(path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = path.with_name(f"{path.stem}.corrupt-{stamp}{path.suffix}")
    shutil.copy(path, backup)
    return backup


def load_transactions(path: Path = DATA_FILE) -> tuple[list[Transaction], list[str]]:
    """Load records. Returns (transactions, notices). Never raises for bad files."""
    notices: list[str] = []
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        save_transactions([], path)
        notices.append(f"No data file found - created a fresh one at {Path(path).name}.")
        return [], notices
    except (json.JSONDecodeError, UnicodeDecodeError):
        backup = _backup_corrupt(Path(path))
        save_transactions([], path)
        notices.append(f"Data file was corrupted. A backup was saved as {backup.name} and a clean file was created.")
        return [], notices

    # schema check: accept {"version":1,"transactions":[...]} or a bare list
    records = raw.get("transactions") if isinstance(raw, dict) else raw
    if not isinstance(records, list):
        backup = _backup_corrupt(Path(path))
        save_transactions([], path)
        notices.append(f"Data file had an unexpected structure. Backup saved as {backup.name}.")
        return [], notices

    transactions: list[Transaction] = []
    seen: set[str] = set()
    for i, rec in enumerate(records, start=1):
        try:
            tx = validate_record(rec)
        except ValidationError as exc:
            notices.append(f"Skipped record #{i}: {exc}")
            continue
        if tx.id in seen:
            notices.append(f"Skipped record #{i}: duplicate id {tx.id}.")
            continue
        seen.add(tx.id)
        transactions.append(tx)
    transactions.sort(key=lambda t: t.date)
    return transactions, notices


def save_transactions(transactions: list[Transaction], path: Path = DATA_FILE) -> None:
    payload = {
        "version": SCHEMA_VERSION,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "transactions": [t.to_dict() for t in transactions],
    }
    _atomic_write(Path(path), json.dumps(payload, indent=2, ensure_ascii=False))


def load_settings(path: Path = SETTINGS_FILE) -> dict:
    settings = dict(DEFAULT_SETTINGS)
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if isinstance(data, dict):
            for key in DEFAULT_SETTINGS:
                if key in data:
                    settings[key] = data[key]
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError):
        save_settings(settings, path)
    return settings


def save_settings(settings: dict, path: Path = SETTINGS_FILE) -> None:
    _atomic_write(Path(path), json.dumps(settings, indent=2))


def parse_csv(text: str) -> tuple[list[Transaction], list[tuple[int, str]]]:
    """Bulk import: validate every CSV row. Returns (valid records, [(row_number, error)])."""
    valid: list[Transaction] = []
    errors: list[tuple[int, str]] = []
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
    header = [h.strip().lower() for h in (reader.fieldnames or [])]
    missing = [f for f in ("date", "type", "category", "amount") if f not in header]
    if missing:
        return [], [(1, f"Header is missing required column(s): {', '.join(missing)}.")]
    for row_no, row in enumerate(reader, start=2):  # row 1 is the header
        clean = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
        if not any(clean.values()):
            errors.append((row_no, "Empty row skipped."))
            continue
        if not clean.get("id"):
            # stable id from the row content, so importing the same file twice adds nothing new
            key = "|".join(clean.get(f, "") for f in ("date", "type", "category", "amount", "note"))
            clean["id"] = "i" + hashlib.sha1(key.encode()).hexdigest()[:7]
        try:
            valid.append(validate_record(clean))
        except ValidationError as exc:
            errors.append((row_no, str(exc)))
    return valid, errors


def import_csv_file(path: Path) -> tuple[list[Transaction], list[tuple[int, str]]]:
    try:
        text = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return [], [(0, f"File not found: {path}")]
    except UnicodeDecodeError:
        return [], [(0, "File is not valid UTF-8 text.")]
    return parse_csv(text)


def merge(existing: list[Transaction], incoming: list[Transaction]) -> tuple[list[Transaction], int]:
    """Add incoming records whose id is new. Returns (merged list, number added)."""
    ids = {t.id for t in existing}
    added = [t for t in incoming if t.id not in ids]
    merged = sorted(existing + added, key=lambda t: t.date)
    return merged, len(added)


def to_csv(transactions: list[Transaction]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_FIELDS)
    writer.writeheader()
    for t in transactions:
        writer.writerow(t.to_dict())
    return buf.getvalue()


def load_sample() -> list[Transaction]:
    records, _ = load_transactions(SAMPLE_JSON)
    return records
