from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
import uuid
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER
import io, json, os, base64
import requests as req_lib
from datetime import datetime
from functools import wraps

from supabase import create_client

# Carga variables desde .env SOLO en desarrollo local (copia .env.example a
# .env). En Render no hace nada si el archivo no existe — ahí las variables
# ya vienen inyectadas por el dashboard.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)
CORS(app)

# ── Subida de imágenes (fotos de menú/productos) al propio VPS ─────────────
# Antes las fotos se subían a un repo público de GitHub Pages; ahora se
# guardan directamente en el disco del servidor, en static/uploads/<carpeta>/,
# y Flask las sirve como archivos estáticos normales en /static/uploads/...
UPLOAD_FOLDER      = os.path.join(app.root_path, 'static', 'uploads')
ALLOWED_IMAGE_EXTS = {'jpg', 'jpeg', 'png', 'webp', 'gif'}
MAX_IMAGE_BYTES    = 6 * 1024 * 1024  # 6 MB

# ── Supabase Auth — identidad única para clientes y administradores ─────────
# El login/registro ya NO se hace comparando contraseñas a mano: todo pasa
# por auth.users de Supabase (supabase.auth.signInWithPassword / signUp en el
# frontend). Aquí, en el backend, solo VALIDAMOS el JWT que manda el cliente
# en el header Authorization y consultamos su role en public.profiles para
# decidir si puede tocar los endpoints de administración.
#
# Variables de entorno — se configuran en Render (Dashboard → Environment),
# NUNCA en este archivo ni en el repo. Ver render.yaml y .env.example.
#   SUPABASE_URL          → https://xxxxx.supabase.co
#   SUPABASE_SERVICE_KEY  → service_role key (nunca la anon/public)
SUPABASE_URL         = os.environ.get('SUPABASE_URL', '')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', '')
sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY) if SUPABASE_URL and SUPABASE_SERVICE_KEY else None


def get_authenticated_profile():
    """Valida el JWT del header Authorization contra Supabase Auth y devuelve
    el profile (con su role) del usuario autenticado, o None si no es válido.
    Nunca confía en nada que mande el cliente aparte del token en sí."""
    if sb is None:
        return None
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None
    token = auth_header.split(' ', 1)[1].strip()
    if not token:
        return None
    try:
        user_res = sb.auth.get_user(token)
        user = user_res.user
        if not user:
            return None
        prof = sb.table('profiles').select('*').eq('id', user.id).limit(1).execute()
        if not prof.data:
            return None
        return prof.data[0]
    except Exception:
        return None


