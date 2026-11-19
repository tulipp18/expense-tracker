"""Data layer for the Expense Tracker.

By default records live in a local SQLite file next to this module. When the
EXPENSES_DB_URL environment variable is set (configured as a Streamlit secret
on the hosted app), a PostgreSQL database is used instead so records persist
across app restarts and redeploys.
"""
from contextlib import contextmanager
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
import os
from pathlib import Path
import sqlite3

DEFAULT_DB = Path(__file__).with_name('expenses.db')
DSN = os.environ.get('EXPENSES_DB_URL') or None
CATEGORIES = ('Food', 'Transport', 'Study', 'Shopping', 'Other')


def _ph():
    return '%s' if DSN else '?'


@contextmanager
def connect(path=DEFAULT_DB):
    if DSN:
        from psycopg import connect as pg_connect
        from psycopg.rows import dict_row
        db = pg_connect(DSN, row_factory=dict_row)
    else:
        db = sqlite3.connect(path)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _run(db, sql, args=()):
    cur = db.cursor()
    cur.execute(sql, args)
    return cur


def init_db(path=DEFAULT_DB):
    with connect(path) as db:
        if DSN:
            _run(db, 'CREATE TABLE IF NOT EXISTS categories('
                     'id SERIAL PRIMARY KEY, name TEXT NOT NULL UNIQUE)')
            _run(db, 'CREATE TABLE IF NOT EXISTS expenses('
                     'id SERIAL PRIMARY KEY, spent_on TEXT NOT NULL, '
                     'category_id INTEGER NOT NULL REFERENCES categories(id), '
                     'amount_paise INTEGER NOT NULL CHECK(amount_paise>0), '
                     'note TEXT NOT NULL CHECK(length(note)<=120))')
            for name in CATEGORIES:
                _run(db, 'INSERT INTO categories(name) VALUES(%s) '
                         'ON CONFLICT (name) DO NOTHING', (name,))
        else:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS categories(
              id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE);
            CREATE TABLE IF NOT EXISTS expenses(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              spent_on TEXT NOT NULL, category_id INTEGER NOT NULL,
              amount_paise INTEGER NOT NULL CHECK(amount_paise>0),
              note TEXT NOT NULL CHECK(length(note)<=120),
              FOREIGN KEY(category_id) REFERENCES categories(id));
            ''')
            db.executemany('INSERT OR IGNORE INTO categories(name) VALUES(?)',
                           [(x,) for x in CATEGORIES])


def _today():
    """'Today' follows Asia/Kolkata (UTC+5:30), matching the app's audience,
    so an expense dated today in India is never rejected as 'future' when the
    server's clock is still on the previous (UTC) day."""
    from datetime import datetime
    return (datetime.utcnow() + timedelta(hours=5, minutes=30)).date()


def validate(spent_on, category, amount, note):
    try:
        parsed = date.fromisoformat(str(spent_on))
    except (ValueError, TypeError):
        raise ValueError('Enter a valid date.')
    if parsed > _today():
        raise ValueError('Expense date cannot be in the future.')
    if category not in CATEGORIES:
        raise ValueError('Choose a listed category.')
    try:
        value = Decimal(str(amount))
    except InvalidOperation:
        raise ValueError('Enter a valid amount.')
    if not value.is_finite() or value <= 0 or value > Decimal('1000000'):
        raise ValueError('Amount must be between INR 0.01 and INR 1,000,000.')
    if value != value.quantize(Decimal('.01')):
        raise ValueError('Use no more than two decimal places.')
    if len(note.strip()) > 120:
        raise ValueError('Note must be at most 120 characters.')
    return parsed.isoformat(), category, int(value*100), note.strip()


def save_expense(spent_on, category, amount, note='', expense_id=None, path=DEFAULT_DB):
    day, category, paise, note = validate(spent_on, category, amount, note)
    ph = _ph()
    with connect(path) as db:
        cid = _run(db, f'SELECT id FROM categories WHERE name={ph}', (category,)).fetchone()['id']
        if expense_id is None:
            if DSN:
                return _run(db, 'INSERT INTO expenses(spent_on,category_id,amount_paise,note) '
                                'VALUES(%s,%s,%s,%s) RETURNING id', (day, cid, paise, note)).fetchone()['id']
            return _run(db, 'INSERT INTO expenses(spent_on,category_id,amount_paise,note) '
                            'VALUES(?,?,?,?)', (day, cid, paise, note)).lastrowid
        cur = _run(db, f'UPDATE expenses SET spent_on={ph},category_id={ph},amount_paise={ph},'
                       f'note={ph} WHERE id={ph}', (day, cid, paise, note, expense_id))
        if cur.rowcount != 1:
            raise ValueError('Expense not found.')
        return expense_id


def list_expenses(start, end, category='All', path=DEFAULT_DB):
    if start > end:
        raise ValueError('Start date must be on or before end date.')
    ph = _ph()
    query = f'''SELECT e.id,e.spent_on,c.name AS category,e.amount_paise,e.note
               FROM expenses e JOIN categories c ON c.id=e.category_id
               WHERE e.spent_on BETWEEN {ph} AND {ph}'''
    args = [str(start), str(end)]
    if category != 'All':
        query += f' AND c.name={ph}'
        args.append(category)
    query += ' ORDER BY e.spent_on DESC,e.id DESC'
    with connect(path) as db:
        return [dict(r) for r in _run(db, query, args).fetchall()]


def delete_expense(expense_id, path=DEFAULT_DB):
    ph = _ph()
    with connect(path) as db:
        if _run(db, f'DELETE FROM expenses WHERE id={ph}', (expense_id,)).rowcount != 1:
            raise ValueError('Expense not found.')
