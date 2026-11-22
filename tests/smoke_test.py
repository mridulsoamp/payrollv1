"""Small dependency-free smoke test; run from project root with `python tests/smoke_test.py`."""
import os, tempfile
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['DATABASE_PATH'] = str(Path(tempfile.mkdtemp()) / 'test.db')
from app import db
from app.payroll import calculate

db.init()
rows = [dict(employee_code='T001', employee_name='Test Person', state='Karnataka', basic=30000, hra=10000, allowances=2000, unpaid_leave_days=1, tds=100, other_deductions=0)]
count, errors = db.save_employees(rows, 'test')
assert count == 1 and not errors
rules = db.active_rules('2026-07')
a = calculate(db.employees()[0], rules, '2026-07')
b = calculate(db.employees()[0], rules, '2026-07')
assert a == b, 'Same inputs/rules must produce identical results'
assert a['lop_divisor'] == 31
assert len(a['breakdown']) >= 7
rid = db.create_run('2026-07', {'rules': rules}, [a])
assert db.set_status(rid, 'pending_approval', 'maker')['status'] == 'pending_approval'
assert db.get_run(rid)['status'] == 'pending_approval'  # persisted in SQLite
assert db.set_status(rid, 'approved', 'checker')['status'] == 'approved'
print('PASS: deterministic calculation, reason breakdown, persisted maker/checker workflow')