def require_role(*roles):
    """Decorator: exige un JWT válido de Supabase cuyo profile.role esté en
    `roles`. Usar en TODO endpoint que escriba/borre datos administrativos —
    nunca confiar solo en que el frontend oculte el botón."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            profile = get_authenticated_profile()
            if not profile:
                return jsonify({'error': 'No autenticado'}), 401
            if profile['role'] not in roles:
                return jsonify({'error': 'No tienes permiso para esta acción'}), 403
            request.profile = profile
            return fn(*args, **kwargs)
        return wrapper
    return decorator


# ── GitHub como base de datos (legacy — la mayoría ya vive en Supabase) ─────
# Variables de entorno — se configuran en Render (Dashboard → Environment),
# NUNCA en este archivo ni en el repo. Ver render.yaml y .env.example.
#   GH_TOKEN  → GitHub Personal Access Token (repo scope)
#   GH_REPO   → usuario/repositorio  ej: sanagua/datos
#   GH_BRANCH → rama donde se guardan los datos (default: main)
#
# counter/history/events/products/logo/empresa/solicitudes ya se migraron a
# Supabase. Lo que queda en GitHub (auth.json, suscripcion.json) es del
# sistema de credenciales/bloqueo previo a Supabase Auth.

GH_TOKEN  = os.environ.get('GH_TOKEN', '')
GH_REPO   = os.environ.get('GH_REPO', '')
GH_BRANCH = os.environ.get('GH_BRANCH', 'main')
GH_BASE   = 'https://api.github.com'

def gh_headers():
    return {
        'Authorization': f'token {GH_TOKEN}',
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json',
    }

def gh_read(filename):
    """Lee un archivo JSON del repo de GitHub en Data/json/."""
    if not GH_TOKEN or not GH_REPO:
        return None
    try:
        url = f'{GH_BASE}/repos/{GH_REPO}/contents/Data/json/{filename}?ref={GH_BRANCH}'
        r = req_lib.get(url, headers=gh_headers(), timeout=8)
        if r.status_code == 404:
            return None
        d = r.json()
        import base64 as b64mod
        content = b64mod.b64decode(d['content']).decode('utf-8')
        return json.loads(content), d['sha']
    except:
        return None

def gh_write(filename, data, sha=None):
    """Escribe un archivo JSON en el repo de GitHub en Data/json/."""
    if not GH_TOKEN or not GH_REPO:
        return False
    try:
        import base64 as b64mod
        content = b64mod.b64encode(json.dumps(data, ensure_ascii=False, indent=2).encode()).decode()
        payload = {
            'message': f'update {filename}',
            'content': content,
            'branch': GH_BRANCH,
        }
        if sha:
            payload['sha'] = sha
        url = f'{GH_BASE}/repos/{GH_REPO}/contents/Data/json/{filename}'
        r = req_lib.put(url, headers=gh_headers(), json=payload, timeout=10)
        return r.status_code in (200, 201)
    except:
        return False

def _load(filename, default):
    result = gh_read(filename)
    if result is None:
        return default, None
    data, sha = result
    return data, sha

# ── Contador ───────────────────────────────────────────────────────────────────
def load_counter():
    data, _ = _load('counter.json', {'count': 1})
    return data.get('count', 1)

def save_counter(n):
    result = gh_read('counter.json')
    sha = result[1] if result else None
    gh_write('counter.json', {'count': n}, sha)

# ── Historial ──────────────────────────────────────────────────────────────────
def load_history():
    data, _ = _load('history.json', {'quotes': []})
    return data.get('quotes', [])

def save_history(quotes):
    result = gh_read('history.json')
    sha = result[1] if result else None
    gh_write('history.json', {'quotes': quotes}, sha)

# ── Productos ──────────────────────────────────────────────────────────────────
PRODUCTOS_DEFAULT = [
    {'id': 1, 'name': 'Cabaña Sencilla (noche)',  'price': 120.00, 'itbms': 7},
    {'id': 2, 'name': 'Cabaña Doble (noche)',     'price': 180.00, 'itbms': 7},
    {'id': 3, 'name': 'Cabaña Familiar (noche)',  'price': 240.00, 'itbms': 7},
    {'id': 4, 'name': 'Paquete con alimentación', 'price': 350.00, 'itbms': 7},
]

def load_products():
    data, _ = _load('products.json', {'products': []})
    prods = data.get('products', [])
    return prods if prods else PRODUCTOS_DEFAULT

def save_products(products):
    result = gh_read('products.json')
    sha = result[1] if result else None
    gh_write('products.json', {'products': products}, sha)

# ── Logo ───────────────────────────────────────────────────────────────────────
def load_logo():
    if sb is None:
        return ''
    try:
        res = sb.table('company_settings').select('value').eq('key', 'logo').limit(1).execute()
        if res.data:
            return res.data[0]['value'].get('logo', '')
    except Exception as e:
        print('load_logo error:', e)
    return ''

def save_logo(logo_b64):
    if sb is None:
        return
    sb.table('company_settings').upsert({'key': 'logo', 'value': {'logo': logo_b64}}).execute()

# ── Rutas ──────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return jsonify({'status': 'ok', 'service': 'Cotizaciones Sanagua Lodge'})

@app.route('/debug')
def debug():
    return jsonify({
        'GH_TOKEN':             '✅ configurado' if GH_TOKEN  else '❌ FALTA',
        'GH_REPO':              GH_REPO  or '❌ FALTA',
        'GH_BRANCH':            GH_BRANCH,
        'storage':              'GitHub API',
        'SUPABASE_URL':         '✅ configurado' if SUPABASE_URL else '❌ FALTA',
        'SUPABASE_SERVICE_KEY': '✅ configurado' if SUPABASE_SERVICE_KEY else '❌ FALTA',
        'auth_storage':         'Supabase Auth (auth.users + public.profiles)',
    })


# ── Autenticación (Supabase Auth) ────────────────────────────────────────────
# El login/registro real ocurre en el navegador con supabase-js
# (auth.signInWithPassword / auth.signUp) contra auth.users. El backend ya no
# recibe ni compara contraseñas: solo valida el JWT resultante.

@app.route('/auth/me', methods=['GET'])
def auth_me():
    """Confirma, del lado del servidor, quién es el usuario del token actual
    y qué role tiene. Lo usan las páginas de sanagua-cot como segunda
    verificación (además de la sesión de Supabase en el navegador) antes de
    confiar en que alguien es admin."""
    profile = get_authenticated_profile()
    if not profile:
        return jsonify({'error': 'No autenticado'}), 401
    return jsonify({
        'id':       profile['id'],
        'email':    profile['email'],
        'name':     profile.get('name', ''),
        'role':     profile['role'],
        'permisos': profile.get('permisos', {}),
    })


@app.route('/auth/admins', methods=['GET'])
@require_role('superadmin')
def auth_list_admins():
    """Lista todos los administradores (para el panel de permisos)."""
    res = sb.table('profiles').select('id, email, name, role, permisos').in_('role', ['admin', 'superadmin']).execute()
    return jsonify(res.data or [])


@app.route('/auth/admins', methods=['POST'])
@require_role('superadmin')
def auth_create_admin():
    """Crea un nuevo administrador directamente en Supabase Auth (reemplaza
    el viejo flujo de escribir un hash bcrypt en admin_users). Solo puede
    invocarlo alguien ya autenticado como superadmin."""
    if sb is None:
        return jsonify({'error': 'Supabase no configurado en el servidor'}), 500
    data = request.get_json() or {}
    email    = (data.get('email') or '').strip()
    name     = (data.get('name') or '').strip()
    password = data.get('password') or ''
    role     = data.get('role') or 'admin'
    if role not in ('admin', 'superadmin'):
        return jsonify({'error': 'Role inválido'}), 400
    if not email or not password or len(password) < 6:
        return jsonify({'error': 'Email y contraseña (mín. 6 caracteres) requeridos'}), 400

    try:
        created = sb.auth.admin.create_user({
            'email': email,
            'password': password,
            'email_confirm': True,
            'user_metadata': {'name': name, 'role': role},
        })
        return jsonify({'ok': True, 'id': created.user.id, 'email': email, 'role': role})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/auth/admins/<user_id>/role', methods=['PUT'])
@require_role('superadmin')
def auth_update_admin_role(user_id):
    """Cambia el role/permisos de un admin existente. Solo superadmin."""
    if sb is None:
        return jsonify({'error': 'Supabase no configurado en el servidor'}), 500
    data = request.get_json() or {}
    updates = {}
    if data.get('role') in ('admin', 'superadmin', 'cliente'):
        updates['role'] = data['role']
    if 'permisos' in data:
        updates['permisos'] = data['permisos']
    if not updates:
        return jsonify({'error': 'Nada que actualizar'}), 400
    sb.table('profiles').update(updates).eq('id', user_id).execute()
    return jsonify({'ok': True})


@app.route('/counter')
def get_counter():
    return jsonify({'next': load_counter()})

# Productos CRUD
@app.route('/products', methods=['GET'])
def get_products():
    return jsonify(load_products())

@app.route('/products', methods=['PUT'])
@require_role('admin', 'superadmin')
def update_products():
    products = request.get_json()
    if not isinstance(products, list):
        return jsonify({'error': 'Expected a list of products'}), 400
    save_products(products)
    return jsonify({'ok': True, 'count': len(products)})

# Logo
@app.route('/logo', methods=['GET'])
def get_logo():
    return jsonify({'logo': load_logo()})

@app.route('/logo', methods=['PUT'])
@require_role('admin', 'superadmin')
def update_logo():
    data = request.get_json()
    save_logo(data.get('logo', ''))
    return jsonify({'ok': True})

# ── Subida de imágenes ────────────────────────────────────────────────────
# El frontend manda un multipart/form-data con el archivo en 'file' y,
# opcionalmente, un campo 'folder' (ej. 'restaurante', 'servicios') para
# organizar las imágenes por sección. Devuelve la URL pública relativa
# (ej. /static/uploads/restaurante/xxxxx.jpg) para guardar en Supabase.
@app.route('/upload-image', methods=['POST'])
@require_role('admin', 'superadmin')
def upload_image():
    if 'file' not in request.files:
        return jsonify({'error': 'No se envió ningún archivo (campo "file")'}), 400
    file = request.files['file']
    if not file or not file.filename:
        return jsonify({'error': 'Archivo vacío'}), 400

    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in ALLOWED_IMAGE_EXTS:
        return jsonify({'error': f'Formato no permitido (.{ext}). Usa: ' + ', '.join(sorted(ALLOWED_IMAGE_EXTS))}), 400

    # Límite de tamaño (Flask ya leyó el stream a memoria/temp; medimos aquí)
    file.stream.seek(0, os.SEEK_END)
    size = file.stream.tell()
    file.stream.seek(0)
    if size > MAX_IMAGE_BYTES:
        return jsonify({'error': f'La imagen supera {MAX_IMAGE_BYTES // (1024*1024)} MB'}), 400

    # Subcarpeta opcional (saneada para evitar path traversal)
    folder = secure_filename(request.form.get('folder', 'general')) or 'general'
    dest_dir = os.path.join(UPLOAD_FOLDER, folder)
    os.makedirs(dest_dir, exist_ok=True)

    filename = f"{uuid.uuid4().hex}.{ext}"
    file.save(os.path.join(dest_dir, filename))

    url = f"/static/uploads/{folder}/{filename}"
    return jsonify({'ok': True, 'url': url})

# Foto de cédula/pasaporte del cliente al registrarse. A diferencia de
# /upload-image (solo admin), aquí basta con estar autenticado — el cliente
# sube la foto de SU PROPIO documento durante el registro.
@app.route('/upload-document', methods=['POST'])
def upload_document():
    profile = get_authenticated_profile()
    if not profile:
        return jsonify({'error': 'No autenticado'}), 401
    if 'file' not in request.files:
        return jsonify({'error': 'No se envió ningún archivo (campo "file")'}), 400
    file = request.files['file']
    if not file or not file.filename:
        return jsonify({'error': 'Archivo vacío'}), 400

    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in ALLOWED_IMAGE_EXTS:
        return jsonify({'error': f'Formato no permitido (.{ext}). Usa: ' + ', '.join(sorted(ALLOWED_IMAGE_EXTS))}), 400

    file.stream.seek(0, os.SEEK_END)
    size = file.stream.tell()
    file.stream.seek(0)
    if size > MAX_IMAGE_BYTES:
        return jsonify({'error': f'La imagen supera {MAX_IMAGE_BYTES // (1024*1024)} MB'}), 400

    # Cada cliente sube a su propia subcarpeta (por su user id) — evita
    # colisiones de nombre y facilita borrar los documentos de alguien si
    # cierra su cuenta.
    dest_dir = os.path.join(UPLOAD_FOLDER, 'documentos', profile['id'])
    os.makedirs(dest_dir, exist_ok=True)

    filename = f"{uuid.uuid4().hex}.{ext}"
    file.save(os.path.join(dest_dir, filename))

    url = f"/static/uploads/documentos/{profile['id']}/{filename}"
    return jsonify({'ok': True, 'url': url})

# Empresa
@app.route('/empresa', methods=['GET'])
def get_empresa():
    return jsonify(load_empresa())

@app.route('/empresa', methods=['PUT'])
@require_role('admin', 'superadmin')
def update_empresa():
    data = request.get_json()
    if not data or not data.get('nombre'):
        return jsonify({'error': 'nombre requerido'}), 400
    save_empresa(data)
    return jsonify({'ok': True})

# Eventos manuales
@app.route('/events', methods=['GET'])
def get_events():
    return jsonify(load_events())

@app.route('/events', methods=['PUT'])
@require_role('admin', 'superadmin')
def update_events():
    data = request.get_json()
    if not isinstance(data, list):
        return jsonify({'error': 'Expected a list'}), 400
    save_events(data)
    return jsonify({'ok': True})

# Historial CRUD
@app.route('/history', methods=['GET'])
@require_role('admin', 'superadmin')
def get_history():
    return jsonify(load_history())

@app.route('/history/<quote_num>', methods=['PUT'])
@require_role('admin', 'superadmin')
def update_quote(quote_num):
    data = request.get_json()
    quotes = load_history()
    for i, q in enumerate(quotes):
        if str(q.get('quote_num')) == str(quote_num):
            quotes[i].update(data)
            quotes[i]['updated_at'] = datetime.now().isoformat()
            save_history(quotes)
            return jsonify({'ok': True, 'quote': quotes[i]})
    return jsonify({'error': 'Not found'}), 404

@app.route('/history/<quote_num>', methods=['DELETE'])
@require_role('admin', 'superadmin')
def delete_quote(quote_num):
    quotes = load_history()
    quotes = [q for q in quotes if str(q.get('quote_num')) != str(quote_num)]
    save_history(quotes)
    return jsonify({'ok': True})

# Generar PDF cotización
@app.route('/generate-pdf', methods=['POST'])
@require_role('admin', 'superadmin')
def generate_pdf():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    quote_num = load_counter()
    save_counter(quote_num + 1)
    quote_str = str(quote_num).zfill(4)

    # Guardar en historial — excluir logo y empresa para no inflar el bin
    record_data = {k: v for k, v in data.items() if k not in ('logo', 'empresa')}
    record = {**record_data, 'quote_num': quote_str,
              'created_at': datetime.now().isoformat(),
              'updated_at': datetime.now().isoformat(),
              'abono_pagado': 0, 'estado': 'Pendiente', 'notas_internas': ''}
    quotes = load_history()
    quotes.append(record)
    # Mantener orden por created_at descendente
    quotes.sort(key=lambda q: q.get('created_at',''), reverse=True)
    save_history(quotes)

    buffer = io.BytesIO()
    _build_quote_pdf(buffer, data, quote_str)
    buffer.seek(0)

    response = send_file(buffer, mimetype='application/pdf', as_attachment=True,
                         download_name=f'Cotización Sanagua Lodge #{quote_str}.pdf')
    response.headers['X-Quote-Number'] = quote_str
    response.headers['Access-Control-Expose-Headers'] = 'X-Quote-Number'
    return response

# Generar PDF confirmación de reserva
@app.route('/regenerate-pdf', methods=['POST'])
@require_role('admin', 'superadmin')
def regenerate_pdf():
    """Regenera el PDF de una cotización existente sin cambiar el contador ni el historial."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    quote_num = str(data.get('quote_num', '0000')).zfill(4)
    buffer = io.BytesIO()
    _build_quote_pdf(buffer, data, quote_num)
    buffer.seek(0)
    return send_file(buffer, mimetype='application/pdf', as_attachment=True,
                     download_name=f'Cotización Sanagua Lodge #{quote_num}.pdf')


