from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from backend.api_transactions import router as transactions_router
from backend.api_chat import router as chat_router
from backend.db import init_db as init_ledgermind_db
import sqlite3, csv, io, json, random, re, os
from datetime import date, timedelta
from difflib import SequenceMatcher
from pathlib import Path
from integrations import memory_status, remember_vendor_event, recall_vendor_context, generate_vendor_message
from gst_engine.calculator import calculate_invoice
from gst_engine.reports import generate_gst_summary_report
BASE=Path(__file__).parent
DB=BASE/'gst_agent.db'
app=FastAPI(title='LedgerMind GST Agent', version='2.0.0')
app.include_router(transactions_router)
app.include_router(chat_router)
app.mount('/static',StaticFiles(directory=BASE/'static'),name='static')
templates=Jinja2Templates(directory=BASE/'templates')

def db():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

def init_db():
    c=db(); q=c.cursor()
    q.executescript('''CREATE TABLE IF NOT EXISTS purchase(id INTEGER PRIMARY KEY, month TEXT, vendor TEXT, gstin TEXT, invoice TEXT, invoice_date TEXT, taxable REAL, tax REAL);
    CREATE TABLE IF NOT EXISTS gstr2b(id INTEGER PRIMARY KEY, month TEXT, vendor TEXT, gstin TEXT, invoice TEXT, invoice_date TEXT, taxable REAL, tax REAL);
    CREATE TABLE IF NOT EXISTS memory(vendor TEXT PRIMARY KEY, gstin TEXT, late_count INTEGER DEFAULT 0, months_seen INTEGER DEFAULT 0, typo_count INTEGER DEFAULT 0, preferred_channel TEXT DEFAULT 'Email', last_outcome TEXT DEFAULT 'Not contacted', notes TEXT DEFAULT '');
    CREATE TABLE IF NOT EXISTS actions(id INTEGER PRIMARY KEY AUTOINCREMENT, vendor TEXT, issue TEXT, channel TEXT, draft TEXT, status TEXT DEFAULT 'Draft', created_at TEXT DEFAULT CURRENT_TIMESTAMP);''')
    if q.execute('SELECT COUNT(*) FROM purchase').fetchone()[0]==0: seed(q)
    c.commit(); c.close()

def seed(q):
    random.seed(19)
    names=['Sharma Traders','Apex Components','Sri Lakshmi Supplies','BluePeak Systems','Nandi Electricals','Metro Packaging','Kaveri Industries','Orion Distributors','GreenLeaf Papers','Vertex Tools','Prime Office Mart','Crest Chemicals','Delta Fasteners','Sunrise Metals','Nova Logistics']
    names += [f'{random.choice(["A1","Bharat","Classic","Global","National","Om","Royal"])} {random.choice(["Enterprises","Traders","Industries","Suppliers","Solutions"])} {i}' for i in range(1,46)]
    months=['2026-05','2026-06','2026-07','2026-08','2026-09','2026-10']
    for idx,name in enumerate(names):
        gstin=f'29{random.randint(10000,99999)}{random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")}{random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")}{random.randint(1000,9999)}Z{random.randint(1,9)}'
        habitual_late=idx==0; typo_vendor=idx==1; whatsapp=idx==2
        late=0; typo=0
        for mi,m in enumerate(months):
            late_flag=habitual_late and mi in [1,2,3,4] or (not habitual_late and random.random()<.12)
            late += int(late_flag); typo += int(typo_vendor and mi in [0,2,4])
            for j in range(random.randint(1,2)):
                inv=f'{idx+1:03d}/{mi+1:02d}/{j+1:03d}'
                invdate=f'{m}-{random.randint(2,24):02d}'
                taxable=round(random.uniform(2500,85000),2); tax=round(taxable*.18,2)
                q.execute('INSERT INTO purchase(month,vendor,gstin,invoice,invoice_date,taxable,tax) VALUES(?,?,?,?,?,?,?)',(m,name,gstin,inv,invdate,taxable,tax))
                # Most appear in 2B; plant one or two issues for selected vendors.
                omit=(habitual_late and mi in [1,3,5] and j==0) or (idx%9==0 and mi==4 and j==1)
                if omit: continue
                gst=gstin
                inv2=inv
                tx2=tax
                if typo_vendor and mi in [0,2,4] and j==0: gst=gstin[:-2]+'X'+gstin[-1]
                if idx%11==0 and mi==2 and j==0: inv2=inv.replace('/','-')
                if idx%13==0 and mi==3 and j==0: tx2=round(tax*.9,2)
                q.execute('INSERT INTO gstr2b(month,vendor,gstin,invoice,invoice_date,taxable,tax) VALUES(?,?,?,?,?,?,?)',(m,name,gst,inv2,invdate,taxable,tx2))
        q.execute('INSERT OR REPLACE INTO memory(vendor,gstin,late_count,months_seen,typo_count,preferred_channel,last_outcome,notes) VALUES(?,?,?,?,?,?,?,?)',(name,gstin,late,6,typo,'WhatsApp' if whatsapp else 'Email','WhatsApp nudge worked' if whatsapp else 'Awaiting vendor response', 'Habitual late filer' if habitual_late else ('Repeated GSTIN typo' if typo_vendor else '')))

