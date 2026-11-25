"""Generate the realistic sample datasets in data/ (CSV + JSON).

Run:  python seed_data.py
Creates:
    data/sample_transactions.csv / .json   - 42 valid entries (Aug-Nov 2026)
    data/sample_import_with_errors.csv     - rows with deliberate mistakes to demo validation
"""
import csv
import json
from pathlib import Path

DATA = Path(__file__).parent / "data"

ROWS = [
    # date, type, category, amount, note
    ("2026-08-01", "received", "Allowance", 3000, "Monthly pocket money from parents"),
    ("2026-08-02", "spent", "Books & Stationery", 450, "Semester notebooks and pens"),
    ("2026-08-04", "spent", "Food", 120, "Canteen lunch with friends"),
    ("2026-08-07", "spent", "Transport", 200, "Bus pass top-up"),
    ("2026-08-10", "spent", "Mobile Recharge", 299, "Monthly data pack"),
    ("2026-08-12", "received", "Gift", 500, "Raksha Bandhan gift from aunt"),
    ("2026-08-15", "spent", "Entertainment", 250, "Movie ticket"),
    ("2026-08-19", "spent", "Food", 85.5, "Evening snacks"),
    ("2026-08-23", "spent", "Shopping", 699, "New T-shirt"),
    ("2026-08-27", "spent", "Food", 140, "Pizza share"),
    ("2026-09-01", "received", "Allowance", 3000, "Monthly pocket money from parents"),
    ("2026-09-03", "spent", "Transport", 200, "Bus pass top-up"),
    ("2026-09-05", "received", "Part-time Job", 1200, "Weekend tutoring - 2 sessions"),
    ("2026-09-08", "spent", "Food", 0.01, "Boundary test: smallest valid amount"),
    ("2026-09-09", "spent", "Mobile Recharge", 299, "Monthly data pack"),
    ("2026-09-12", "spent", "Books & Stationery", 380, "Python reference book"),
    ("2026-09-14", "spent", "Food", 160, "Cafe with study group"),
    ("2026-09-18", "spent", "Health", 220, "Pharmacy - cold medicine"),
    ("2026-09-21", "spent", "Entertainment", 400, "College fest pass"),
    ("2026-09-25", "spent", "Food", 95, "Juice and sandwich"),
    ("2026-09-28", "received", "Prize", 750, "2nd place in coding quiz"),
    ("2026-10-01", "received", "Allowance", 3000, "Monthly pocket money from parents"),
    ("2026-10-02", "spent", "Transport", 200, "Bus pass top-up"),
    ("2026-10-05", "spent", "Food", 130, "Canteen lunch"),
    ("2026-10-08", "spent", "Mobile Recharge", 299, "Monthly data pack"),
    ("2026-10-11", "spent", "Shopping", 2499, "Wireless earbuds (big purchase)"),
    ("2026-10-15", "spent", "Food", 180, "Birthday treat for roommate"),
    ("2026-10-19", "received", "Part-time Job", 800, "Weekend tutoring"),
    ("2026-10-21", "spent", "Entertainment", 350, "Bowling night"),
    ("2026-10-24", "spent", "Books & Stationery", 120, "Printouts for project"),
    ("2026-10-28", "spent", "Food", 75, "Tea and samosa"),
    ("2026-10-31", "spent", "Other", 300, "Diwali decorations"),
    ("2026-11-01", "received", "Allowance", 3000, "Monthly pocket money from parents"),
    ("2026-11-02", "received", "Gift", 1000, "Diwali gift from grandparents"),
    ("2026-11-03", "spent", "Transport", 200, "Bus pass top-up"),
    ("2026-11-05", "spent", "Mobile Recharge", 299, "Monthly data pack"),
    ("2026-11-07", "spent", "Food", 210, "Dinner out"),
    ("2026-11-10", "spent", "Shopping", 1299, "Hackathon hoodie and backpack"),
    ("2026-11-13", "spent", "Books & Stationery", 560, "Exam prep guides"),
    ("2026-11-16", "spent", "Entertainment", 199, "Streaming subscription"),
    ("2026-11-18", "received", "Refund", 150, "Returned faulty charger"),
    ("2026-11-20", "spent", "Food", 145, "Hackathon snacks"),
]

BAD_ROWS = [
    ("2026-11-21", "spent", "Food", "120", "Valid row - will be imported"),
    ("2026-11-21", "received", "Allowance", "abc", "Non-numeric amount"),
    ("2026-13-05", "spent", "Food", "50", "Impossible month"),
    ("2026-11-19", "spent", "Food", "-40", "Negative amount"),
    ("2026-11-19", "spent", "Pets", "100", "Unknown category"),
    ("", "spent", "Food", "60", "Missing date"),
    ("2026-11-19", "borrowed", "Other", "60", "Unknown type"),
    ("2026-11-19", "spent", "Transport", "250000", "Amount above the limit"),
    ("2099-01-01", "spent", "Food", "30", "Date in the future"),
    ("2026-11-21", "received", "Gift", "200.00", "Valid row - will be imported"),
]


def main():
    DATA.mkdir(exist_ok=True)
    records = [
        {"id": f"s{i:03d}", "date": d, "type": t, "category": c, "amount": float(a), "note": n}
        for i, (d, t, c, a, n) in enumerate(ROWS, start=1)
    ]
    fields = ["id", "date", "type", "category", "amount", "note"]
    with open(DATA / "sample_transactions.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(records)
    (DATA / "sample_transactions.json").write_text(
        json.dumps({"version": 1, "transactions": records}, indent=2), encoding="utf-8"
    )
    with open(DATA / "sample_import_with_errors.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "type", "category", "amount", "note"])
        w.writerows(BAD_ROWS)
    print(f"Wrote {len(records)} sample entries and {len(BAD_ROWS)} import-test rows to {DATA}")


if __name__ == "__main__":
    main()