@app.route('/generate-confirmation', methods=['POST'])
def generate_confirmation():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    quote_str = str(data.get('quote_num', '0000')).zfill(4)
    client_name = data.get('client', {}).get('name', 'Cliente')

    buffer = io.BytesIO()
    _build_confirmation_pdf(buffer, data, quote_str)
    buffer.seek(0)

    filename = f'Confirmación Sanagua Lodge {quote_str} {client_name}.pdf'
    response = send_file(buffer, mimetype='application/pdf', as_attachment=True,
                         download_name=filename)
    response.headers['Access-Control-Expose-Headers'] = 'X-Quote-Number'
    return response


# ── Empresa ───────────────────────────────────────────────────────────────────
EMPRESA_DEFAULT = {
    'nombre': 'Sanagua Lodge S.A.',
    'ruc':    '155761744-2-2025',
    'tel':    '+507 6166-0114',
    'email':  'sanagualodge@gmail.com',
}

def load_empresa():
    if sb is None:
        return EMPRESA_DEFAULT.copy()
    try:
        res = sb.table('company_settings').select('value').eq('key', 'empresa').limit(1).execute()
        if res.data and res.data[0]['value'].get('nombre'):
            return res.data[0]['value']
    except Exception as e:
        print('load_empresa error:', e)
    return EMPRESA_DEFAULT.copy()

