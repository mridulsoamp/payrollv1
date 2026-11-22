import os, sqlite3, json
from pathlib import Path
DB=Path(os.getenv('DATABASE_PATH','./data/payroll_v2.db'))
DB.parent.mkdir(parents=True,exist_ok=True)
def conn():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
def init():
 with conn() as c:
  c.executescript("""
  CREATE TABLE IF NOT EXISTS employees(code TEXT PRIMARY KEY, name TEXT, state TEXT, basic REAL, hra REAL, allowances REAL, unpaid_leave_days REAL, tds REAL, other_deductions REAL, source TEXT);
  CREATE TABLE IF NOT EXISTS rules(id INTEGER PRIMARY KEY AUTOINCREMENT, company TEXT, key TEXT, value TEXT, effective_from TEXT, note TEXT);
  CREATE TABLE IF NOT EXISTS runs(id INTEGER PRIMARY KEY AUTOINCREMENT, month TEXT, status TEXT, snapshot TEXT, results TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, submitted_by TEXT, approved_by TEXT);
  CREATE TABLE IF NOT EXISTS proposals(id INTEGER PRIMARY KEY AUTOINCREMENT, instruction TEXT, proposal TEXT, status TEXT DEFAULT 'pending', created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  """)
  defaults=[('DEMO','lop_basis','calendar_days','2020-01','Days in the month'),('DEMO','pf_basis','capped_basic','2020-01','PF on first ₹15,000 of basic'),('INDIA','pf_rate','0.12','2020-01','Demo employee PF rate; configure against applicable rules'),('INDIA','esi_rate','0.0075','2020-01','Demo employee ESI rate'),('INDIA','esi_ceiling','21000','2020-01','Demo ESI gross wage ceiling'),('INDIA','pt_karnataka_threshold','15000','2020-01','Illustrative demo threshold'),('INDIA','pt_karnataka_amount','200','2020-01','Illustrative demo PT amount')]
  for company,key,value,effective,note in defaults:
   c.execute('INSERT INTO rules(company,key,value,effective_from,note) SELECT ?,?,?,?,? WHERE NOT EXISTS (SELECT 1 FROM rules WHERE company=? AND key=? AND effective_from=?)',(company,key,value,effective,note,company,key,effective))
def active_rules(month):
 with conn() as c:
  rows=c.execute('SELECT company,key,value,effective_from,note FROM rules WHERE effective_from<=? ORDER BY effective_from',(month+'-01',)).fetchall()
 out={}
 for r in rows: out[r['key']]=r['value']
 return out
def employees():
 with conn() as c: return [dict(r) for r in c.execute('SELECT * FROM employees ORDER BY code')]
def save_employees(rows,source):
 saved=0; errors=[]
 with conn() as c:
  for i,r in enumerate(rows, start=1):
   try:
    code=str(r.get('employee_code',r.get('code',''))).strip(); name=str(r.get('employee_name',r.get('name',''))).strip()
    if not code or not name: raise ValueError('employee_code and employee_name are required')
    def num(k): return float(r.get(k) or 0)
    c.execute('INSERT INTO employees(code,name,state,basic,hra,allowances,unpaid_leave_days,tds,other_deductions,source) VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(code) DO UPDATE SET name=excluded.name,state=excluded.state,basic=excluded.basic,hra=excluded.hra,allowances=excluded.allowances,unpaid_leave_days=excluded.unpaid_leave_days,tds=excluded.tds,other_deductions=excluded.other_deductions,source=excluded.source',(code,name,str(r.get('state','Karnataka')),num('basic'),num('hra'),num('allowances'),num('unpaid_leave_days'),num('tax_deduction') if r.get('tax_deduction') is not None else num('tds'),num('other_deductions'),source)); saved+=1
   except Exception as e: errors.append(f'Row {i}: {e}')
 return saved,errors
def add_rule(key,value,effective_from,note='User-approved company/statutory rule'):
 with conn() as c: c.execute('INSERT INTO rules(company,key,value,effective_from,note) VALUES(?,?,?,?,?)',('DEMO',key,str(value),effective_from,note))
def list_rules():
 with conn() as c: return [dict(r) for r in c.execute('SELECT * FROM rules ORDER BY effective_from DESC,id DESC')]
def save_proposal(instruction,proposal):
 with conn() as c:
  cur=c.execute('INSERT INTO proposals(instruction,proposal) VALUES(?,?)',(instruction,json.dumps(proposal))); return cur.lastrowid
def approve_proposal(pid):
 with conn() as c:
  row=c.execute('SELECT * FROM proposals WHERE id=?',(pid,)).fetchone()
  if not row: return None
  p=json.loads(row['proposal'])
  for key,val in p.get('rules',{}).items(): c.execute('INSERT INTO rules(company,key,value,effective_from,note) VALUES(?,?,?,?,?)',('DEMO',key,str(val),p['effective_from'],'Approved plain-English proposal'))
  if p.get('bonus'): c.execute('UPDATE employees SET allowances=allowances+? WHERE code=?',(p['bonus']['amount'],p['bonus']['employee_code']))
  c.execute("UPDATE proposals SET status='approved' WHERE id=?",(pid,)); return dict(row)
def create_run(month,snapshot,results):
 with conn() as c:
  cur=c.execute('INSERT INTO runs(month,status,snapshot,results) VALUES(?,?,?,?)',(month,'calculated',json.dumps(snapshot),json.dumps(results))); return cur.lastrowid
def get_run(rid):
 with conn() as c:
  r=c.execute('SELECT * FROM runs WHERE id=?',(rid,)).fetchone()
  if not r:return None
  d=dict(r); d['snapshot']=json.loads(d['snapshot']); d['results']=json.loads(d['results']); return d
def set_status(rid,status,actor):
 with conn() as c:
  if status=='pending_approval': c.execute("UPDATE runs SET status=?,submitted_by=? WHERE id=? AND status='calculated'",(status,actor,rid))
  elif status=='approved': c.execute("UPDATE runs SET status=?,approved_by=? WHERE id=? AND status='pending_approval'",(status,actor,rid))
  else: return None
 return get_run(rid)
def all_runs():
 with conn() as c: return [dict(r) for r in c.execute('SELECT id,month,status,created_at,submitted_by,approved_by FROM runs ORDER BY id DESC')]