def norm(s): return re.sub(r'[^A-Z0-9]','',str(s or '').upper())
def analyze(month=None):
    c=db(); p=c.execute('SELECT * FROM purchase'+(' WHERE month=?' if month else ''),((month,) if month else ())).fetchall(); g=c.execute('SELECT * FROM gstr2b'+(' WHERE month=?' if month else ''),((month,) if month else ())).fetchall()
    g_by={}
    for r in g: g_by.setdefault(norm(r['invoice']),[]).append(r)
    rows=[]; used=set()
    for r in p:
        candidates=g_by.get(norm(r['invoice']),[])
        issue='Matched'; detail='Invoice, GSTIN and tax values agree'; risk=0
        if not candidates:
            # Fuzzy invoice lookup for GSTIN matches
            fuzzy=[]
            for gr in g:
                if SequenceMatcher(None,norm(gr['invoice']),norm(r['invoice'])).ratio()>=.82: fuzzy.append(gr)
            if fuzzy:
                gr=fuzzy[0]; issue='Invoice number mismatch'; detail=f"Possible match: {gr['invoice']}"; risk=r['tax']
            else:
                issue='Missing in GSTR-2B'; detail='Purchase invoice not found in supplier-filed GSTR-2B'; risk=r['tax']
        else:
            gr=candidates[0]; used.add(gr['id'])
            if gr['gstin']!=r['gstin']: issue='GSTIN mismatch'; detail='Supplier GSTIN differs'; risk=r['tax']
            elif abs(float(gr['tax'])-float(r['tax']))>1: issue='Tax amount mismatch'; detail=f"Books ₹{r['tax']:.2f} vs 2B ₹{gr['tax']:.2f}"; risk=abs(float(gr['tax'])-float(r['tax']))
        mem=c.execute('SELECT * FROM memory WHERE vendor=?',(r['vendor'],)).fetchone()
        if issue!='Matched':
            priority='High' if risk>=5000 or issue=='Missing in GSTR-2B' else 'Medium'
            rows.append(dict(id=r['id'],month=r['month'],vendor=r['vendor'],gstin=r['gstin'],invoice=r['invoice'],taxable=r['taxable'],tax=r['tax'],issue=issue,detail=detail,risk=round(risk,2),priority=priority,channel=mem['preferred_channel'] if mem else 'Email',late_count=mem['late_count'] if mem else 0,typo_count=mem['typo_count'] if mem else 0))
    # unmatched 2B invoices are informational, not credit-at-risk
    c.close(); return rows

@app.on_event('startup')
def startup():
    init_db()
    init_ledgermind_db()

@app.get('/',response_class=HTMLResponse)
def home(request:Request): return templates.TemplateResponse('index.html',{'request':request})
@app.get('/api/dashboard')
def dashboard():
    c=db(); total=c.execute('SELECT COUNT(*) FROM purchase').fetchone()[0]; vendors=c.execute('SELECT COUNT(DISTINCT vendor) FROM purchase').fetchone()[0]
    issues=analyze(); risk=sum(x['risk'] for x in issues); high=sum(x['priority']=='High' for x in issues)
    months=[r[0] for r in c.execute('SELECT DISTINCT month FROM purchase ORDER BY month').fetchall()]
    trend=[]
    for m in months:
        its=analyze(m); trend.append({'month':m,'risk':round(sum(x['risk'] for x in its)),'issues':len(its)})
    memories=c.execute('SELECT * FROM memory ORDER BY late_count DESC LIMIT 8').fetchall(); actions=c.execute('SELECT * FROM actions ORDER BY id DESC LIMIT 5').fetchall(); c.close()
    return {'total_invoices':total,'vendors':vendors,'issues':len(issues),'risk':round(risk,2),'high_priority':high,'matched':total-len(issues),'trend':trend,'memories':[dict(x) for x in memories],'actions':[dict(x) for x in actions]}
@app.get('/api/integrations')
def integrations(): return memory_status()

@app.get('/api/memory/{vendor}')
def vendor_memory(vendor:str):
    return {'vendor':vendor,'memories':recall_vendor_context(vendor,'vendor filing behaviour recurring GST mismatches and previously successful resolutions', detailed=True)}

@app.get('/api/issues')
def issues(month:str|None=None): return analyze(month)
@app.get('/api/vendors')
def vendors():
    c=db(); out=[dict(x) for x in c.execute('SELECT * FROM memory ORDER BY late_count DESC,typo_count DESC').fetchall()]; c.close(); return out
