from calendar import monthrange
from decimal import Decimal, ROUND_HALF_UP
D=lambda x: Decimal(str(x or 0))
def money(x): return float(D(x).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP))
def calculate(e, rules, month):
 days=monthrange(*map(int,month.split('-')))[1]
 basis=rules.get('lop_basis','calendar_days'); divisor=days if basis=='calendar_days' else (30 if basis=='30_days' else 26)
 basic,hra,allow=D(e['basic']),D(e['hra']),D(e['allowances']); gross=basic+hra+allow
 lopdays=D(e['unpaid_leave_days']); lop=gross/D(divisor)*lopdays if divisor else D(0)
 pfbase=min(basic,D(15000)) if rules.get('pf_basis','capped_basic')=='capped_basic' else basic
 pf=pfbase*D(rules.get('pf_rate','0.12'))
 esi=gross*D(rules.get('esi_rate','0.0075')) if gross<=D(rules.get('esi_ceiling','21000')) else D(0)
 state=str(e.get('state') or '').lower(); pt=D(rules.get('pt_karnataka_amount','200')) if 'karnataka' in state and gross>D(rules.get('pt_karnataka_threshold','15000')) else D(0)
 tds=D(e.get('tds',0)); other=D(e.get('other_deductions',0)); net=gross-lop-pf-esi-pt-tds-other
 b=[{'item':'Gross earnings','formula':'Basic + HRA + allowances','working':f'{basic} + {hra} + {allow}','amount':money(gross)}, {'item':'Unpaid leave','formula':f'Gross ÷ {divisor} × unpaid leave days','working':f'{money(gross)} ÷ {divisor} × {lopdays}','amount':money(lop)}, {'item':'Employee PF','formula':f'{rules.get("pf_rate","0.12")} × PF wage','working':f'{pfbase} × {rules.get("pf_rate","0.12")}','amount':money(pf)}, {'item':'Employee ESI','formula':'ESI rate × gross if gross is within configured ceiling','working':f'{rules.get("esi_rate","0.0075")} × {gross}' if esi else 'Not applicable: gross exceeds configured ceiling','amount':money(esi)}, {'item':'Professional tax','formula':'Effective-dated Karnataka demo rule','working':f'{state}; gross {gross}','amount':money(pt)}, {'item':'TDS','formula':'Imported employee TDS amount','working':str(tds),'amount':money(tds)}, {'item':'Other deductions','formula':'Imported other deductions','working':str(other),'amount':money(other)}, {'item':'Net pay','formula':'Gross − all deductions','working':'Gross less unpaid leave, PF, ESI, PT, TDS and other deductions','amount':money(net)}]
 return {'employee_code':e['code'],'employee_name':e['name'],'state':e['state'],'basic':money(basic),'hra':money(hra),'allowances':money(allow),'gross':money(gross),'unpaid_leave_days':float(lopdays),'lop_divisor':divisor,'lop_deduction':money(lop),'pf_wage':money(pfbase),'pf':money(pf),'esi':money(esi),'professional_tax':money(pt),'tds':money(tds),'other_deductions':money(other),'net_pay':money(net),'breakdown':b}