def save_empresa(data):
    if sb is None:
        return
    sb.table('company_settings').upsert({'key': 'empresa', 'value': data}).execute()

# ── Eventos manuales ───────────────────────────────────────────────────────────
def load_events():
    data, _ = _load('events.json', {'events': []})
    return data.get('events', [])

def save_events(events):
    result = gh_read('events.json')
    sha = result[1] if result else None
    gh_write('events.json', {'events': events}, sha)

# ── HELPERS COMPARTIDOS ────────────────────────────────────────────────────────
# Los datos de empresa vienen del payload (editables desde la UI)
# Estos son los valores por defecto si no vienen en el payload
_COMPANY_DEFAULTS = {
    'nombre': 'Sanagua Lodge S.A.',
    'ruc':    '155761744-2-2025',
    'tel':    '+507 6166-0114',
    'email':  'sanagualodge@gmail.com',
}

def _get_company(data):
    """Devuelve datos de empresa desde el payload o usa defaults."""
    emp = data.get('empresa') or {}
    return {
        'nombre': emp.get('nombre') or _COMPANY_DEFAULTS['nombre'],
        'ruc':    emp.get('ruc')    or _COMPANY_DEFAULTS['ruc'],
        'tel':    emp.get('tel')    or _COMPANY_DEFAULTS['tel'],
        'email':  emp.get('email')  or _COMPANY_DEFAULTS['email'],
    }

