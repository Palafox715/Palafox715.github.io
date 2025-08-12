import os
from flask import Flask, render_template, request, redirect, url_for, Response, jsonify
import sqlite3
from datetime import datetime
import csv
from werkzeug.security import generate_password_hash, check_password_hash

# --- Persistencia amigable con Railway ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.getenv("DATA_DIR", os.path.join(BASE_DIR, "data"))  # ./data por defecto
os.makedirs(DATA_DIR, exist_ok=True)  # << crea la carpeta si no existe
DATABASE = os.path.join(DATA_DIR, "tickets.db")


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)



from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("form.html")  # o la página que quieras mostrar

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)


# ──────────────────────────────────────────────────────────────────────────────
# Configuración de rutas y base de datos
# ──────────────────────────────────────────────────────────────────────────────
# Si se define un directorio de datos en las variables de entorno (ej. /mnt/data en Railway), usarlo
DATA_DIR = os.getenv('DATA_DIR', os.path.dirname(os.path.abspath(__file__)))
DATABASE = os.path.join(DATA_DIR, 'tickets.db')

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
    'K1','K2','K3','TM Ricky','TM Rubi','TM Julio','TM Manuel','TM Masao', 'TM Oscar', 'Back Office LCR',
    'Back Office BTR', 'Contabilidad','reclutamiento','RH','Psicologia','Marketing',
    'Mantenimiento','Ovalle'
]

PROBLEMAS = [
    'Audio','Cableado','Cambio de cubículo','Computadora no enciende','HeadSet', 'Impresora',
    'Inicio de sesion','Instalación de equipo','Live caption','Llamadas cortadas','Logixx',
    'Monitor sin imagen','Mouse','Movimiento agente','No internet','Página congelada',
    'Pagina no carga', 'Sheets/Docs','Sistema congelado','Slack','Teclado','Wifi',
    'Ytel congelado','Ytel delay','Ytel Interferencias','Ytel latencia','Ytel login',
    'Ytel logout','Ytel script'
]

TECHNICOS = ['Brayan', 'Hans', 'Diana', 'Ismael']

# === Normalización de cubículos (case-insensitive) ===
CUBICULOS_MAP = {c.lower(): c for c in CUBICULOS}

def canon_cubiculo(name: str):
    if not name:
        return None
    return CUBICULOS_MAP.get(name.strip().lower())

# Password fallback si aún no configuras en Ajustes (para borrar seleccionados)
ADMIN_PASS_FALLBACK = os.getenv('ADMIN_PASS', 'cambia-esto')

app = Flask(__name__)

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
# App
# ──────────────────────────────────────────────────────────────────────────────
@app.before_request
def _init():
    init_db()

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

# --- Tus rutas van aquí (idénticas a las que ya tienes) ---
# No recorto el resto por espacio, pero es tu mismo código original de rutas y lógica.

# ... [todo el bloque de rutas submit_ticket, dashboard, dashboard_table,
# process_ticket, resolve_ticket, edit_ticket, admin_delete_selected,
# admin_settings, export_tickets] ...

# ──────────────────────────────────────────────────────────────────────────────
# Entrada principal adaptada a Railway aqui tengo el problema
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)


