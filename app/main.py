import csv,io,re,json
from pathlib import Path
from fastapi import FastAPI,Request,UploadFile,File,Form,HTTPException
from fastapi.responses import HTMLResponse,StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import pandas as pd
from . import db
from .payroll import calculate
from .horilla_reader import reader
app=FastAPI(title='Payroll AI Agent V2')
BASE=Path(__file__).resolve().parent
app.mount('/static',StaticFiles(directory=BASE/'static'),name='static')
templates=Jinja2Templates(directory=BASE/'templates')
@app.on_event('startup')
def startup(): db.init()
@app.get('/',response_class=HTMLResponse)
def home(request:Request): return templates.TemplateResponse('index.html',{'request':request,'employees':db.employees(),'rules':db.list_rules(),'runs':db.all_runs()})
@app.get('/api/state')
def state(): return {'employees':db.employees(),'rules':db.list_rules(),'runs':db.all_runs()}
@app.post('/api/demo')
def demo():
 p=BASE.parent/'sample_data'/'employees.csv'; df=pd.read_csv(p).fillna(0); n,errors=db.save_employees(df.to_dict('records'),'synthetic demo'); return {'saved':n,'errors':errors}
@app.post('/api/import')
async def import_file(file:UploadFile=File(...)):
 name=(file.filename or '').lower(); content=await file.read()
 try:
  df=pd.read_csv(io.BytesIO(content)) if name.endswith('.csv') else pd.read_excel(io.BytesIO(content)) if name.endswith(('.xlsx','.xls')) else None
  if df is None: raise ValueError('Upload CSV or XLSX.')
  df.columns=[str(c).strip().lower().replace(' ','_') for c in df.columns]
  aliases={'employee_id':'employee_code','code':'employee_code','name':'employee_name','basic_salary':'basic','hra_amount':'hra','other_allowance':'allowances','lop_days':'unpaid_leave_days','leave_without_pay':'unpaid_leave_days','tax_deduction':'tds'}
  df=df.rename(columns={k:v for k,v in aliases.items() if k in df.columns})
  missing={'employee_code','employee_name','basic'}-set(df.columns)
  if missing: raise ValueError('Missing columns: '+', '.join(sorted(missing)))
  n,errors=db.save_employees(df.fillna(0).to_dict('records'),'spreadsheet'); return {'saved':n,'errors':errors}
 except Exception as e: raise HTTPException(400,str(e))
@app.post('/api/horilla/open')
async def horilla_open(url:str=Form('http://localhost:8000')):
 try:return await reader.open(url)
 except Exception as e:raise HTTPException(400,str(e))
@app.post('/api/horilla/capture')
async def horilla_capture():
 try:
  data=await reader.capture(); (BASE.parent/'data').mkdir(exist_ok=True); (BASE.parent/'data'/'last_horilla_capture.json').write_text(json.dumps(data,indent=2)); return data
 except Exception as e:raise HTTPException(400,str(e))
@app.post('/api/horilla/close')
async def horilla_close(): await reader.close(); return {'message':'Browser closed'}
@app.post('/api/propose')
def propose(instruction:str=Form(...),effective_from:str=Form(...)):
 t=instruction.lower(); proposal={'effective_from':effective_from,'rules':{}}
 if re.search(r'\b30\s*(day|days)\b',t) and any(x in t for x in ['leave','lop','unpaid']):proposal['rules']['lop_basis']='30_days'
 elif re.search(r'\b26\s*(day|days)\b',t) and any(x in t for x in ['leave','lop','unpaid']):proposal['rules']['lop_basis']='26_working_days'
 elif 'calendar' in t and any(x in t for x in ['leave','lop','unpaid']):proposal['rules']['lop_basis']='calendar_days'
 if ('15,000' in t or '15000' in t) and 'pf' in t:proposal['rules']['pf_basis']='capped_basic'
 elif 'full basic' in t or 'all of basic' in t:proposal['rules']['pf_basis']='full_basic'
 bonus=re.search(r'bonus.*?₹?\s*([0-9,]+).*?(?:to|for)\s+([a-z0-9_-]+)',t)
 if bonus: proposal['bonus']={'amount':float(bonus.group(1).replace(',','')),'employee_code':bonus.group(2)}
 if not proposal['rules'] and not proposal.get('bonus'):return {'status':'needs_clarification','message':'Could not safely interpret. Try: Set unpaid leave divisor to 30 days effective 2026-07, or set PF to first ₹15,000 of basic.'}
 pid=db.save_proposal(instruction,proposal); return {'id':pid,'status':'pending_review','instruction':instruction,'proposal':proposal,'message':'Proposal only. No payroll rule or employee pay was changed.'}
