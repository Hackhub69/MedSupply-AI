import os, sqlite3, math, re, hashlib
from datetime import date, timedelta
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)
ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join('/tmp', f'medsupply-demo-{os.getpid()}.db') if os.getenv('VERCEL') else os.path.join(ROOT, 'demo.db')
TODAY = date.today()

SCHEMA = [
    "CREATE TABLE hospitals (id INTEGER PRIMARY KEY, name VARCHAR(100), city VARCHAR(100))",
    "CREATE TABLE medicines (id INTEGER PRIMARY KEY, name VARCHAR(100), unit VARCHAR(30))",
    "CREATE TABLE inventory (hospital_id INTEGER, medicine_id INTEGER, quantity INTEGER, expiry VARCHAR(10))",
    "CREATE TABLE demand (hospital_id INTEGER, medicine_id INTEGER, day VARCHAR(10), quantity INTEGER)",
    "CREATE TABLE suppliers (id INTEGER PRIMARY KEY, name VARCHAR(100), medicine_id INTEGER, lead_days INTEGER)",
    "CREATE TABLE documents (id INTEGER PRIMARY KEY, title VARCHAR(150), content VARCHAR(2000))"
]

def connect():
    connection = os.getenv('DB2_CONNECTION_STRING')
    if connection:
        import ibm_db
        handle = ibm_db.connect(connection, '', '')
        return ('db2', handle)
    return ('sqlite', sqlite3.connect(DB_PATH))

def query(sql, params=()):
    kind, conn = connect()
    try:
        if kind == 'sqlite':
            conn.row_factory = sqlite3.Row
            return [dict(row) for row in conn.execute(sql, params).fetchall()]
        import ibm_db
        stmt = ibm_db.prepare(conn, sql)
        ibm_db.execute(stmt, tuple(params))
        rows = []
        row = ibm_db.fetch_assoc(stmt)
        while row:
            rows.append({str(k).lower(): v for k, v in row.items()})
            row = ibm_db.fetch_assoc(stmt)
        return rows
    finally:
        if kind == 'sqlite': conn.close()
        else:
            import ibm_db
            ibm_db.close(conn)

def init_demo():
    if os.path.exists(DB_PATH): return
    c = sqlite3.connect(DB_PATH)
    try:
        for statement in SCHEMA: c.execute(statement)
        c.executemany('INSERT INTO hospitals VALUES (?, ?, ?)', [(1,'Central Hospital','Pune'),(2,'Riverside Hospital','Pune'),(3,'Hillview Hospital','Mumbai')])
        c.executemany('INSERT INTO medicines VALUES (?, ?, ?)', [(1,'Amoxicillin 500 mg','capsules'),(2,'Insulin glargine','vials'),(3,'Salbutamol inhaler','inhalers')])
        stocks=[(1,1,120,45),(2,1,1100,50),(3,1,250,180),(1,2,30,120),(2,2,220,35),(3,2,90,160),(1,3,70,180),(2,3,300,100),(3,3,45,150)]
        c.executemany('INSERT INTO inventory VALUES (?, ?, ?, ?)', [(h,m,q,(TODAY+timedelta(days=d)).isoformat()) for h,m,q,d in stocks])
        rates={(1,1):20,(2,1):8,(3,1):6,(1,2):5,(2,2):2,(3,2):3,(1,3):4,(2,3):3,(3,3):5}
        c.executemany('INSERT INTO demand VALUES (?, ?, ?, ?)', [(h,m,(TODAY-timedelta(days=i)).isoformat(), max(0, rate + ((i*7+h+m)%5)-2)) for (h,m),rate in rates.items() for i in range(1,29)])
        c.executemany('INSERT INTO suppliers VALUES (?, ?, ?, ?)', [(1,'MedSource',1,7),(2,'Healthline',2,10),(3,'CareSupply',3,5)])
        c.executemany('INSERT INTO documents VALUES (?, ?, ?)', [(1,'Transfer handling','Verify medicine identity, batch, expiry and receiving hospital capacity before any stock transfer. A pharmacist must approve the transfer.'),(2,'Cold chain guidance','Insulin requires a validated cold chain during storage and transfer. Confirm temperature requirements with the manufacturer and local policy.'),(3,'Procurement guidance','Review supplier lead time and current stock before ordering. Escalate projected shortages to the procurement team.')])
        c.commit()
    finally: c.close()

