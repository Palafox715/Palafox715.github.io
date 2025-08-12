import os
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask import (
    Flask, render_template, request, redirect, url_for, Response, jsonify
)

# ──────────────────────────────────────────────────────────────────────────────
# Persistencia amigable con Railway (y local)
# ──────────────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.getenv("DATA_DIR", os.path.join(BASE_DIR, "data"))  # ./data por defecto
os.makedirs(DATA_DIR, exist_ok=True)                               # crea carpeta si no existe
DATABASE = os.path.join(DATA_DIR, "tickets.db")

# ──────────────────────────────────────────────────────────────────────────────
# App
# ──────────────────────────────────────────────────────────────────────────────
app = Flask(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Pruebade rutas
# ──────────────────────────────────────────────────────────────────────────────

@app.route("/__routes")
def __routes():
    return "<br>".join(sorted(str(r) for r in app.url_map.iter_rules()))

@app.route("/__health")
def __health():
    return "OK"

# ──────────────────────────────────────────────────────────────────────────────
# Catálogos
# ──────────────────────────────────────────────────────────────────────────────
CUBICULOS = [
    'A01','A02','A03','A04','A05','A06','A07','A08','A09','A10','A11','A12','A13','A14','A15','A16',
    'A17','A18','A19','A20','A21','A22','A23','A24','A25','A26','A27','A28','A29','A30','A31','A32',
    'A33','A34','A35','A36','A37','A38','A39','A40','A41','A42','A43','A44','A45','A46','A47','A48',
    'B01','B02','B03','B04','B05','B06','B07','B08','B09','B10','B11','B12','B13','B14','B15','B16',
    'B17','B18','B19','B20','B21','B22',
    'C01','C02','C03','C04','C05','C06','C07','C08','C09','C10','C11','C12','C13','C14','C15','C16',
    'C17','C18','C19','C20','C21','C22',
    'D01','D02','D03','D04','D05','D06','D07','D08','D09','D10','D11','D12','D13','D14','D15','D16',
    'D17','D18','D19','D20','D21',
    'E01','E02','E03','E04','E05','E06','E07','E08','E09','E10','E11','E12','E13','E14','E15','E16',
    'E17','E18','E19','E20','E21','E22',
    'F01','F02','F03','F04','F05','F06','F07','F08','F09','F10',
    'G01','G02','G03','G04','G05','G06','G07','G08','G09','G10',
    'H01','H02','H03','H04','H05','H06','H07','H08','H09','H10',
    'I01','I02','I03','I04','I05','I06','I07','I08','I09','I10',
    'J01','J02','J03','J04','J05','J06','J07','J08','J09','J10',
    'K1','K2','K3','TM Ricky','TM Rubi','TM Julio','TM Manuel','TM Masao','TM Oscar',
    'Back Office LCR','Back Office BTR','Contabilidad','reclutamiento','RH','Psicologia',
    'Marketing','Mantenimiento','Ovalle'
]

PROBLEMAS = [
    'Audio','Cableado','Cambio de cubículo','Computadora no enciende','HeadSet','Impresora',
    'Inicio de sesion','Instalación de equipo','Live caption','Llamadas cortadas','Logixx',
    'Monitor sin imagen','Mouse','Movimiento agente','No internet','Página congelada',
    'Pagina no carga','Sheets/Docs','Sistema congelado','Slack','Teclado','Wifi',
    'Ytel congelado','Ytel delay','Ytel Interferencias','Ytel latencia','Ytel login',
    'Ytel logout','Ytel script'
]

TECHNICOS = ['Brayan', 'Hans', 'Diana', 'Ismael']

# Normalización de cubículos
CUBICULOS_MAP = {c.lower(): c for c in CUBICULOS}
def canon_cubiculo(name: str):
    if not name: return None
    return CUBICULOS_MAP.get(name.strip().lower())

# Password fallback (borrado seguro) si no hay hash en settings
ADMIN_PASS_FALLBACK = os.getenv('ADMIN_PASS', 'cambia-esto')

# ──────────────────────────────────────────────────────────────────────────────
# DB helpers
# ──────────────────────────────────────────────────────────────────────────────
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            cubiculo      TEXT    NOT NULL,
            problema      TEXT    NOT NULL,
            solucion      TEXT,
            status        TEXT    NOT NULL DEFAULT 'pendiente',
            atendido_por  TEXT,
            hora          TEXT,
            observaciones TEXT
        );
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
    ''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_ticket_cub_status ON tickets (cubiculo, status)')
    conn.commit()
    conn.close()

def get_setting(key: str):
    conn = get_db_connection()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row['value'] if row else None