def _colors():
    return {
        'BRAND':      colors.HexColor('#7fa0ac'),  # Pantone 2177 C — color insignia
        'DARK':       colors.HexColor('#1a2226'),
        'LIGHT_GRAY': colors.HexColor('#f5f3ee'),
        'MID_GRAY':   colors.HexColor('#6b6670'),
        'GREEN':      colors.HexColor('#2d7a4f'),  # éxito / descuentos — se deja igual a propósito
        'BLUE':       colors.HexColor('#566d75'),  # tono oscuro de la misma familia del insignia
        'PURPLE':     colors.HexColor('#5f7881'),
        'WHITE':      colors.white,
        'RED10':      colors.HexColor('#c0392b'),
        'TEAL':       colors.HexColor('#4d6b75'),
        'GOLD':       colors.HexColor('#c9a84c'),
    }

def S(name, **kw):
    return ParagraphStyle(name, parent=getSampleStyleSheet()['Normal'], **kw)

def _fmt_date(d):
    try:
        dt = datetime.strptime(d, '%Y-%m-%d')
        meses = ['enero','febrero','marzo','abril','mayo','junio',
                 'julio','agosto','septiembre','octubre','noviembre','diciembre']
        return f"{dt.day} de {meses[dt.month-1]} de {dt.year}"
    except:
        return d or '—'

def _header_block(story, W, C, quote_label, quote_num, logo_b64=None, empresa=None):
    emp = empresa or _COMPANY_DEFAULTS
    company_name  = emp.get('nombre', _COMPANY_DEFAULTS['nombre'])
    company_ruc   = f"RUC: {emp.get('ruc', _COMPANY_DEFAULTS['ruc'])}"
    company_tel   = f"Tel: {emp.get('tel', _COMPANY_DEFAULTS['tel'])}"
    company_email = emp.get('email', _COMPANY_DEFAULTS['email'])
    logo_img = None
    if logo_b64:
        try:
            # Quitar el prefijo data:image/...;base64,
            if ',' in logo_b64:
                logo_b64 = logo_b64.split(',', 1)[1]
            logo_bytes = base64.b64decode(logo_b64)
            logo_buf = io.BytesIO(logo_bytes)

            # Calcular el tamaño real del logo para no deformarlo: lo
            # encajamos dentro de una caja máxima (1.5in x 0.6in)
            # respetando su proporción original.
            max_w, max_h = 1.5 * inch, 0.6 * inch
            try:
                from PIL import Image as PILImage
                logo_buf.seek(0)
                with PILImage.open(logo_buf) as im:
                    orig_w, orig_h = im.size
                logo_buf.seek(0)
                escala = min(max_w / orig_w, max_h / orig_h)
                draw_w, draw_h = orig_w * escala, orig_h * escala
            except Exception:
                draw_w, draw_h = max_w, max_h  # si PIL no puede leerlo, usar la caja completa

            logo_img = Image(logo_buf, width=draw_w, height=draw_h)
            logo_img.hAlign = 'LEFT'
        except Exception:
            logo_img = None

    if logo_img:
        left_cell = Table([
            [logo_img],
            [Paragraph(f'<font color="#7fa0ac"><b>{company_name}</b></font>',
                       S('cn', fontSize=14, fontName='Helvetica-Bold'))]
        ], colWidths=[W*0.6])
        left_cell.setStyle(TableStyle([
            ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
            ('LEFTPADDING',(0,0),(-1,-1),0),
            ('RIGHTPADDING',(0,0),(-1,-1),0),
            ('TOPPADDING',(0,0),(-1,-1),2),
            ('BOTTOMPADDING',(0,0),(-1,-1),2),
        ]))
    else:
        left_cell = Paragraph(f'<font color="#7fa0ac"><b>{company_name}</b></font>',
                              S('cn', fontSize=18, fontName='Helvetica-Bold'))

    hdr = Table([[
        left_cell,
        Paragraph(
            f'<font size="9">{quote_label}</font><br/>'
            f'<font color="#7fa0ac" size="24"><b>#{quote_num}</b></font>',
            S('qn', fontSize=9, alignment=TA_RIGHT, leading=28)
        )
    ]], colWidths=[W*0.6, W*0.4])
    hdr.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE')]))
    story.append(hdr)
    story.append(Spacer(1,4))
    story.append(Paragraph(f'{company_ruc} | {company_tel} | {company_email}',
                            S('si', fontSize=8, textColor=C['MID_GRAY'])))
    story.append(Spacer(1,6))
    story.append(HRFlowable(width=W, thickness=2, color=C['BRAND']))
    story.append(Spacer(1,12))

