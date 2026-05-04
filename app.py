from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER
import io
import json
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Permite peticiones desde GitHub Pages

# ─── Contador de cotizaciones ─────────────────────────────────────────────────
COUNTER_FILE = 'counter.json'

def load_counter():
    if os.path.exists(COUNTER_FILE):
        with open(COUNTER_FILE) as f:
            return json.load(f).get('count', 1)
    return 1

def save_counter(n):
    with open(COUNTER_FILE, 'w') as f:
        json.dump({'count': n}, f)

# ─── Rutas ────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return jsonify({'status': 'ok', 'service': 'Cotizaciones API'})

@app.route('/counter')
def get_counter():
    return jsonify({'next': load_counter()})

@app.route('/generate-pdf', methods=['POST'])
def generate_pdf():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Incrementar contador
    quote_num = load_counter()
    save_counter(quote_num + 1)
    quote_str = str(quote_num).zfill(4)

    # Generar PDF en memoria
    buffer = io.BytesIO()
    _build_pdf(buffer, data, quote_str)
    buffer.seek(0)

    response = send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'Cotizacion-{quote_str}.pdf'
    )
    response.headers['X-Quote-Number'] = quote_str
    response.headers['Access-Control-Expose-Headers'] = 'X-Quote-Number'
    return response