def set_setting(key: str, value: str):
    conn = get_db_connection()
    conn.execute("REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def verify_admin_password(pwd: str) -> bool:
    hash_in_db = get_setting('admin_pass_hash')
    if hash_in_db:
        return check_password_hash(hash_in_db, pwd or '')
    return (pwd or '') == ADMIN_PASS_FALLBACK

# ──────────────────────────────────────────────────────────────────────────────
# Hooks
# ──────────────────────────────────────────────────────────────────────────────
@app.before_request
def _ensure_db():
    init_db()

# ──────────────────────────────────────────────────────────────────────────────
# Utilidades
# ──────────────────────────────────────────────────────────────────────────────
def query_tickets(status: str, tech: str):
    conn = get_db_connection()
    where, params = [], []
    if status in ('pendiente', 'en progreso', 'resuelto'):
        where.append("status=?"); params.append(status)
    if tech and tech != 'todos':
        where.append("atendido_por=?"); params.append(tech)
    sql = "SELECT * FROM tickets"
    if where: sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY id DESC"
    rows = conn.execute(sql, tuple(params)).fetchall()
    conn.close()
    return rows

# ──────────────────────────────────────────────────────────────────────────────
# Rutas
# ──────────────────────────────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def index():
    # Puedes cambiar a redirect(url_for('submit_ticket')) si prefieres
    return render_template("form.html", message=request.args.get('message'),
                           category=request.args.get('category','success'),
                           cubiculos=CUBICULOS, problemas=PROBLEMAS)

@app.route('/', methods=['POST'])
def submit_ticket():
    cubiculo_in = request.form['cubiculo']
    problema = request.form['problema'].strip()

    cubiculo = canon_cubiculo(cubiculo_in)
    if not cubiculo:
        return redirect(url_for('index', message='❌ Cubículo inválido.', category='error'))

    if problema not in PROBLEMAS:
        return redirect(url_for('index', message='❌ Problema inválido.', category='error'))

    conn = get_db_connection()
    row = conn.execute(
        "SELECT COUNT(*) AS cnt FROM tickets WHERE lower(cubiculo)=lower(?) AND status!='resuelto'",
        (cubiculo,)
    ).fetchone()
    if row['cnt'] > 0:
        conn.close()
        return redirect(url_for('index',
            message='❌ Ya tienes un ticket pendiente en tu cubículo. Espera a que sea atendido.',
            category='error'))

    hora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn.execute('INSERT INTO tickets (cubiculo, problema, hora) VALUES (?, ?, ?)',
                 (cubiculo, problema, hora))
    conn.commit(); conn.close()
    return redirect(url_for('index', message='🎫 Ticket generado correctamente', category='success'))

@app.route('/dashboard')
def dashboard():
    status = request.args.get('status', 'todos')
    tech   = request.args.get('tech', 'todos')
    tickets = query_tickets(status, tech)
    message  = request.args.get('message')
    category = request.args.get('category', 'success')
    return render_template('dashboard.html',
        tickets=tickets, tecnicos=TECHNICOS,
        cubiculos=CUBICULOS, problemas=PROBLEMAS,
        selected_status=status, selected_tech=tech,
        message=message, category=category)

@app.route('/dashboard/table')
def dashboard_table():
    status   = request.args.get('status', 'todos')
    tech     = request.args.get('tech', 'todos')
    since_id = request.args.get('since_id', type=int, default=0)

    tickets = query_tickets(status, tech)  # DESC
    html = render_template('_tickets_tbody.html', tickets=tickets, tecnicos=TECHNICOS)
    max_id = max([t['id'] for t in tickets], default=0)

    news = []
    if since_id:
        for t in tickets:
            if t['id'] > since_id:
                news.append({'id': t['id'], 'cubiculo': t['cubiculo'], 'problema': t['problema'], 'hora': t['hora']})
            else:
                break

    return jsonify({'html': html, 'max_id': max_id, 'news': news})

@app.route('/process/<int:ticket_id>')
def process_ticket(ticket_id):
    conn = get_db_connection()
    conn.execute("UPDATE tickets SET status='en progreso' WHERE id=?", (ticket_id,))
    conn.commit(); conn.close()
    return redirect(url_for('dashboard'))

@app.route('/resolve/<int:ticket_id>', methods=['POST'])
def resolve_ticket(ticket_id):
    tecnico  = request.form['atendido_por'].strip()
    solucion = request.form['solucion'].strip()
    if tecnico not in TECHNICOS:
        return redirect(url_for('dashboard', message='❌ Técnico inválido.', category='error'))
    conn = get_db_connection()
    conn.execute("UPDATE tickets SET solucion=?, status='resuelto', atendido_por=? WHERE id=?",
                 (solucion, tecnico, ticket_id))
    conn.commit(); conn.close()
    return redirect(url_for('dashboard'))

@app.route('/ticket/<int:ticket_id>/edit', methods=['POST'])
def edit_ticket(ticket_id):
    cubiculo_in   = request.form.get('cubiculo','')
    problema      = request.form.get('problema','').strip()
    status        = request.form.get('status','').strip()
    tecnico       = request.form.get('atendido_por','').strip()
    solucion      = request.form.get('solucion','').strip()
    hora_in       = request.form.get('hora','').strip()
    observaciones = request.form.get('observaciones','').strip() or None

    cubiculo = canon_cubiculo(cubiculo_in)
    if not cubiculo:
        return redirect(url_for('dashboard', message='❌ Cubículo inválido.', category='error'))

    if problema not in PROBLEMAS or status not in ('pendiente','en progreso','resuelto'):
        return redirect(url_for('dashboard', message='❌ Datos inválidos en edición.', category='error'))

    if status == 'resuelto':
        if tecnico not in TECHNICOS or not solucion:
            return redirect(url_for('dashboard', message='❌ Para "resuelto" elige técnico y escribe solución.', category='error'))
    else:
        tecnico = None
        solucion = None

    def normalize_hora(s):
        if not s: return None
        s = s.replace('T', ' ')
        for fmt in ('%Y-%m-%d %H:%M', '%Y-%m-%d %H:%M:%S'):
            try:
                dt = datetime.strptime(s, fmt)
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                continue
        return None

    hora_norm = normalize_hora(hora_in)
    conn = get_db_connection()
    if not hora_norm:
        row = conn.execute("SELECT hora FROM tickets WHERE id=?", (ticket_id,)).fetchone()
        if not row:
            conn.close()
            return redirect(url_for('dashboard', message='❌ Ticket no encontrado.', category='error'))
        hora_norm = row['hora']

    conn.execute(
        "UPDATE tickets SET cubiculo=?, problema=?, status=?, atendido_por=?, solucion=?, hora=?, observaciones=? WHERE id=?",
        (cubiculo, problema, status, tecnico, solucion, hora_norm, observaciones, ticket_id)
    )
    conn.commit(); conn.close()
    return redirect(url_for('dashboard', message='✏️ Ticket actualizado.', category='success'))

@app.route('/admin/delete_selected', methods=['POST'])
def admin_delete_selected():
    pwd = request.form.get('password', '')
    confirm = request.form.get('confirm', '')
    ids_str = request.form.get('ids', '').strip()

    if not verify_admin_password(pwd) or confirm != 'ELIMINAR':
        return jsonify({'ok': False, 'error': 'Clave o confirmación incorrecta.'}), 400

    ids = [int(x) for x in ids_str.split(',') if x.isdigit()]
    if not ids:
        return jsonify({'ok': False, 'error': 'Sin IDs válidos.'}), 400

    conn = get_db_connection()
    qmarks = ','.join(['?'] * len(ids))
    conn.execute(f"DELETE FROM tickets WHERE id IN ({qmarks})", ids)
    conn.commit(); conn.close()
    return jsonify({'ok': True, 'deleted': len(ids)})

@app.route('/admin/settings', methods=['GET', 'POST'])
def admin_settings():
    hash_in_db = get_setting('admin_pass_hash')
    if request.method == 'POST':
        current = request.form.get('current', '')
        new     = request.form.get('new', '').strip()
        confirm = request.form.get('confirm', '').strip()
        if not new or len(new) < 4:
            return render_template('admin_settings.html',
                has_hash=bool(hash_in_db), message='❌ La nueva clave debe tener al menos 4 caracteres.', category='error')
        if new != confirm:
            return render_template('admin_settings.html',
                has_hash=bool(hash_in_db), message='❌ Las claves no coinciden.', category='error')
        if hash_in_db and not verify_admin_password(current):
            return render_template('admin_settings.html',
                has_hash=True, message='❌ Clave actual incorrecta.', category='error')
        set_setting('admin_pass_hash', generate_password_hash(new))
        return redirect(url_for('dashboard', message='🔐 Clave actualizada correctamente.', category='success'))
    return render_template('admin_settings.html', has_hash=bool(hash_in_db))

@app.route('/export')
def export_tickets():
    conn = get_db_connection()
    tickets = conn.execute('SELECT * FROM tickets').fetchall()
    conn.close()

    def csv_escape(s):
        if s is None: return ''
        return str(s).replace('"', '""')

    def generate():
        yield '\ufeff'
        yield 'id,cubiculo,problema,solucion,status,atendido_por,hora,observaciones\r\n'
        for t in tickets:
            row = [str(t['id']), csv_escape(t['cubiculo']), csv_escape(t['problema']),
                   csv_escape(t['solucion']), csv_escape(t['status']),
                   csv_escape(t['atendido_por']), csv_escape(t['hora']),
                   csv_escape(t['observaciones'] if 'observaciones' in t.keys() else '')]
            yield ','.join(f'"{c}"' for c in row) + '\r\n'

    return Response(generate(), mimetype='text/csv',
        headers={"Content-Disposition": "attachment; filename=tickets.csv"})

# ──────────────────────────────────────────────────────────────────────────────
# Arranque (Railway: puerto dinámico)
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

