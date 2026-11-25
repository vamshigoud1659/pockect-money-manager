"""Unit tests for Pocket Money Manager.  Run:  python -m unittest -v"""
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from pmm.logic import add_transaction, balance, check_warnings, search, summarize
from pmm.models import Transaction
from pmm.storage import load_transactions, merge, parse_csv, save_transactions
from pmm.validation import ValidationError, validate_amount, validate_date, validate_record

TODAY = date(2026, 11, 22)


def tx(d, t, c, a, note=""):
    return Transaction(date=d, type=t, category=c, amount=a, note=note)


class ValidationTests(unittest.TestCase):
    def test_amount_accepts_normal_values(self):
        self.assertEqual(validate_amount("250"), 250.0)
        self.assertEqual(validate_amount(" 99.50 "), 99.5)
        self.assertEqual(validate_amount("1,200"), 1200.0)

    def test_amount_boundaries(self):
        self.assertEqual(validate_amount("0.01"), 0.01)
        self.assertEqual(validate_amount("100000"), 100000.0)
        for bad in ("", "abc", "-5", "0", "12.345", "100000.01"):
            with self.assertRaises(ValidationError, msg=bad):
                validate_amount(bad)

    def test_date_rules(self):
        self.assertEqual(validate_date("2026-11-22", today=TODAY), "2026-11-22")
        self.assertEqual(validate_date("", today=TODAY), "2026-11-22")  # blank = today
        for bad in ("2026-11-23", "2026-13-01", "22/11/2026", "1999-12-31"):
            with self.assertRaises(ValidationError, msg=bad):
                validate_date(bad, today=TODAY)

    def test_category_must_match_type(self):
        with self.assertRaises(ValidationError):
            validate_record({"date": "2026-11-01", "type": "spent", "category": "Allowance", "amount": "10"}, today=TODAY)
        r = validate_record({"date": "2026-11-01", "type": "SPENT", "category": "food", "amount": "10"}, today=TODAY)
        self.assertEqual((r.type, r.category), ("spent", "Food"))


class LogicTests(unittest.TestCase):
    def setUp(self):
        self.data = [
            tx("2026-10-01", "received", "Allowance", 3000),
            tx("2026-10-05", "spent", "Food", 500, "canteen"),
            tx("2026-11-01", "received", "Allowance", 3000),
            tx("2026-11-03", "spent", "Transport", 200, "bus pass"),
            tx("2026-11-04", "spent", "Food", 300, "pizza"),
        ]

    def test_balance_is_received_minus_spent(self):
        self.assertEqual(balance(self.data), 5000.0)

    def test_summary_totals(self):
        s = summarize(self.data)
        self.assertEqual((s.total_received, s.total_spent, s.balance), (6000.0, 1000.0, 5000.0))
        self.assertEqual(s.top_category, "Food")
        self.assertEqual(s.status, "Healthy")
        self.assertEqual([m["month"] for m in s.monthly], ["2026-10", "2026-11"])

    def test_overspending_status(self):
        s = summarize([tx("2026-11-01", "received", "Gift", 100), tx("2026-11-02", "spent", "Food", 150)])
        self.assertEqual(s.status, "Overspending")
        self.assertEqual(s.balance, -50.0)

    def test_search_by_keyword_type_and_dates(self):
        self.assertEqual(len(search(self.data, keyword="pizza")), 1)
        self.assertEqual(len(search(self.data, tx_type="spent")), 3)
        self.assertEqual(len(search(self.data, start="2026-11-01", end="2026-11-03")), 2)

    def test_budget_warning(self):
        warns = check_warnings(self.data, monthly_budget=400, low_balance_threshold=100, today=TODAY)
        self.assertTrue(any("budget exceeded" in w.message.lower() for w in warns))

    def test_negative_balance_is_critical(self):
        data = [tx("2026-11-02", "spent", "Food", 50)]
        warns = check_warnings(data, monthly_budget=0, low_balance_threshold=100, today=TODAY)
        self.assertEqual(warns[0].level, "critical")

    def test_add_transaction_rejects_bad_input(self):
        with self.assertRaises(ValidationError):
            add_transaction(self.data, {"date": "2026-11-05", "type": "spent", "category": "Food", "amount": "abc"})
        self.assertEqual(len(self.data), 5)


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.file = self.dir / "t.json"

    def test_round_trip(self):
        data = [tx("2026-11-01", "received", "Gift", 100, "hi")]
        save_transactions(data, self.file)
        loaded, notices = load_transactions(self.file)
        self.assertEqual(loaded[0].to_dict(), data[0].to_dict())
        self.assertEqual(notices, [])

    def test_missing_file_creates_template(self):
        loaded, notices = load_transactions(self.file)
        self.assertEqual(loaded, [])
        self.assertTrue(self.file.exists())

    def test_corrupted_file_is_backed_up(self):
        self.file.write_text("{not json")
        loaded, notices = load_transactions(self.file)
        self.assertEqual(loaded, [])
        self.assertTrue(any(p.name.startswith("t.corrupt-") for p in self.dir.iterdir()))
        self.assertEqual(json.loads(self.file.read_text())["transactions"], [])

    def test_bad_records_are_skipped(self):
        self.file.write_text(json.dumps({"version": 1, "transactions": [
            {"id": "a", "date": "2026-11-01", "type": "spent", "category": "Food", "amount": 10},
            {"id": "b", "date": "2026-11-01", "type": "spent", "category": "Food", "amount": "oops"},
        ]}))
        loaded, notices = load_transactions(self.file)
        self.assertEqual([t.id for t in loaded], ["a"])
        self.assertEqual(len(notices), 1)

    def test_csv_import_reports_bad_rows_and_is_idempotent(self):
        text = "date,type,category,amount,note\n2026-11-01,spent,Food,50,ok\n2026-11-01,spent,Food,xx,bad\n"
        valid, errors = parse_csv(text)
        self.assertEqual(len(valid), 1)
        self.assertEqual(errors[0][0], 3)
        merged, added = merge(valid, parse_csv(text)[0])
        self.assertEqual(added, 0)

    def test_csv_missing_columns(self):
        valid, errors = parse_csv("date,amount\n2026-11-01,5\n")
        self.assertEqual(valid, [])
        self.assertIn("missing", errors[0][1])


if __name__ == "__main__":
    unittest.main()
