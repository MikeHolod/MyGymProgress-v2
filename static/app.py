from flask import Flask, request, jsonify
import sqlite3, datetime, os
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

DB_PATH = os.environ.get('DB_PATH', 'database.db')
BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
ADMIN_CHAT_ID = os.environ.get('ADMIN_CHAT_ID', '')
PUBLIC_URL = os.environ.get('PUBLIC_URL', '')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id TEXT,
            date TEXT,
            name TEXT,
            muscle TEXT,
            total REAL
        )
    """)
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/api/init', methods=['POST'])
def api_init():
    body = request.get_json(silent=True) or {}
    initData = body.get('initData') or {}
    tg_id = 'anon'
    if isinstance(initData, dict) and initData.get('user'):
        tg_id = str(initData['user'].get('id','anon'))
    conn = get_db()
    cur = conn.execute('SELECT date,name,total FROM workouts WHERE tg_id=? ORDER BY id DESC LIMIT 20',(tg_id,))
    rows = cur.fetchall()
    conn.close()
    history = [{'date':r['date'],'name':r['name'],'total':r['total']} for r in rows]
    return jsonify({'history':history})

@app.route('/api/log', methods=['POST'])
def api_log():
    body = request.get_json(silent=True) or {}
    name = body.get('name','Без названия')
    muscle = body.get('muscle_group','—')
    sets = body.get('sets',[])
    initData = body.get('initData') or {}
    tg_id='anon'
    if isinstance(initData, dict) and initData.get('user'):
        tg_id=str(initData['user'].get('id','anon'))
    total=0
    for s in sets:
        try: total+=float(s.get('reps',0))*float(s.get('weight',0))
        except: pass
    date=datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    conn=get_db()
    conn.execute('INSERT INTO workouts (tg_id,date,name,muscle,total) VALUES (?,?,?,?,?)',(tg_id,date,name,muscle,total))
    conn.commit()
    conn.close()
    return jsonify({'ok':True,'total':total})

@app.route('/send_button')
def send_button():
    import requests, json
    if not BOT_TOKEN or not ADMIN_CHAT_ID or not PUBLIC_URL:
        return 'Set BOT_TOKEN, ADMIN_CHAT_ID, PUBLIC_URL',400
    keyboard={"inline_keyboard":[[{"text":"Открыть MyGymProgress","web_app":{"url":PUBLIC_URL}}]]}
    params={'chat_id':ADMIN_CHAT_ID,'text':'Открыть приложение MyGymProgress','reply_markup':json.dumps(keyboard)}
    r=requests.get(f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',params=params)
    return ('OK' if r.ok else r.text)

if __name__=='__main__':
    init_db()
    port=int(os.environ.get('PORT',5000))
    app.run(host='0.0.0.0',port=port)

