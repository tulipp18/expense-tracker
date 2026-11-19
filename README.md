# Expense Tracker
Software Engineering mini-project for Tulip Gupta.
Streamlit app with validated INR expense records. Hosted runs use PostgreSQL
(persistent storage); local runs use a SQLite file. Records are private to
invited signed-in viewers on the hosted app.

## Live app
Deployed on Streamlit Community Cloud. Database: PostgreSQL (Supabase free
tier), configured through Streamlit secrets; no credentials in this repo.

## Run locally
Tested with Python 3.10.12. Python 3.10+ recommended.

Windows:
```
py -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python seed_demo.py
python -m streamlit run app.py
```

macOS / Linux:
```
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python seed_demo.py
python -m streamlit run app.py
```
Open the local address printed by Streamlit (normally http://localhost:8501).
Stop with Ctrl+C. The first dependency installation needs internet access.

## Use
- Add: enter a date (not in the future), category, positive INR amount
  with at most two decimal places, and an optional note.
- Dashboard: sidebar date/category filters drive totals, chart, table and CSV.
- Manage: edit uses a record selector; deletion requires the confirmation
  checkbox. The manage list always shows every saved record.
- CSV export covers filtered records only. Notes that might be spreadsheet
  formulas are prefixed with an apostrophe in the export.

## Data and storage
- Hosted: records persist in PostgreSQL across app restarts and redeploys.
  The database connection string lives in Streamlit secrets (EXPENSES_DB_URL),
  never in this repository.
- Local: the app creates expenses.db next to storage.py. seed_demo.py adds six
  fictional sample expenses to an empty local database only.
- Back up a local expenses.db while the app is stopped. To reset locally, stop
  the app, back up then remove expenses.db, then restart.

## Verify
```
python -m unittest -v
```
20 data-layer tests use temporary SQLite databases and do not alter
expenses.db. Test evidence in test-results.txt and ui-test-results.txt.

## Files
- app.py: Streamlit UI, chart, CSV export, forms.
- storage.py: validation, schema, parameterized CRUD (SQLite and PostgreSQL).
- seed_demo.py: optional fictional demo data for a local database.
- test_storage.py: repeatable unit tests.
- screenshots/, diagrams/: original project documentation.