@app.post('/api/run-agent')
def run_agent():
    rows=analyze(); c=db(); created=0; memory_used=0; llm_used=0
    for r in rows:
        # Recall vendor-specific history from Hindsight before deciding the follow-up.
        recalled=recall_vendor_context(r['vendor'], f"{r['issue']} for invoice {r['invoice']} in {r['month']}")
        if recalled: memory_used += 1
        existing=c.execute('SELECT id FROM actions WHERE vendor=? AND issue=? AND status="Draft"',(r['vendor'],r['issue'])).fetchone()
        if existing: continue
        if r['issue']=='Missing in GSTR-2B': ask='Please confirm the filing status and share the expected GSTR-1 filing date.'
        elif r['issue']=='GSTIN mismatch': ask='Please verify the GSTIN reported against this invoice and file the required correction.'
        elif r['issue']=='Invoice number mismatch': ask='Please confirm the correct invoice number and amend the filing if required.'
        else: ask='Please verify the tax amount reported for this invoice and confirm the correction timeline.'
        fallback=f"Hello {r['vendor']} team,\n\nDuring our GSTR-2B reconciliation for invoice {r['invoice']} ({r['month']}), we noticed: {r['issue']} — {r['detail']}.\n\n{ask}\n\nThis may affect our input tax credit claim. Kindly update us at the earliest.\n\nRegards,\nFinance Team"
        draft, used_llm=generate_vendor_message(r, ask, recalled, fallback)
        llm_used += int(used_llm)
        c.execute('INSERT INTO actions(vendor,issue,channel,draft) VALUES(?,?,?,?)',(r['vendor'],r['issue'],r['channel'],draft)); created+=1
    c.commit(); c.close()
    for r in rows:
        remember_vendor_event(r['vendor'], f"Reconciliation {r['month']}: {r['issue']} on invoice {r['invoice']}; estimated tax exposure ₹{r['risk']}. Suggested channel: {r['channel']}.")
    return {'created':created,'memory_recalled':memory_used,'llm_drafts':llm_used,'message':f'Agent reviewed {len(rows)} exceptions, recalled {memory_used} vendor memories, and prepared {created} drafts ({llm_used} with Groq). Nothing was sent.'}
@app.post('/api/actions/{action_id}/sent')
def mark_sent(action_id:int):
    c=db(); cur=c.execute('UPDATE actions SET status="Marked sent" WHERE id=?',(action_id,)); c.commit(); c.close()
    if not cur.rowcount: raise HTTPException(404,'Action not found')
    return {'ok':True}
@app.post('/api/upload/{kind}')
async def upload(kind:str,file:UploadFile=File(...)):
    if kind not in ['purchase','gstr2b']: raise HTTPException(400,'Unknown file type')
    raw=(await file.read()).decode('utf-8-sig'); reader=csv.DictReader(io.StringIO(raw)); required={'month','vendor','gstin','invoice','invoice_date','taxable','tax'}
    if not reader.fieldnames or not required.issubset(set(reader.fieldnames)): raise HTTPException(400,'CSV must contain: '+', '.join(sorted(required)))
    c=db(); count=0
    for row in reader:
        try: c.execute(f'INSERT INTO {kind}(month,vendor,gstin,invoice,invoice_date,taxable,tax) VALUES(?,?,?,?,?,?,?)',(row['month'],row['vendor'],row['gstin'],row['invoice'],row['invoice_date'],float(row['taxable']),float(row['tax']))); count+=1
        except Exception as e: c.rollback(); c.close(); raise HTTPException(400,f'Invalid row: {e}')
    c.commit(); c.close(); return {'inserted':count,'kind':kind}
@app.get('/api/sample/{kind}')
def sample(kind:str):
    if kind not in ['purchase','gstr2b']: raise HTTPException(404)
    c=db(); rows=c.execute(f'SELECT month,vendor,gstin,invoice,invoice_date,taxable,tax FROM {kind} LIMIT 100').fetchall(); c.close()
    out=io.StringIO(); w=csv.writer(out); w.writerow(['month','vendor','gstin','invoice','invoice_date','taxable','tax']); w.writerows([tuple(r) for r in rows])
    from fastapi.responses import Response
    return Response(out.getvalue(),media_type='text/csv',headers={'Content-Disposition':f'attachment; filename={kind}_sample.csv'})
@app.get('/api/actions')
def actions():
    c=db(); rows=[dict(x) for x in c.execute('SELECT * FROM actions ORDER BY id DESC').fetchall()]; c.close(); return rows
# ==========================================
# GST Engine & Financial Logic Endpoints
# ==========================================

@app.post("/api/gst/calculate")
async def api_calculate_gst(request: Request):
    """Calculates CGST, SGST, IGST and grand totals for an invoice."""
    try:
        payload = await request.json()
        result = calculate_invoice(payload)
        return {"status": "success", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal calculation error: {str(e)}")

@app.post("/api/gst/reports")
async def api_generate_gst_report(request: Request):
    """Generates GST summary reports (B2B vs B2C breakdown, rate-wise summary)."""
    try:
        data = await request.json()
        invoices = data.get("invoices", [])
        if not invoices:
            raise ValueError("No invoices provided to generate report")
        report = generate_gst_summary_report(invoices)
        return {"status": "success", "report": report}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")