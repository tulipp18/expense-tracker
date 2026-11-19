import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from storage import *

class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/'test.db'
        init_db(self.path)
        self.today=date.today().isoformat()
    def tearDown(self): self.tmp.cleanup()
    def add(self,**kw):
        args=dict(spent_on=self.today,category='Food',amount='12.50',note='Lunch',path=self.path)
        args.update(kw)
        return save_expense(**args)
    def rows(self,category='All'):
        return list_expenses('0001-01-01','9999-12-31',category,self.path)
    def test_create_persists_exact_paise(self):
        self.add(); self.assertEqual(self.rows()[0]['amount_paise'],1250)
    def test_update(self):
        i=self.add();self.add(expense_id=i,amount='25.75',category='Study');self.assertEqual(self.rows()[0]['amount_paise'],2575)
    def test_delete(self):
        i=self.add();delete_expense(i,self.path);self.assertEqual(self.rows(),[])
    def test_category_filter(self):
        self.add();self.add(category='Study');self.assertEqual(len(self.rows('Study')),1)
    def test_date_filter(self):
        self.add();self.assertEqual(list_expenses('2000-01-01','2000-01-02',path=self.path),[])
    def test_zero_rejected(self):
        with self.assertRaises(ValueError): self.add(amount='0')
    def test_negative_rejected(self):
        with self.assertRaises(ValueError): self.add(amount='-1')
    def test_extra_precision_rejected(self):
        with self.assertRaises(ValueError): self.add(amount='1.001')
    def test_invalid_amount_rejected(self):
        with self.assertRaises(ValueError): self.add(amount='abc')
    def test_nan_rejected(self):
        with self.assertRaises(ValueError): self.add(amount='NaN')
    def test_future_date_rejected(self):
        with self.assertRaises(ValueError): self.add(spent_on=(date.today()+timedelta(days=1)).isoformat())
    def test_invalid_date_rejected(self):
        with self.assertRaises(ValueError): self.add(spent_on='2026-02-30')
    def test_invalid_category_rejected(self):
        with self.assertRaises(ValueError): self.add(category='Unknown')
    def test_long_note_rejected(self):
        with self.assertRaises(ValueError): self.add(note='x'*121)
    def test_parameterized_note(self):
        self.add(note="'); DROP TABLE expenses; --");self.add();self.assertEqual(len(self.rows()),2)
    def test_missing_update_rejected(self):
        with self.assertRaises(ValueError):self.add(expense_id=999)
    def test_missing_delete_rejected(self):
        with self.assertRaises(ValueError):delete_expense(999,self.path)
    def test_invalid_filter_range(self):
        with self.assertRaises(ValueError):list_expenses('2026-02-02','2026-01-01',path=self.path)
    def test_max_amount_rejected(self):
        with self.assertRaises(ValueError):self.add(amount='1000000.01')
    def test_idempotent_setup(self):
        init_db(self.path)
        with connect(self.path) as db:self.assertEqual(db.execute('SELECT count(*) FROM categories').fetchone()[0],5)
if __name__=='__main__':unittest.main(verbosity=2)
