from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER
import io, json, os
import requests as req_lib
from datetime import datetime

app = Flask(__name__)
CORS(app)

# ── JSONBin.io — contador + historial ─────────────────────────────────────────
# Variables de entorno en Render:
#   JSONBIN_API_KEY  → tu Master Key de jsonbin.io
#   JSONBIN_BIN_ID   → bin para el contador  {"count": 1}
#   JSONBIN_HIST_ID  → bin para el historial {"quotes": []}
JSONBIN_API_KEY = os.environ.get('$2a$10$f9n49LwCyy1dMgX1P21vTuggE/.KPTac3RbdfxvqbzYy7KfixWeMy', '')
JSONBIN_BIN_ID  = os.environ.get('69fa0a37aaba8821977460d0', '')
JSONBIN_HIST_ID = os.environ.get('69fd166bc0954111d8f0a841', '')
JSONBIN_BASE    = 'https://api.jsonbin.io/v3/b'

HEADERS_R = {'X-Master-Key': JSONBIN_API_KEY}
HEADERS_W = {'X-Master-Key': JSONBIN_API_KEY, 'Content-Type': 'application/json'}

# ── Contador ───────────────────────────────────────────────────────────────────
def load_counter():
    if not JSONBIN_API_KEY or not JSONBIN_BIN_ID:
        return 1
    try:
        r = req_lib.get(f'{JSONBIN_BASE}/{JSONBIN_BIN_ID}/latest', headers=HEADERS_R, timeout=5)
        return r.json().get('record', {}).get('count', 1)
    except:
        return 1

def save_counter(n):
    if not JSONBIN_API_KEY or not JSONBIN_BIN_ID:
        return
    try:
        req_lib.put(f'{JSONBIN_BASE}/{JSONBIN_BIN_ID}', headers=HEADERS_W, json={'count': n}, timeout=5)
    except:
        pass

# ── Historial ──────────────────────────────────────────────────────────────────
def load_history():
    if not JSONBIN_API_KEY or not JSONBIN_HIST_ID:
        return []
    try:
        r = req_lib.get(f'{JSONBIN_BASE}/{JSONBIN_HIST_ID}/latest', headers=HEADERS_R, timeout=5)
        return r.json().get('record', {}).get('quotes', [])
    except:
        return []

def save_history(quotes):
    if not JSONBIN_API_KEY or not JSONBIN_HIST_ID:
        return
    try:
        req_lib.put(f'{JSONBIN_BASE}/{JSONBIN_HIST_ID}', headers=HEADERS_W, json={'quotes': quotes}, timeout=5)
    except:
        pass

# ── Rutas ──────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return jsonify({'status': 'ok', 'service': 'Cotizaciones Sanagua Lodge'})

@app.route('/counter')
def get_counter():
    return jsonify({'next': load_counter()})

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

    # Guardar en historial
    record = {**data, 'quote_num': quote_str,
              'created_at': datetime.now().isoformat(),
              'updated_at': datetime.now().isoformat(),
              'abono_pagado': 0, 'estado': 'Pendiente', 'notas_internas': ''}
    quotes = load_history()
    quotes.insert(0, record)
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


# ── HELPERS COMPARTIDOS ────────────────────────────────────────────────────────
COMPANY_NAME  = "Sanagua Lodge S.A."
COMPANY_RUC   = "RUC: 155761744-2-2025"
COMPANY_TEL   = "Tel: +507 6166-0114"
COMPANY_EMAIL = "sanagualodge@gmail.com"

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

