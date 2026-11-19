"""Expense Tracker - Streamlit app.

Run locally:  python -m streamlit run app.py
Hosted runs use a PostgreSQL database configured through Streamlit secrets
(EXPENSES_DB_URL) and refuse to start without it. Local development uses a
SQLite file next to storage.py only when EXPENSES_ALLOW_SQLITE=1 is set.
"""
import os
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import csv
import io

import pandas as pd
import streamlit as st


# The app is built for use in India: default dates follow Asia/Kolkata (UTC+5:30),
# not the host server's timezone.
IST = timezone(timedelta(hours=5, minutes=30), name='IST')


def today_ist():
    return datetime.now(IST).date()


def _secret(key, default=None):
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default


if _secret('EXPENSES_DB_URL'):
    os.environ['EXPENSES_DB_URL'] = _secret('EXPENSES_DB_URL')

# Fail closed: the hosted app must never silently fall back to ephemeral
# SQLite storage. PostgreSQL is required unless SQLite is explicitly
# enabled for local development (EXPENSES_ALLOW_SQLITE=1).
_ALLOW_SQLITE = os.environ.get('EXPENSES_ALLOW_SQLITE', '').strip().lower() in ('1', 'true', 'yes')
if not os.environ.get('EXPENSES_DB_URL') and not _ALLOW_SQLITE:
    st.set_page_config(page_title='Expense Tracker', page_icon='\U0001F4B3')
    st.error(
        'This app is not connected to a database yet. '
        'The hosted deployment requires the EXPENSES_DB_URL secret (PostgreSQL). '
        'For local development only, set EXPENSES_ALLOW_SQLITE=1 to use a local SQLite file.'
    )
    st.stop()

from storage import CATEGORIES, init_db, list_expenses, save_expense, delete_expense, DSN

st.set_page_config(page_title='Expense Tracker', page_icon='💳', layout='wide')
init_db()

st.title('💳 Expense Tracker')
st.caption('Software Engineering mini-project | Python + Streamlit + '
           + ('PostgreSQL (persistent cloud storage)' if DSN else 'SQLite (local storage)'))

st.warning(
    'Shared public demo: anyone with this link can view, edit and delete the same '
    'saved records. Do not enter real financial or personal data here.',
    icon='\u26a0\ufe0f')


def rupees(paise):
    return f'₹{paise/100:,.2f}'


def safe_cell(s):
    # Prefix formula-leading text before export so spreadsheet apps do not execute it.
    return "'" + s if s.lstrip().startswith(('=', '+', '-', '@')) else s


with st.sidebar:
    st.header('🔎 Filters')
    start = st.date_input('From', today_ist().replace(day=1))
    end = st.date_input('To', today_ist())
    category = st.selectbox('Category', ['All', *CATEGORIES])
    st.caption('Totals, chart and CSV follow these filters. The manage list always shows every saved record.')
    st.divider()
    st.caption('Public demo: anyone with the link can see, change or delete these shared records.')

if start > end:
    st.error('Start date must be on or before end date.')
    st.stop()

rows = list_expenses(start, end, category)
total = sum(r['amount_paise'] for r in rows)

m1, m2, m3 = st.columns(3)
m1.metric('Selected spending', rupees(total))
m2.metric('Expenses', len(rows))
m3.metric('Categories used', len(set(r['category'] for r in rows)))

tab_dash, tab_add, tab_manage = st.tabs(['📊 Dashboard', '➕ Add expense', '🛠️ Manage records'])

with tab_dash:
    st.subheader('Spending by category')
    if rows:
        summary = {c: sum(r['amount_paise'] for r in rows if r['category'] == c) / 100 for c in CATEGORIES}
        chart = pd.DataFrame({'Amount (₹)': summary}).rename_axis('Category')
        st.bar_chart(chart, height=260, color='#255a81', horizontal=True)
        view = pd.DataFrame([{
            'ID': r['id'],
            'Date': date.fromisoformat(r['spent_on']),
            'Category': r['category'],
            'Amount (₹)': r['amount_paise'] / 100,
            'Note': r['note'],
        } for r in rows])
        st.subheader('Expense records')
        st.dataframe(
            view, hide_index=True, width='stretch',
            column_config={
                'ID': st.column_config.NumberColumn('ID', width='small'),
                'Date': st.column_config.DateColumn('Date', format='DD MMM YYYY'),
                'Amount (₹)': st.column_config.NumberColumn('Amount (₹)', format='₹ %.2f'),
            })
        buffer = io.StringIO()
        out = csv.writer(buffer)
        out.writerow(['ID', 'Date', 'Category', 'Amount (INR)', 'Note'])
        for r in rows:
            out.writerow([r['id'], r['spent_on'], r['category'], f"{r['amount_paise']/100:.2f}", safe_cell(r['note'])])
        st.download_button('⬇️ Download filtered CSV', buffer.getvalue(), 'expenses.csv', 'text/csv')
    else:
        st.info('No expenses match these filters. Add a record or widen the date range.')

with tab_add:
    st.subheader('Add an expense')
    with st.form('add', clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            day = st.date_input('Expense date', today_ist(), max_value=today_ist())
            cat = st.selectbox('Category', CATEGORIES, key='add-cat')
        with c2:
            amount = st.text_input('Amount (₹)', '', placeholder='e.g. 120.50')
            note = st.text_input('Note (optional)', max_chars=120)
        if st.form_submit_button('💾 Save expense', width='stretch'):
            try:
                save_expense(day, cat, amount, note)
                st.toast('Expense saved.', icon='✅')
                st.session_state['flash'] = 'Expense saved.'
                st.rerun()
            except ValueError as e:
                st.error(str(e))

with tab_manage:
    st.subheader('Edit or delete a record')
    all_rows = list_expenses('0001-01-01', '9999-12-31')
    if not all_rows:
        st.info('No saved records yet. Add your first expense from the Add tab.')
    else:
        mapping = {r['id']: r for r in all_rows}
        selected = st.selectbox(
            'Record', list(mapping),
            format_func=lambda i: f"#{i} | {mapping[i]['spent_on']} | {mapping[i]['category']} | {rupees(mapping[i]['amount_paise'])}")
        r = mapping[selected]
        with st.form(f'edit-{selected}'):
            c1, c2 = st.columns(2)
            with c1:
                d = st.date_input('New date', date.fromisoformat(r['spent_on']), max_value=today_ist())
                c = st.selectbox('New category', CATEGORIES, index=CATEGORIES.index(r['category']))
            with c2:
                v = st.text_input('New amount (₹)', str(Decimal(r['amount_paise']) / 100))
                n = st.text_input('New note', r['note'], max_chars=120)
            if st.form_submit_button('✏️ Update expense', width='stretch'):
                try:
                    save_expense(d, c, v, n, expense_id=selected)
                    st.toast('Expense updated.', icon='✏️')
                    st.session_state['flash'] = 'Expense updated.'
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))
        confirm = st.checkbox('I understand deletion is permanent', key=f'confirm-{selected}')
        if st.button('🗑️ Delete selected expense', disabled=not confirm):
            delete_expense(selected)
            st.toast('Expense deleted.', icon='🗑️')
            st.session_state['flash'] = 'Expense deleted.'
            st.rerun()

if 'flash' in st.session_state:
    st.success(st.session_state.pop('flash'))

st.caption('Currency: INR. Amounts are stored as integer paise; totals are derived from saved records.')
