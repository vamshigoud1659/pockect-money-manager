
from __future__ import annotations
import subprocess, sys
if "streamlit" not in sys.modules:
    subprocess.run(["py", "-u", "-m", "streamlit", "run", __file__, "--server.headless", "false"])
    sys.exit()

from datetime import date

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from pmm import APP_NAME, VERSION
from pmm.charts import balance_chart, category_chart, monthly_chart, save_all_charts
from pmm.logic import add_transaction, check_warnings, delete_transaction, search, summarize
from pmm.models import CATEGORIES, TYPE_RECEIVED, TYPE_SPENT, fmt_money
from pmm.reports import csv_report, export_all, markdown_report, text_audit_log
from pmm.storage import (
    EXPORT_DIR,
    load_sample,
    load_settings,
    load_transactions,
    merge,
    parse_csv,
    save_settings,
    save_transactions,
    to_csv,
)
from pmm.validation import ValidationError, validate_amount

st.set_page_config(page_title=APP_NAME, page_icon="💰", layout="wide")

st.markdown(
    """
    <style>
      .block-container {padding-top: 2rem; max-width: 1200px;}
      .pmm-hero {background: radial-gradient(ellipse at 85% 10%, rgba(232,176,48,.35), transparent 55%), linear-gradient(140deg, #123524, #2a6e4a); box-shadow: 0 12px 30px -12px rgba(232,176,48,.45);
                 color: #fbf8f1; padding: 1.4rem 1.8rem; border-radius: 18px; margin-bottom: 1.2rem;}
      .pmm-hero h1 {margin: 0; font-size: 2rem; color: #fbf8f1;}
      .pmm-hero p {margin: .25rem 0 0; opacity: .85;}
      .pmm-badge {display:inline-block; padding:.2rem .75rem; border-radius:999px; font-weight:700; font-size:.85rem;}
      .pmm-Healthy {background:#1f4d36; color:#8fe3b0;}
      .pmm-Watch {background:#4a3a12; color:#f5c95a;}
      .pmm-Overspending {background:#4d1f1a; color:#f4a093;}
      .pmm-No {background:#2a332e; color:#b8c4bc;}
      div[data-testid="stMetric"] {background:#16241d; border:1px solid #2a3d32; box-shadow: 0 8px 24px -14px rgba(0,0,0,.6); border-radius:14px; padding:.8rem 1rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


# ----------------------------------------------------------------- state
def load_state():
    if "transactions" not in st.session_state:
        txs, notices = load_transactions()
        st.session_state.transactions = txs
        st.session_state.notices = notices
    if "settings" not in st.session_state:
        st.session_state.settings = load_settings()


def persist():
    save_transactions(st.session_state.transactions)


def to_frame(rows) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ID": t.id,
                "Date": t.date,
                "Type": t.type.title(),
                "Category": t.category,
                "Amount (₹)": t.amount if t.type == TYPE_RECEIVED else -t.amount,
                "Note": t.note,
            }
            for t in rows
        ]
    )


def show_fig(fig):
    st.pyplot(fig, width="stretch")
    plt.close(fig)


def show_warnings(txs, settings):
    warns = check_warnings(txs, settings["monthly_budget"], settings["low_balance_threshold"])
    for w in warns:
        (st.error if w.level == "critical" else st.warning)(w.message, icon="⚠️")
    if not warns and txs:
        st.success("No warnings - your pocket money is in good shape.", icon="✅")


load_state()
txs = st.session_state.transactions
settings = st.session_state.settings

# ----------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown(f"## 💰 {APP_NAME}")
    st.caption(f"v{VERSION} · data saved to data/transactions.json")
    page = st.radio(
        "Go to",
        ["🏠 Dashboard", "➕ Add entry", "🔎 Records & search", "📊 Reports & charts", "📥 Bulk import", "⚙️ Settings"],
        label_visibility="collapsed",
    )
    st.divider()
    sidebar_stats = st.empty()  # filled at the end so it reflects changes made on this run

for n in st.session_state.pop("notices", []):
    st.info(n, icon="ℹ️")

st.markdown(
    f"""<div class="pmm-hero"><h1>{page.split(' ', 1)[1]}</h1>
    <p>Hi {settings['student_name']} - log pocket money received and spent, and see where it goes.</p></div>""",
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------- pages
if page.endswith("Dashboard"):
    s = summarize(txs)
    if not txs:
        st.info("No entries yet. Add your first one, or load the sample data to try the demo.")
        if st.button("Load sample data (42 entries)", type="primary"):
            st.session_state.transactions, _ = merge(txs, load_sample())
            persist()
            st.rerun()
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Balance", fmt_money(s.balance))
        c2.metric("Total received", fmt_money(s.total_received))
        c3.metric("Total spent", fmt_money(s.total_spent))
        c4.metric("Savings rate", f"{s.savings_rate}%")
        badge = s.status.split()[0]
        st.markdown(
            f'Status: <span class="pmm-badge pmm-{badge}">{s.status}</span> &nbsp; '
            f"Spending trend vs last month: **{s.spending_trend}** &nbsp; Top category: **{s.top_category or '-'}**",
            unsafe_allow_html=True,
        )
        st.write("")
        show_warnings(txs, settings)
        left, right = st.columns([3, 2])
        with left:
            show_fig(monthly_chart(txs))
        with right:
            show_fig(category_chart(txs))
        st.subheader("Recent entries")
        st.dataframe(to_frame(list(reversed(txs))[:8]), hide_index=True, width="stretch")

elif page.endswith("Add entry"):
    st.caption("Try typing a wrong amount like 'abc', '-50' or '12.345' to see validation in action.")
    tx_type = st.radio("What happened?", ["Money received", "Money spent"], horizontal=True)
    t = TYPE_RECEIVED if tx_type == "Money received" else TYPE_SPENT
    with st.form("add", clear_on_submit=True):
        col1, col2 = st.columns(2)
        when = col1.date_input("Date", value=date.today(), max_value=date.today(), format="YYYY-MM-DD")
        category = col2.selectbox("Category", CATEGORIES[t])
        amount = col1.text_input("Amount (₹)", placeholder="e.g. 250 or 99.50")
        note = col2.text_input("Note (optional)", max_chars=100, placeholder="e.g. Canteen lunch")
        submitted = st.form_submit_button("Save entry", type="primary")
    if submitted:
        try:
            tx = add_transaction(txs, {"date": when, "type": t, "category": category, "amount": amount, "note": note})
            persist()
            st.success(f"Saved: {tx.type} {fmt_money(tx.amount)} for {tx.category} on {tx.date}.", icon="✅")
            st.toast("Entry saved")
        except ValidationError as exc:
            st.error(str(exc), icon="✋")

elif page.endswith("Records & search"):
    f1, f2, f3 = st.columns([2, 1, 1])
    kw = f1.text_input("Keyword", placeholder="Search notes and categories")
    tsel = f2.selectbox("Type", ["All", "Received", "Spent"])
    tval = None if tsel == "All" else tsel.lower()
    cats = CATEGORIES[tval] if tval else sorted(set(CATEGORIES[TYPE_RECEIVED] + CATEGORIES[TYPE_SPENT]))
    csel = f3.selectbox("Category", ["All"] + cats)
    d1, d2 = st.columns(2)
    start = d1.date_input("From", value=None, format="YYYY-MM-DD")
    end = d2.date_input("To", value=None, format="YYYY-MM-DD")
    results = search(txs, keyword=kw, tx_type=tval, category=None if csel == "All" else csel, start=start, end=end)
    st.markdown(f"**{len(results)}** record(s) · net {fmt_money(sum(r.signed_amount for r in results))}")
    if results:
        st.dataframe(to_frame(results), hide_index=True, width="stretch", height=420 if len(results) > 10 else "auto")
        st.download_button("Download these records (CSV)", to_csv(results), "records.csv", "text/csv")
        with st.expander("Delete a record"):
            options = {f"{r.date} · {r.category} · {fmt_money(r.signed_amount)} · {r.id}": r.id for r in results}
            label = st.selectbox("Record", list(options))
            if st.button("Delete record", type="secondary"):
                delete_transaction(txs, options[label])
                persist()
                st.rerun()

elif page.endswith("Reports & charts"):
    if not txs:
        st.info("Add some entries first.")
    else:
        s = summarize(txs)
        st.subheader("Executive summary")
        summary_rows = {
            "Entries": str(s.count),
            "Total received": fmt_money(s.total_received),
            "Total spent": fmt_money(s.total_spent),
            "Balance": fmt_money(s.balance),
            "Savings rate": f"{s.savings_rate}%",
            "Average received": fmt_money(s.avg_received),
            "Average expense": fmt_money(s.avg_spent),
            "Largest expense": f"{fmt_money(s.largest_expense.amount)} - {s.largest_expense.category}" if s.largest_expense else "-",
            "Top spending category": s.top_category or "-",
            "Spending trend": s.spending_trend,
            "Status": s.status,
        }
        a, b = st.columns(2)
        a.dataframe(pd.DataFrame(summary_rows.items(), columns=["Metric", "Value"]), hide_index=True, width="stretch", height=425)
        b.dataframe(
            pd.DataFrame(s.monthly).rename(columns=str.title), hide_index=True, width="stretch"
        )
        show_fig(balance_chart(txs))
        l, r = st.columns(2)
        with l:
            show_fig(monthly_chart(txs))
        with r:
            show_fig(category_chart(txs))
        st.subheader("Export")
        e1, e2, e3, e4 = st.columns(4)
        e1.download_button("Markdown report", markdown_report(txs, settings), "summary_report.md", "text/markdown")
        e2.download_button("Text audit log", text_audit_log(txs), "audit_log.txt", "text/plain")
        e3.download_button("CSV summary", csv_report(txs), "summary_report.csv", "text/csv")
        if e4.button("Save all to exports/ folder"):
            files = export_all(txs, settings, EXPORT_DIR) + save_all_charts(txs, EXPORT_DIR)
            st.success("Saved: " + ", ".join(p.name for p in files))
        with st.expander("Preview Markdown report"):
            st.markdown(markdown_report(txs, settings))

elif page.endswith("Bulk import"):
    st.write("Upload a CSV with columns **date, type, category, amount, note**. Every row is checked; bad rows are listed with the reason.")
    up = st.file_uploader("CSV file", type=["csv"])
    use_demo = st.button("Or try the demo file with deliberate mistakes")
    text = None
    if up is not None:
        try:
            text = up.getvalue().decode("utf-8")
        except UnicodeDecodeError:
            st.error("That file isn't valid UTF-8 text.")
    elif use_demo:
        text = open("data/sample_import_with_errors.csv", encoding="utf-8").read()
    if text is not None:
        valid, errors = parse_csv(text)
        st.session_state.transactions, added = merge(txs, valid)
        txs = st.session_state.transactions
        persist()
        skipped = len(valid) - added
        st.success(f"Imported {added} valid record(s)." + (f" {skipped} already existed and were skipped." if skipped else ""), icon="✅")
        if errors:
            st.error(f"{len(errors)} row(s) were rejected:")
            st.dataframe(pd.DataFrame(errors, columns=["Row", "Problem"]), hide_index=True, width="stretch")

elif page.endswith("Settings"):
    with st.form("settings"):
        name = st.text_input("Your name", value=settings["student_name"], max_chars=40)
        budget = st.text_input("Monthly spending budget (₹)", value=str(settings["monthly_budget"]))
        low = st.text_input("Warn me when balance drops below (₹)", value=str(settings["low_balance_threshold"]))
        if st.form_submit_button("Save settings", type="primary"):
            try:
                settings.update(
                    student_name=name.strip() or "Student",
                    monthly_budget=validate_amount(budget),
                    low_balance_threshold=validate_amount(low),
                )
                save_settings(settings)
                st.success("Settings saved.")
            except ValidationError as exc:
                st.error(str(exc))
    st.subheader("Data")
    c1, c2 = st.columns(2)
    if c1.button("Load sample data (42 entries)"):
        st.session_state.transactions, added = merge(txs, load_sample())
        txs = st.session_state.transactions
        persist()
        st.success(f"Added {added} sample entries.")
    confirm = c2.checkbox("Yes, I want to delete all my entries")
    if c2.button("Clear all data", disabled=not confirm):
        st.session_state.transactions = []
        persist()
        st.rerun()

# ----------------------------------------------------------------- sidebar stats (always up to date)
with sidebar_stats.container():
    s_side = summarize(st.session_state.transactions)
    st.metric("Current balance", fmt_money(s_side.balance))
    st.caption(f"{s_side.count} entries recorded")