def _client_block(story, W, C, data):
    client   = data.get('client', {})
    date_str = _fmt_date(data.get('date',''))
    valid_str= _fmt_date(data.get('valid_until',''))
    left = '<br/>'.join([
        f"<b>Cliente:</b> {client.get('name','—')}",
        f"<b>RUC/Cédula:</b> {client.get('ruc','—')}",
        f"<b>Correo:</b> {client.get('email','—')}",
        f"<b>Teléfono:</b> {client.get('phone','—')}",
        f"<b>Dirección:</b> {client.get('address','—')}",
    ])
    visit_str = _fmt_date(data.get('visit_date',''))
    categoria = data.get('categoria','')
    right_lines = [
        f"<b>Fecha:</b> {date_str}",
        f"<b>Válida hasta:</b> {valid_str}",
    ]
    if visit_str and visit_str != '—':
        right_lines.append(f"<b>Fecha de visita:</b> {visit_str}")
    if categoria:
        right_lines.append(f"<b>Categoría:</b> {categoria}")
    right = '<br/>'.join(right_lines)
    ct = Table([[
        Paragraph(left,  S('cl', fontSize=9, leading=14)),
        Paragraph(right, S('cr', fontSize=9, leading=14, alignment=TA_RIGHT))
    ]], colWidths=[W*0.6, W*0.4])
    ct.setStyle(TableStyle([
        ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('BACKGROUND',(0,0),(-1,-1), C['LIGHT_GRAY']),
        ('BOX',(0,0),(-1,-1),0.5, colors.HexColor('#e0dbd4')),
        ('PADDING',(0,0),(-1,-1),10),
    ]))
    story.append(ct)
    story.append(Spacer(1,16))
    return valid_str

def _items_block(story, W, C, data):
    disc_amount = data.get('discount_amount', 0)
    disc_label  = data.get('discount_label')

    # Banner solo si hay descuentos aplicados
    if disc_amount and disc_amount > 0:
        bt = Table([[Paragraph(
            f'<font color="white"><b>🏷 {disc_label or "Descuentos aplicados"} — ver detalle por ítem</b></font>',
            S('bn', fontSize=9, textColor=C['WHITE'])
        )]], colWidths=[W])
        bt.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),C['BLUE']),('PADDING',(0,0),(-1,-1),8)]))
        story.append(bt)
        story.append(Spacer(1,10))

    def th(txt, align=TA_CENTER):
        return Paragraph(f'<b>{txt}</b>', S('th', fontSize=8, textColor=C['WHITE'], alignment=align))
    def td(txt, align=TA_LEFT, bold=False, color=None):
        style = S('td', fontSize=8.5, alignment=align, textColor=color or C['DARK'])
        return Paragraph(f'<b>{txt}</b>' if bold else txt, style)

    # Detectar si algún ítem tiene descuento para mostrar la columna
    items_list = data.get('items', [])
    any_disc = any(it.get('disc_pct', 0) > 0 for it in items_list)

    if any_disc:
        col_w = [W*0.30, W*0.06, W*0.11, W*0.13, W*0.09, W*0.11, W*0.20]
        rows = [[th('Descripción',TA_LEFT), th('Cant.'), th('P. Unit.'),
                 th('Descuento'), th('ITBMS'), th('Monto ITBMS'), th('Total')]]
        for it in items_list:
            pct_itbms = it.get('itbms_pct', 0)
            disc_pct_it = it.get('disc_pct', 0)
            disc_lbl_it = it.get('disc_label') or ''
            disc_line   = it.get('line_discount', 0)
            disc_cell = f'{disc_lbl_it}\n−${disc_line:.2f}' if disc_pct_it > 0 else '—'
            rows.append([
                td(it.get('desc','')),
                td(str(it.get('qty',1)), TA_CENTER),
                td(f"${it.get('price',0):.2f}", TA_RIGHT),
                td(disc_cell, TA_CENTER, color=C['GREEN'] if disc_pct_it>0 else C['MID_GRAY']),
                td(f'{pct_itbms}%' if pct_itbms else 'Sin', TA_CENTER),
                td(f"${it.get('itbms_amount',0):.2f}", TA_RIGHT),
                td(f"${it.get('line_total',0):.2f}", TA_RIGHT, bold=True),
            ])
    else:
        col_w = [W*0.35, W*0.07, W*0.13, W*0.09, W*0.13, W*0.23]
        rows = [[th('Descripción',TA_LEFT), th('Cant.'), th('P. Unitario'),
                 th('ITBMS'), th('Monto ITBMS'), th('Total')]]
        for it in items_list:
            pct = it.get('itbms_pct', 0)
            rows.append([
                td(it.get('desc','')),
                td(str(it.get('qty',1)), TA_CENTER),
                td(f"${it.get('price',0):.2f}", TA_RIGHT),
                td(f'{pct}%' if pct else 'Sin', TA_CENTER),
                td(f"${it.get('itbms_amount',0):.2f}", TA_RIGHT),
                td(f"${it.get('line_total',0):.2f}", TA_RIGHT, bold=True),
            ])

    tbl = Table(rows, colWidths=col_w, repeatRows=1)
    tbl.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0), C['DARK']),
        ('TEXTCOLOR',(0,0),(-1,0), C['WHITE']),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[C['WHITE'], C['LIGHT_GRAY']]),
        ('GRID',(0,0),(-1,-1),0.4,colors.HexColor('#e0dbd4')),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),
        ('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),
    ]))
    story.append(tbl)
    story.append(Spacer(1,12))

