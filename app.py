from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER
import io, json, os, base64
import requests as req_lib
from datetime import datetime

import bcrypt
from supabase import create_client

app = Flask(__name__)
CORS(app)

# ── Supabase — SOLO para credenciales de administrador ───────────────────────
# El resto de los datos (cotizaciones, productos, empresa, eventos, usuarios
# web) sigue guardándose en GitHub exactamente igual que antes.
#
# Variables de entorno nuevas en Render:
#   SUPABASE_URL          → https://xxxxx.supabase.co
#   SUPABASE_SERVICE_KEY  → service_role key (nunca la anon/public)
SUPABASE_URL         = os.environ.get('SUPABASE_URL', '')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', '')
sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY) if SUPABASE_URL and SUPABASE_SERVICE_KEY else None


# ── GitHub como base de datos ────────────────────────────────────────────────
# Variables de entorno en Render:
#   GH_TOKEN  → GitHub Personal Access Token (repo scope)
#   GH_REPO   → usuario/repositorio  ej: sanagua/datos
#   GH_BRANCH → rama donde se guardan los datos (default: main)
#
# Los datos se guardan como archivos JSON en el repo:
#   data/counter.json   data/history.json   data/products.json
#   data/logo.json      data/empresa.json   data/events.json

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
    data, _ = _load('logo.json', {'logo': ''})
    return data.get('logo', '')

def save_logo(logo_b64):
    result = gh_read('logo.json')
    sha = result[1] if result else None
    gh_write('logo.json', {'logo': logo_b64}, sha)

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
        'auth_storage':         'Supabase (tabla admin_users)',
    })


# ── Autenticación de administradores (Supabase) ──────────────────────────────
# Reemplaza la comparación de auth.json en el navegador. Ahora cualquier
# dispositivo puede iniciar sesión llamando a este endpoint, sin necesitar
# configurar un token de GitHub localmente.
@app.route('/auth/login', methods=['POST'])
def auth_login():
    if sb is None:
        return jsonify({'error': 'Supabase no configurado en el servidor'}), 500
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    if not username or not password:
        return jsonify({'error': 'Usuario y contraseña requeridos'}), 400

    res = sb.table('admin_users').select('*').eq('username', username).limit(1).execute()
    if not res.data:
        return jsonify({'error': 'Credenciales inválidas'}), 401
    user = res.data[0]
    if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
        return jsonify({'error': 'Credenciales inválidas'}), 401

    return jsonify({
        'ok':       True,
        'username': user['username'],
        'role':     user['role'],
        'permisos': user.get('permisos', {}),
    })


@app.route('/auth/credentials', methods=['PUT'])
def auth_update_credentials():
    """Reemplaza a saveCreds() del panel (antes escribía auth.json en GitHub).
    Requiere reautenticarse con la contraseña actual del superadmin que hace
    el cambio, ya que no hay sesión/token de servidor todavía."""
    if sb is None:
        return jsonify({'error': 'Supabase no configurado en el servidor'}), 500
    data = request.get_json() or {}
    actor_username = (data.get('actor_username') or '').strip()
    actor_password = data.get('actor_password') or ''

    res = sb.table('admin_users').select('*').eq('username', actor_username).limit(1).execute()
    if not res.data or res.data[0]['role'] != 'superadmin':
        return jsonify({'error': 'Solo el super administrador puede cambiar credenciales'}), 403
    actor = res.data[0]
    if not bcrypt.checkpw(actor_password.encode('utf-8'), actor['password_hash'].encode('utf-8')):
        return jsonify({'error': 'Contraseña actual incorrecta'}), 401

    updates = data.get('updates', [])  # [{role, username?, password?}, ...]
    for u in updates:
        role = u.get('role')
        if role not in ('superadmin', 'admin'):
            continue
        row = {}
        new_username = (u.get('username') or '').strip()
        new_password = u.get('password') or ''
        if new_username:
            row['username'] = new_username
        if new_password:
            row['password_hash'] = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        if row:
            sb.table('admin_users').update(row).eq('role', role).execute()

    return jsonify({'ok': True})


@app.route('/counter')
def get_counter():
    return jsonify({'next': load_counter()})

# Productos CRUD
@app.route('/products', methods=['GET'])
def get_products():
    return jsonify(load_products())

@app.route('/products', methods=['PUT'])
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
def update_logo():
    data = request.get_json()
    save_logo(data.get('logo', ''))
    return jsonify({'ok': True})

# Empresa
@app.route('/empresa', methods=['GET'])
def get_empresa():
    return jsonify(load_empresa())

@app.route('/empresa', methods=['PUT'])
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
def update_events():
    data = request.get_json()
    if not isinstance(data, list):
        return jsonify({'error': 'Expected a list'}), 400
    save_events(data)
    return jsonify({'ok': True})

# Historial CRUD
@app.route('/history', methods=['GET'])
def get_history():
    return jsonify(load_history())

@app.route('/history/<quote_num>', methods=['PUT'])
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
def delete_quote(quote_num):
    quotes = load_history()
    quotes = [q for q in quotes if str(q.get('quote_num')) != str(quote_num)]
    save_history(quotes)
    return jsonify({'ok': True})

# Generar PDF cotización
@app.route('/generate-pdf', methods=['POST'])
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
    data, _ = _load('empresa.json', EMPRESA_DEFAULT)
    return data if data.get('nombre') else EMPRESA_DEFAULT.copy()

def save_empresa(data):
    result = gh_read('empresa.json')
    sha = result[1] if result else None
    gh_write('empresa.json', data, sha)

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
        'BRAND':      colors.HexColor('#c8541a'),
        'DARK':       colors.HexColor('#1a1814'),
        'LIGHT_GRAY': colors.HexColor('#f5f3ee'),
        'MID_GRAY':   colors.HexColor('#6b6660'),
        'GREEN':      colors.HexColor('#2d7a4f'),
        'BLUE':       colors.HexColor('#1a5fa8'),
        'PURPLE':     colors.HexColor('#6b3fa0'),
        'WHITE':      colors.white,
        'RED10':      colors.HexColor('#c62828'),
        'TEAL':       colors.HexColor('#0e7490'),
        'GOLD':       colors.HexColor('#b45309'),
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
            logo_img = Image(logo_buf, width=1.5*inch, height=0.6*inch)
            logo_img.hAlign = 'LEFT'
        except Exception:
            logo_img = None

    if logo_img:
        left_cell = Table([
            [logo_img],
            [Paragraph(f'<font color="#c8541a"><b>{company_name}</b></font>',
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
        left_cell = Paragraph(f'<font color="#c8541a"><b>{company_name}</b></font>',
                              S('cn', fontSize=18, fontName='Helvetica-Bold'))

    hdr = Table([[
        left_cell,
        Paragraph(
            f'<font size="9">{quote_label}</font><br/>'
            f'<font color="#c8541a" size="24"><b>#{quote_num}</b></font>',
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
            ('BACKGROUND',(0,len(td_list)-1),(-1,len(td_list)-1),colors.HexColor('#e8f0fa')),
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
        ('BACKGROUND',(0,len(pago_data)-1),(-1,len(pago_data)-1),colors.HexColor('#fef2e8')),
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