def _header_block(story, W, C, quote_label, quote_num):
    hdr = Table([[
        Paragraph(f'<font color="#c8541a"><b>{COMPANY_NAME}</b></font>',
                  S('cn', fontSize=18, fontName='Helvetica-Bold')),
        Paragraph(
            f'<font size="9">{quote_label}</font><br/>'
            f'<font color="#c8541a" size="24"><b>#{quote_num}</b></font>',
            S('qn', fontSize=9, alignment=TA_RIGHT, leading=28)
        )
    ]], colWidths=[W*0.6, W*0.4])
    hdr.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE')]))
    story.append(hdr)
    story.append(Spacer(1,4))
    story.append(Paragraph(f'{COMPANY_RUC} | {COMPANY_TEL} | {COMPANY_EMAIL}',
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
    right = '<br/>'.join([
        f"<b>Fecha:</b> {date_str}",
        f"<b>Válida hasta:</b> {valid_str}",
    ])
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
    disc_label  = data.get('discount_label')
    disc_pct    = data.get('discount_pct', 0)
    disc_amount = data.get('discount_amount', 0)

    if disc_pct and disc_pct > 0:
        banner_color = C['PURPLE'] if 'Discapacidad' in (disc_label or '') else C['BLUE']
        bt = Table([[Paragraph(
            f'<font color="white"><b>🏷 {disc_label} — {int(disc_pct)}% de descuento sobre precio base</b></font>',
            S('bn', fontSize=9, textColor=C['WHITE'])
        )]], colWidths=[W])
        bt.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),banner_color),('PADDING',(0,0),(-1,-1),8)]))
        story.append(bt)
        story.append(Spacer(1,10))

    def th(txt, align=TA_CENTER):
        return Paragraph(f'<b>{txt}</b>', S('th', fontSize=8, textColor=C['WHITE'], alignment=align))
    def td(txt, align=TA_LEFT, bold=False):
        return Paragraph(f'<b>{txt}</b>' if bold else txt, S('td', fontSize=8.5, alignment=align))

    col_w = [W*0.35, W*0.07, W*0.13, W*0.09, W*0.13, W*0.23]
    rows = [[th('Descripción',TA_LEFT), th('Cant.'), th('P. Unitario'), th('ITBMS'), th('Monto ITBMS'), th('Total')]]
    for it in data.get('items', []):
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
        ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),
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
    if disc_pct and disc_pct > 0:
        td_list.append(tot_row(f'{disc_label} (−{int(disc_pct)}%):', f'−${disc_amount:.2f}', C['GREEN']))
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

    _header_block(story, W, C, 'Cotización Sanagua Lodge', quote_num)
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
        f'Esta cotización es válida hasta el {valid_str}. Gracias por su confianza en {COMPANY_NAME}.',
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
    _header_block(story, W, C, 'Confirmación de Reserva', quote_num)

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

    # Notas internas (si las hay)
    notas_internas = data.get('notas_internas','').strip()
    notes = data.get('notes','').strip()
    if notes or notas_internas:
        story.append(Spacer(1,16))
        story.append(HRFlowable(width=W, thickness=0.5, color=colors.HexColor('#e0dbd4')))
        story.append(Spacer(1,8))
        if notes:
            story.append(Paragraph('<b>Condiciones:</b>', S('nt', fontSize=9, textColor=C['MID_GRAY'])))
            story.append(Spacer(1,4))
            for line in notes.split('\n'):
                if line.strip():
                    story.append(Paragraph(line.strip(), S('nb', fontSize=9, textColor=C['DARK'], leading=14)))
                else:
                    story.append(Spacer(1,5))
        if notas_internas:
            story.append(Spacer(1,8))
            story.append(Paragraph('<b>Observaciones:</b>', S('ni', fontSize=9, textColor=C['MID_GRAY'])))
            story.append(Spacer(1,4))
            story.append(Paragraph(notas_internas, S('nib', fontSize=9, textColor=C['DARK'], leading=14)))

    # Pie
    story.append(Spacer(1,20))
    story.append(HRFlowable(width=W, thickness=0.5, color=colors.HexColor('#e0dbd4')))
    story.append(Spacer(1,6))
    story.append(Paragraph(
        f'Gracias por elegir {COMPANY_NAME}. ¡Esperamos recibirle pronto!',
        S('ft', fontSize=7.5, textColor=C['MID_GRAY'], alignment=TA_CENTER)
    ))
    doc.build(story)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)