def _totals_block(story, W, C, data, show_abono=True):
    subtotal      = data.get('subtotal', 0)
    base_after    = data.get('base_after_discount', subtotal)
    itbms7        = data.get('itbms7_total', 0)
    itbms10       = data.get('itbms10_total', 0)
    total         = data.get('total', 0)
    abono_50      = data.get('abono_50', total * 0.5)
    disc_pct      = data.get('discount_pct', 0)
    disc_label    = data.get('discount_label')
    disc_amount   = data.get('discount_amount', 0)
    has_7         = any(it.get('itbms_pct')==7  for it in data.get('items',[]))
    has_10        = any(it.get('itbms_pct')==10 for it in data.get('items',[]))

    def tot_row(label, amount, color=None, bold=False, size=9):
        color = color or C['MID_GRAY']
        lbl = f'<b>{label}</b>' if bold else label
        amt = f'<b>{amount}</b>' if bold else amount
        return [
            Paragraph('', S('x')),
            Paragraph(lbl, S('tl', fontSize=size, alignment=TA_RIGHT, textColor=color)),
            Paragraph(amt, S('tr', fontSize=size, alignment=TA_RIGHT, textColor=color)),
        ]

    td_list = [tot_row('Subtotal (sin impuestos):', f'${subtotal:.2f}')]
    if disc_amount and disc_amount > 0:
        td_list.append(tot_row(f'{disc_label or "Descuentos aplicados"}:', f'−${disc_amount:.2f}', C['GREEN']))
        td_list.append(tot_row('Base gravable:', f'${base_after:.2f}'))
    if itbms7 > 0 or has_7:
        td_list.append(tot_row('ITBMS 7%:', f'${itbms7:.2f}'))
    if itbms10 > 0 or has_10:
        td_list.append(tot_row('ITBMS 10%:', f'${itbms10:.2f}', C['RED10']))
    td_list.append(tot_row('TOTAL:', f'${total:.2f}', C['BRAND'], bold=True, size=11))
    if show_abono:
        td_list.append(tot_row('Abono requerido (50%):', f'${abono_50:.2f}', C['BLUE'], bold=True, size=10))

    tc = [W*0.52, W*0.28, W*0.20]
    tot_table = Table(td_list, colWidths=tc)
    ts = [
        ('LINEABOVE',(1,len(td_list)-2),(-1,len(td_list)-2),1.5,C['BRAND']),
        ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
        ('RIGHTPADDING',(0,0),(-1,-1),4),
    ]
    if show_abono:
        ts += [
            ('LINEABOVE',(1,len(td_list)-1),(-1,len(td_list)-1),0.5,C['BLUE']),
            ('BACKGROUND',(0,len(td_list)-1),(-1,len(td_list)-1),colors.HexColor('#eef4f5')),
        ]
    tot_table.setStyle(TableStyle(ts))
    story.append(tot_table)


# ── PDF COTIZACIÓN ─────────────────────────────────────────────────────────────
def _build_quote_pdf(buffer, data, quote_num):
    C = _colors()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
        leftMargin=0.75*inch, rightMargin=0.75*inch,
        topMargin=0.6*inch, bottomMargin=0.7*inch)
    W = letter[0] - 1.5*inch
    story = []

    _header_block(story, W, C, 'Cotización Sanagua Lodge', quote_num,
                  logo_b64=data.get('logo'), empresa=_get_company(data))
    valid_str = _client_block(story, W, C, data)
    _items_block(story, W, C, data)
    _totals_block(story, W, C, data, show_abono=True)

    notes = data.get('notes','').strip()
    if notes:
        story.append(Spacer(1,16))
        story.append(HRFlowable(width=W, thickness=0.5, color=colors.HexColor('#e0dbd4')))
        story.append(Spacer(1,8))
        story.append(Paragraph('<b>Notas y Condiciones:</b>', S('nt', fontSize=9, textColor=C['MID_GRAY'])))
        story.append(Spacer(1,4))
        for line in notes.split('\n'):
            if line.strip():
                story.append(Paragraph(line.strip(), S('nb', fontSize=9, textColor=C['DARK'], leading=14)))
            else:
                story.append(Spacer(1,5))

    story.append(Spacer(1,20))
    story.append(HRFlowable(width=W, thickness=0.5, color=colors.HexColor('#e0dbd4')))
    story.append(Spacer(1,6))
    story.append(Paragraph(
        f'Esta cotización es válida hasta el {valid_str}. Gracias por su confianza en {_get_company(data)["nombre"]}.',
        S('ft', fontSize=7.5, textColor=C['MID_GRAY'], alignment=TA_CENTER)
    ))
    doc.build(story)


