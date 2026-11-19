"""Populate fictional demo data only if there are no expenses."""
from datetime import date
from storage import *
init_db()
if not list_expenses('0001-01-01','9999-12-31'):
    today=date.today()
    for day,cat,amount,note in [(2,'Food','180.00','Campus lunch'),(4,'Transport','80.00','Metro recharge'),(6,'Study','450.00','Reference book'),(8,'Food','240.50','Groceries'),(10,'Shopping','650.00','Desk supplies'),(12,'Other','199.00','Printing and binding')]:
        save_expense(today.replace(day=min(day,today.day)),cat,amount,note)
    print('Created 6 fictional demo records. Total: INR 1799.50')
else:
    print('Database already contains records; no demo data added.')