# ─── Construcción del PDF ──────────────────────────────────────────────────────
def _build_pdf(buffer, data, quote_num):
    # ── Colores de marca ──────────────────────────────────────────────────────
    BRAND      = colors.HexColor('#c8541a')   # naranja corporativo
    DARK       = colors.HexColor('#1a1814')
    LIGHT_GRAY = colors.HexColor('#f5f3ee')
    MID_GRAY   = colors.HexColor('#6b6660')
    WHITE      = colors.white

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.75*inch,
        rightMargin=0.75*inch,
        topMargin=0.6*inch,
        bottomMargin=0.7*inch,
    )

    W = letter[0] - 1.5*inch   # ancho útil
    story = []
    styles = getSampleStyleSheet()

    def style(name, **kw):
        s = ParagraphStyle(name, parent=styles['Normal'], **kw)
        return s

    # ── ENCABEZADO ─────────────────────────────────────────────────────────────
    # Tu empresa (personaliza estos datos)
    company_name = "Sanagua Lodge S.A."
    company_ruc  = "RUC: 155761744-2-2025"
    company_tel  = "Tel: +507 6166-0114"
    company_email = "sanagualodge@a.com"

    header_data = [[
        Paragraph(f'<font color="#c8541a"><b>{company_name}</b></font>',
                  style('cn', fontSize=18, fontName='Helvetica-Bold')),
        Paragraph(
            f'<b>COTIZACIÓN</b><br/><font color="#c8541a" size="22">#{quote_num}</font>',
            style('qn', fontSize=10, alignment=TA_RIGHT)
        )
    ]]
    header_table = Table(header_data, colWidths=[W*0.6, W*0.4])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(header_table)

    # Datos empresa bajo el nombre
    story.append(Spacer(1, 4))
    sub_info = f'{company_ruc} | {company_tel} | {company_email}'
    story.append(Paragraph(sub_info, style('si', fontSize=8, textColor=MID_GRAY)))
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width=W, thickness=2, color=BRAND))
    story.append(Spacer(1, 12))

    # ── CLIENTE y FECHAS ───────────────────────────────────────────────────────
    client = data.get('client', {})
    date_str = _fmt_date(data.get('date', ''))
    valid_str = _fmt_date(data.get('valid_until', ''))

    left_lines = [
        f"<b>Cliente:</b> {client.get('name', '—')}",
        f"<b>RUC/Cédula:</b> {client.get('ruc', '—')}",
        f"<b>Correo:</b> {client.get('email', '—')}",
        f"<b>Teléfono:</b> {client.get('phone', '—')}",
        f"<b>Dirección:</b> {client.get('address', '—')}",
    ]
    right_lines = [
        f"<b>Fecha:</b> {date_str}",
        f"<b>Válida hasta:</b> {valid_str}",
    ]

    cl = '<br/>'.join(left_lines)
    cr = '<br/>'.join(right_lines)

    client_table = Table([[
        Paragraph(cl, style('cl', fontSize=9, leading=14)),
        Paragraph(cr, style('cr', fontSize=9, leading=14, alignment=TA_RIGHT))
    ]], colWidths=[W*0.6, W*0.4])
    client_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BACKGROUND', (0,0), (-1,-1), LIGHT_GRAY),
        ('ROUNDEDCORNERS', [6]),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#e0dbd4')),
        ('PADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(client_table)
    story.append(Spacer(1, 16))

    # ── TABLA DE ÍTEMS ─────────────────────────────────────────────────────────
    col_desc  = W * 0.40
    col_qty   = W * 0.08
    col_price = W * 0.16
    col_itbms = W * 0.14
    col_sub   = W * 0.16
    col_total = W * 0.06  # unused, absorbed

    def th(txt):
        return Paragraph(f'<b>{txt}</b>', style('th', fontSize=8, textColor=WHITE, alignment=TA_CENTER))

    def td(txt, align=TA_LEFT):
        return Paragraph(txt, style('td', fontSize=9, alignment=align))

    rows = [[th('Descripción'), th('Cant.'), th('P. Unitario'), th('ITBMS (7%)'), th('ITBMS (10%)') th('Subtotal')]]

    items = data.get('items', [])

subtotal_general = 0
itbms_total = 0

for it in items:
    precio = it.get('price', 0)
    cantidad = it.get('qty', 1)
    exento = it.get('exento', False)
    tasa = it.get('itbms_rate', 0.07)  # ← aquí decides 7% o 10%

    subtotal = precio * cantidad

    # ITBMS
    if exento:
        itbms_amt = 0
    else:
        itbms_amt = subtotal * tasa

    total_linea = subtotal + itbms_amt

    subtotal_general += subtotal
    itbms_total += itbms_amt

    rows.append([
        td(it.get('desc', '')),
        td(str(cantidad), TA_CENTER),
        td(f"${precio:.2f}", TA_RIGHT),
        td(f"${itbms_amt:.2f}", TA_RIGHT),
        td(f"${total_linea:.2f}", TA_RIGHT),
    ])

    col_widths = [col_desc, col_qty, col_price, col_itbms, col_sub]
    items_table = Table(rows, colWidths=col_widths, repeatRows=1)

    # Estilo de la tabla
    ts = [
        ('BACKGROUND',  (0,0), (-1,0), DARK),
        ('TEXTCOLOR',   (0,0), (-1,0), WHITE),
        ('FONTNAME',    (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',    (0,0), (-1,0), 8),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [WHITE, LIGHT_GRAY]),
        ('GRID',        (0,0), (-1,-1), 0.5, colors.HexColor('#e0dbd4')),
        ('VALIGN',      (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING',  (0,0), (-1,-1), 8),
        ('BOTTOMPADDING',(0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING',(0,0), (-1,-1), 8),
    ]
    items_table.setStyle(TableStyle(ts))
    story.append(items_table)
    story.append(Spacer(1, 12))

    # ── TOTALES ────────────────────────────────────────────────────────────────
    subtotal   = data.get('subtotal', 0)
    itbms_tot  = data.get('itbms_total', 0)
    total      = data.get('total', 0)

    def total_row(label, amount, bold=False):
        lbl = f'<b>{label}</b>' if bold else label
        amt = f'<b>{amount}</b>' if bold else amount
        return [
            Paragraph('', style('x')),
            Paragraph(lbl, style('tl', fontSize=9, alignment=TA_RIGHT)),
            Paragraph(amt, style('tr', fontSize=9, alignment=TA_RIGHT,
                                 textColor=BRAND if bold else DARK)),
        ]

    tot_data = [
        total_row('Subtotal:', f'${subtotal:.2f}'),
        total_row('ITBMS (7%):', f'${itbms_tot:.2f}'),
        total_row('TOTAL:', f'${total:.2f}', bold=True),
    ]

    tot_col = [W*0.55, W*0.25, W*0.20]
    tot_table = Table(tot_data, colWidths=tot_col)
    tot_table.setStyle(TableStyle([
        ('LINEABOVE', (1, 2), (-1, 2), 1.5, BRAND),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(tot_table)

    # ── NOTAS ──────────────────────────────────────────────────────────────────
    notes = data.get('notes', '').strip()
    if notes:
        story.append(Spacer(1, 16))
        story.append(HRFlowable(width=W, thickness=0.5, color=colors.HexColor('#e0dbd4')))
        story.append(Spacer(1, 8))
        story.append(Paragraph('<b>Notas y Condiciones:</b>',
                               style('nt', fontSize=9, textColor=MID_GRAY)))
        story.append(Spacer(1, 4))
        story.append(Paragraph(notes, style('nb', fontSize=9, textColor=DARK, leading=14)))

    # ── PIE DE PÁGINA ──────────────────────────────────────────────────────────
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width=W, thickness=0.5, color=colors.HexColor('#e0dbd4')))
    story.append(Spacer(1, 6))
    footer_txt = (f'Esta cotización es válida hasta el {valid_str}. '
                  f'Gracias por su confianza en {company_name}.')
    story.append(Paragraph(footer_txt,
                            style('ft', fontSize=7.5, textColor=MID_GRAY, alignment=TA_CENTER)))

    doc.build(story)


def _fmt_date(d: str) -> str:
    try:
        dt = datetime.strptime(d, '%Y-%m-%d')
        meses = ['enero','febrero','marzo','abril','mayo','junio',
                 'julio','agosto','septiembre','octubre','noviembre','diciembre']
        return f"{dt.day} de {meses[dt.month-1]} de {dt.year}"
    except:
        return d or '—'


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
