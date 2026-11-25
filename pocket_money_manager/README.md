# 💰 Pocket Money Manager

**DataSpark Challenge · Project #14 · Finance & Personal Management**

A beginner-friendly Python application to log pocket money **received** and **spent**,
with balance summaries, strict input validation, local JSON/CSV storage, search,
warnings, reports and Matplotlib charts.

It has **two interfaces that share the same data**:

| Interface | Command | Use it for |
|---|---|---|
| 🌐 **Streamlit web app** (demo UI) | `streamlit run app.py` | The class / hackathon demo |
| 🖥️ Terminal menu | `python main.py` | The menu-driven console version from the brief |

---

## 1. Setup (one time)

Needs **Python 3.10 or newer**.

```bash
cd pocket_money_manager
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

## 2. Run

```bash
streamlit run app.py      # opens http://localhost:8501 in your browser
python main.py            # terminal version
python -m unittest -v     # run the 17 automated tests
python seed_data.py       # (optional) regenerate the sample datasets
```

On the first launch the app starts empty. Click **Load sample data (42 entries)**
(or choose menu option **10** in the terminal) to fill it with realistic records.

---

## 3. Features vs. the brief

| Requirement | Where |
|---|---|
| Interactive interface (menu-driven) | `main.py` (terminal), `app.py` (Streamlit GUI) |
| Defensive input validation | `pmm/validation.py` - amount, date, type, category, note checks |
| Core business logic | `pmm/logic.py` - balance, running balance, monthly & category totals |
| Local data persistence (JSON + CSV) | `pmm/storage.py` - `data/transactions.json`, atomic saves |
| Record query & search | keyword, type, category and date-range filters |
| Executive summary | totals, averages, savings rate, largest expense, trend, status |
| Visual data plotting (Matplotlib) | `pmm/charts.py` - monthly bars, category donut, balance line |
| ⭐ Multi-format export | Markdown report, plain-text audit log, CSV summary (`exports/`) |
| ⭐ Threshold warnings | low balance, budget nearly used / exceeded, unusually large expenses |
| ⭐ GUI enhancement | Streamlit web interface |
| ⭐ Bulk CSV import | row-by-row validation with an error log |

### Validation rules
- **Amount**: required, numeric, more than 0, at most 100,000, max 2 decimals (`abc`, `-50`, `12.345` are rejected)
- **Date**: `YYYY-MM-DD`, not in the future, not before 2000-01-01 (blank = today in the terminal)
- **Type**: `received` or `spent`
- **Category**: must belong to the chosen type (e.g. *Allowance* can't be "spent")
- **Note**: optional, up to 100 characters

### Status levels
- **Healthy** - you saved 20% or more of what you received
- **Watch** - you saved less than 20%
- **Overspending** - you spent more than you received

### Robustness
- Missing data file → a fresh one is created automatically
- Corrupted JSON → backed up as `transactions.corrupt-<time>.json`, a clean file is created
- Invalid records inside the file → skipped with a notice, the rest still load
- Matplotlib missing → the terminal app still works, charts are skipped with a message
- Importing the same CSV twice doesn't create duplicates

---

## 4. Project structure

```
pocket_money_manager/
├── app.py                 # Streamlit web interface
├── main.py                # Terminal (console) interface
├── seed_data.py           # Generates the sample datasets
├── requirements.txt
├── .streamlit/config.toml # Web app colours/theme
├── pmm/                   # Core package shared by both interfaces
│   ├── models.py          # Transaction dataclass, categories
│   ├── validation.py      # Input validation
│   ├── storage.py         # JSON/CSV load, save, import
│   ├── logic.py           # Calculations, search, warnings
│   ├── reports.py         # Markdown / TXT / CSV export
│   └── charts.py          # Matplotlib charts
├── data/
│   ├── sample_transactions.csv / .json   # 42 realistic entries (incl. boundary value 0.01)
│   └── sample_import_with_errors.csv     # 10 rows, 8 with deliberate mistakes
├── exports/               # Reports and charts are saved here
└── tests/test_pmm.py      # 17 unit tests
```

---

## 5. Demo script (≈ 3 minutes)

1. `streamlit run app.py` → show the branded **Dashboard**, click **Load sample data**.
2. Walk through the balance cards, status badge, warnings and charts.
3. **Add entry** → type `abc` as the amount → red validation message. Then `-50` → rejected.
   Enter `150` → saved, balance in the sidebar updates.
4. **Records & search** → search `tutoring`, filter by type / dates, download as CSV.
5. **Reports & charts** → executive summary table, balance chart, download the
   Markdown report / audit log / CSV, or *Save all to exports/ folder*.
6. **Bulk import** → *Try the demo file with deliberate mistakes* → 2 rows imported,
   8 rejected with the reason for each row.
7. **Prove persistence**: stop the app (Ctrl+C in the terminal), run `streamlit run app.py`
   again (or `python main.py`) - all entries are still there.