class HashEmbeddings:
    # Deterministic local embeddings for the prototype, not a clinical semantic model.
    def embed_query(self, text):
        vec=[0.0]*128
        for word in re.findall(r'[a-z0-9]+', text.lower()):
            idx=int(hashlib.sha256(word.encode()).hexdigest(),16)%128
            vec[idx]+=1
        norm=math.sqrt(sum(x*x for x in vec)) or 1
        return [x/norm for x in vec]
    def embed_documents(self, texts): return [self.embed_query(x) for x in texts]

def guidance(question):
    from langchain_core.vectorstores import InMemoryVectorStore
    from langchain_core.embeddings import Embeddings
    from langchain_core.documents import Document
    class LocalEmbeddings(Embeddings, HashEmbeddings):
        def embed_query(self, text): return HashEmbeddings.embed_query(self, text)
        def embed_documents(self, texts): return HashEmbeddings.embed_documents(self, texts)
    docs=query('SELECT title, content FROM documents')
    if not docs: return []
    store=InMemoryVectorStore(embedding=LocalEmbeddings())
    store.add_documents([Document(page_content=d['content'], metadata={'title':d['title']}) for d in docs])
    return [{'title':d.metadata['title'],'content':d.page_content} for d in store.similarity_search(question,k=min(2,len(docs)))]

def analyze(scenario=None):
    hospitals=query('SELECT id, name, city FROM hospitals')
    medicines=query('SELECT id, name, unit FROM medicines')
    inventory=query('SELECT hospital_id, medicine_id, quantity, expiry FROM inventory')
    demand=query('SELECT hospital_id, medicine_id, day, quantity FROM demand')
    suppliers=query('SELECT medicine_id, lead_days FROM suppliers')
    hm={x['id']:x for x in hospitals}; mm={x['id']:x for x in medicines}
    rates={}
    for d in demand:
        try: day=date.fromisoformat(str(d['day'])[:10])
        except ValueError: continue
        if TODAY-timedelta(days=28) <= day < TODAY:
            key=(d['hospital_id'],d['medicine_id']); rates[key]=rates.get(key,0)+int(d['quantity'])
    # Divide by 28 calendar days, including days without recorded consumption.
    rates={k:v/28 for k,v in rates.items()}
    if scenario:
        key=(scenario['hospital_id'], scenario['medicine_id'])
        if key in rates: rates[key] *= scenario['demand_multiplier']
    grouped={}
    for row in inventory:
        key=(row['hospital_id'],row['medicine_id'])
        if key[0] not in hm or key[1] not in mm: continue
        try: expiry=date.fromisoformat(str(row['expiry'])[:10])
        except ValueError: continue
        if expiry < TODAY: continue
        entry=grouped.setdefault(key, {'quantity':0,'batches':[]})
        entry['quantity']+=int(row['quantity']); entry['batches'].append((expiry,int(row['quantity'])))
    cards=[]
    for (h,m),g in grouped.items():
        rate=rates.get((h,m),0); days=round(g['quantity']/rate,1) if rate else None
        near=sum(q for e,q in g['batches'] if e<=TODAY+timedelta(days=30))
        cards.append({'hospital_id':h,'medicine_id':m,'hospital':hm[h]['name'],'city':hm[h]['city'],'medicine':mm[m]['name'],'unit':mm[m]['unit'],'quantity':g['quantity'],'daily_demand':round(rate,1),'days_left':days,'expiring':near,'status':'No demand data' if not rate and not near else ('Shortage risk' if rate and g['quantity']/rate<14 else ('Expiry risk' if near else 'Stable'))})
    recommendations=[]
    # Allocate each donor's usable surplus once across recipients.
    available={}
    for c in cards:
        key=(c['hospital_id'],c['medicine_id']); rate=rates.get(key,0)
        if rate<=0: continue
        safe_batches=sum(q for e,q in grouped[key]['batches'] if e>TODAY+timedelta(days=14))
        available[key]=max(0,min(safe_batches, math.floor(c['quantity']-rate*30)))
    for receiver in sorted(cards,key=lambda c: c['days_left'] if c['days_left'] is not None else float('inf')):
        if receiver['days_left'] is None or receiver['quantity']/rates[(receiver['hospital_id'],receiver['medicine_id'])]>=14: continue
        need=max(0, math.ceil(rates[(receiver['hospital_id'],receiver['medicine_id'])]*30-receiver['quantity']))
        donors=sorted([d for d in cards if d['medicine_id']==receiver['medicine_id'] and d['hospital_id']!=receiver['hospital_id']],key=lambda d: (d['city']!=receiver['city'], -available.get((d['hospital_id'],d['medicine_id']),0)))
        for donor in donors:
            key=(donor['hospital_id'],donor['medicine_id']); amount=min(need,available.get(key,0))
            if amount<=0: continue
            recommendations.append({'medicine':receiver['medicine'],'unit':receiver['unit'],'source':donor['hospital'],'destination':receiver['hospital'],'quantity':amount,'days_left':receiver['days_left'],'receiver_stock':receiver['quantity'],'receiver_daily':receiver['daily_demand'],'donor_stock':donor['quantity'],'donor_daily':donor['daily_demand'],'reason':'Target 30 days of recipient stock; preserve 30 days at the donor. Batches expiring within 14 days are excluded from transferable stock.'})
            available[key]-=amount; need-=amount
            if need<=0: break
    return {'cards':cards,'recommendations':recommendations,'suppliers':suppliers,'as_of':TODAY.isoformat(),'backend':'IBM Db2' if os.getenv('DB2_CONNECTION_STRING') else 'Local sample data'}