@app.post('/api/proposals/{pid}/approve')
def approve_proposal(pid:int):
 r=db.approve_proposal(pid)
 if not r:raise HTTPException(404,'Proposal not found')
 return {'status':'approved','message':'Proposal applied as dated data. Recalculate a draft to see its effect.'}
@app.post('/api/rules')
def rule(key:str=Form(...),value:str=Form(...),effective_from:str=Form(...),note:str=Form('Finance-approved rule')):
 if not re.fullmatch(r'\d{4}-\d{2}',effective_from):raise HTTPException(400,'Effective date must be YYYY-MM.')
 if key not in {'lop_basis','pf_basis','pf_rate','esi_rate','esi_ceiling','pt_karnataka_threshold','pt_karnataka_amount'}:raise HTTPException(400,'Unsupported rule key')
 if key=='lop_basis' and value not in {'calendar_days','30_days','26_working_days'}:raise HTTPException(400,'Invalid LOP basis')
 if key=='pf_basis' and value not in {'capped_basic','full_basic'}:raise HTTPException(400,'Invalid PF basis')
 db.add_rule(key,value,effective_from,note);return {'saved':True}
@app.post('/api/calculate')
def calculate_month(month:str=Form(...)):
 if not re.fullmatch(r'\d{4}-\d{2}',month):raise HTTPException(400,'Month must be YYYY-MM')
 emps=db.employees()
 if not emps:raise HTTPException(400,'Load synthetic demo data or import a spreadsheet first')
 rules=db.active_rules(month); results=[calculate(e,rules,month) for e in emps]
 rid=db.create_run(month,{'rules':rules,'employee_source':'latest imported/demonstration records'},results);return db.get_run(rid)
@app.post('/api/runs/{rid}/submit')
def submit(rid:int,maker:str=Form('Finance maker')):
 r=db.set_status(rid,'pending_approval',maker)
 if not r:raise HTTPException(400,'Run must be calculated before submission')
 return r
@app.post('/api/runs/{rid}/approve')
def approve(rid:int,checker:str=Form('Finance checker')):
 r=db.set_status(rid,'approved',checker)
 if not r:raise HTTPException(400,'Run must be awaiting approval')
 return r
@app.get('/api/runs/{rid}')
def run(rid:int):
 r=db.get_run(rid)
 if not r:raise HTTPException(404,'Run not found')
 return r
@app.get('/api/runs/{rid}/export/{kind}')
def export(rid:int,kind:str):
 r=db.get_run(rid)
 if not r:raise HTTPException(404,'Run not found')
 if r['status']!='approved':raise HTTPException(400,'A second-person approval is required before exports')
 cols={'register':['employee_code','employee_name','basic','hra','allowances','gross','unpaid_leave_days','lop_divisor','lop_deduction','pf_wage','pf','esi','professional_tax','tds','other_deductions','net_pay'],'pf':['employee_code','employee_name','pf_wage','pf'],'esi':['employee_code','employee_name','gross','esi'],'pt':['employee_code','employee_name','state','professional_tax'],'tds':['employee_code','employee_name','tds']}
 if kind not in cols:raise HTTPException(404,'Unknown export type')
 out=io.StringIO();w=csv.DictWriter(out,fieldnames=cols[kind]);w.writeheader();w.writerows([{k:x.get(k,'') for k in cols[kind]} for x in r['results']])
 return StreamingResponse(iter([out.getvalue()]),media_type='text/csv',headers={'Content-Disposition':f'attachment; filename="{r["month"]}_{kind}.csv"'})