# ── PDF CONFIRMACIÓN DE RESERVA ────────────────────────────────────────────────
def _build_confirmation_pdf(buffer, data, quote_num):
    C = _colors()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
        leftMargin=0.75*inch, rightMargin=0.75*inch,
        topMargin=0.6*inch, bottomMargin=0.7*inch)
    W = letter[0] - 1.5*inch
    story = []

    # Encabezado con etiqueta diferente
    _header_block(story, W, C, 'Confirmación de Reserva', quote_num,
                  logo_b64=data.get('logo'), empresa=_get_company(data))

    # Banner verde de confirmación
    banner = Table([[Paragraph(
        '<font color="white"><b>✅  RESERVA CONFIRMADA</b></font>',
        S('cb', fontSize=11, textColor=C['WHITE'], alignment=TA_CENTER)
    )]], colWidths=[W])
    banner.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1), C['GREEN']),
        ('PADDING',(0,0),(-1,-1),10),
    ]))
    story.append(banner)
    story.append(Spacer(1,14))

    valid_str = _client_block(story, W, C, data)
    _items_block(story, W, C, data)

    # Totales sin abono 50% (ya lo pagaron)
    _totals_block(story, W, C, data, show_abono=False)

    # ── RESUMEN DE PAGO ────────────────────────────────────────────────────────
    total      = data.get('total', 0)
    abono_50   = data.get('abono_50', total * 0.5)
    abono_pago = float(data.get('abono_pagado', 0))
    saldo      = total - abono_pago

    story.append(Spacer(1,16))
    story.append(HRFlowable(width=W, thickness=1, color=C['GREEN']))
    story.append(Spacer(1,8))
    story.append(Paragraph('<b>Resumen de Pago</b>', S('rp', fontSize=10, textColor=C['GREEN'])))
    story.append(Spacer(1,8))

    pago_data = [
        [Paragraph('<b>Concepto</b>', S('ph', fontSize=8.5, textColor=C['WHITE'])),
         Paragraph('<b>Monto</b>',    S('ph', fontSize=8.5, textColor=C['WHITE'], alignment=TA_RIGHT))],
        [Paragraph('Total de la reserva',   S('pd', fontSize=9)),
         Paragraph(f'<b>${total:.2f}</b>',   S('pd', fontSize=9, alignment=TA_RIGHT))],
        [Paragraph('Abono requerido (50%)', S('pd', fontSize=9, textColor=C['BLUE'])),
         Paragraph(f'${abono_50:.2f}',       S('pd', fontSize=9, alignment=TA_RIGHT, textColor=C['BLUE']))],
        [Paragraph('<b>Abono recibido</b>', S('pd', fontSize=9, textColor=C['GREEN'])),
         Paragraph(f'<b>${abono_pago:.2f}</b>', S('pd', fontSize=9, alignment=TA_RIGHT, textColor=C['GREEN']))],
        [Paragraph('<b>Saldo pendiente</b>', S('pd', fontSize=10, textColor=C['BRAND'])),
         Paragraph(f'<b>${saldo:.2f}</b>',    S('pd', fontSize=10, alignment=TA_RIGHT, textColor=C['BRAND']))],
    ]

    pago_table = Table(pago_data, colWidths=[W*0.65, W*0.35])
    pago_table.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0), C['DARK']),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[C['WHITE'], C['LIGHT_GRAY']]),
        ('GRID',(0,0),(-1,-1),0.4,colors.HexColor('#e0dbd4')),
        ('LINEABOVE',(0,len(pago_data)-1),(-1,len(pago_data)-1),1.5,C['BRAND']),
        ('BACKGROUND',(0,len(pago_data)-1),(-1,len(pago_data)-1),colors.HexColor('#f0f5f6')),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),
        ('LEFTPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),10),
    ]))
    story.append(pago_table)

    # Solo notas internas en la confirmación (sin condiciones de cotización)
    notas_internas = data.get('notas_internas','').strip()
    if notas_internas:
        story.append(Spacer(1,16))
        story.append(HRFlowable(width=W, thickness=0.5, color=colors.HexColor('#e0dbd4')))
        story.append(Spacer(1,8))
        story.append(Paragraph('<b>Observaciones:</b>', S('ni', fontSize=9, textColor=C['MID_GRAY'])))
        story.append(Spacer(1,4))
        for line in notas_internas.split('\n'):
            if line.strip():
                story.append(Paragraph(line.strip(), S('nib', fontSize=9, textColor=C['DARK'], leading=14)))
            else:
                story.append(Spacer(1,5))

    # Pie
    story.append(Spacer(1,20))
    story.append(HRFlowable(width=W, thickness=0.5, color=colors.HexColor('#e0dbd4')))
    story.append(Spacer(1,6))
    story.append(Paragraph(
        f'Gracias por elegir {_get_company(data)["nombre"]}. ¡Esperamos recibirle pronto!',
        S('ft', fontSize=7.5, textColor=C['MID_GRAY'], alignment=TA_CENTER)
    ))
    doc.build(story)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