if os.getenv('VERCEL') and not os.getenv('DB2_CONNECTION_STRING'):
    init_demo()

@app.route('/')
def index():
    data=analyze()
    return render_template('index.html', data=data, guidance=guidance('medicine transfer expiry cold chain pharmacist approval'))

@app.route('/workspace')
def workspace():
    data=analyze()
    hospitals=query('SELECT id, name, city FROM hospitals')
    medicines=query('SELECT id, name, unit FROM medicines')
    suppliers=query('SELECT name, medicine_id, lead_days FROM suppliers')
    for hospital in hospitals:
        positions=[c for c in data['cards'] if c['hospital_id']==hospital['id']]
        hospital['positions']=len(positions)
        hospital['shortages']=sum(c['status']=='Shortage risk' for c in positions)
        hospital['expiries']=sum(c['expiring']>0 for c in positions)
    for medicine in medicines:
        positions=[c for c in data['cards'] if c['medicine_id']==medicine['id']]
        medicine['stock']=sum(c['quantity'] for c in positions)
        medicine['facilities']=len(positions)
        medicine['suppliers']=[supplier for supplier in suppliers if supplier['medicine_id']==medicine['id']]
    return render_template('workspace.html', data=data, hospitals=hospitals, medicines=medicines)

@app.route('/api/overview')
def overview(): return jsonify(analyze())

@app.post('/api/scenario')
def scenario():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict): return jsonify(error='Send a JSON object.'), 400
    h, m, multiplier = payload.get('hospital_id'), payload.get('medicine_id'), payload.get('demand_multiplier')
    if type(h) is not int or type(m) is not int or type(multiplier) not in (int, float) or not math.isfinite(multiplier) or not 0.5 <= multiplier <= 3:
        return jsonify(error='Select a hospital and medicine, and enter a demand multiplier from 0.5 to 3.'), 400
    baseline=analyze()
    before=next((c for c in baseline['cards'] if c['hospital_id']==h and c['medicine_id']==m),None)
    if not before or before['days_left'] is None:
        return jsonify(error='This inventory position has no usable demand history.'), 400
    projected=analyze({'hospital_id':h,'medicine_id':m,'demand_multiplier':multiplier})
    after=next(c for c in projected['cards'] if c['hospital_id']==h and c['medicine_id']==m)
    proposals=[r for r in projected['recommendations'] if r['destination']==after['hospital'] and r['medicine']==after['medicine']]
    return jsonify(before=before, after=after, recommendations=proposals, multiplier=multiplier)


if __name__ == '__main__':
    if not os.getenv('DB2_CONNECTION_STRING'): init_demo()
    app.run(host='127.0.0.1', port=int(os.getenv('PORT','5000')), debug=False)
