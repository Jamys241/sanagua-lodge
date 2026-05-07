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

# ── Contador persistente via JSONBin.io ───────────────────────────────────────
# Pasos para configurar (una sola vez):
# 1. Crea cuenta gratis en https://jsonbin.io
# 2. Ve a "API Keys" y copia tu Master Key
# 3. Haz clic en "Create Bin", pega {"count": 1} y guarda
# 4. Copia el Bin ID que aparece en la URL
# 5. En Render > tu servicio > Environment, agrega:
#    JSONBIN_API_KEY = <tu Master Key>
#    JSONBIN_BIN_ID  = <tu Bin ID>
JSONBIN_API_KEY = os.environ.get('JSONBIN_API_KEY', '')
JSONBIN_BIN_ID  = os.environ.get('JSONBIN_BIN_ID', '')
JSONBIN_BASE    = 'https://api.jsonbin.io/v3/b'

def load_counter():
    if not JSONBIN_API_KEY or not JSONBIN_BIN_ID:
        return 1
    try:
        r = req_lib.get(
            f'{JSONBIN_BASE}/{JSONBIN_BIN_ID}/latest',
            headers={'X-Master-Key': JSONBIN_API_KEY},
            timeout=5
        )
        return r.json().get('record', {}).get('count', 1)
    except Exception:
        return 1

def save_counter(n):
    if not JSONBIN_API_KEY or not JSONBIN_BIN_ID:
        return
    try:
        req_lib.put(
            f'{JSONBIN_BASE}/{JSONBIN_BIN_ID}',
            headers={'X-Master-Key': JSONBIN_API_KEY, 'Content-Type': 'application/json'},
            json={'count': n},
            timeout=5
        )
    except Exception:
        pass

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

    quote_num = load_counter()
    save_counter(quote_num + 1)
    quote_str = str(quote_num).zfill(4)

    buffer = io.BytesIO()
    _build_pdf(buffer, data, quote_str)
    buffer.seek(0)

    response = send_file(
        buffer, mimetype='application/pdf',
        as_attachment=True,
        download_name=f'Cotización Sanagua Lodge #{quote_str}.pdf'
    )
    response.headers['X-Quote-Number'] = quote_str
    response.headers['Access-Control-Expose-Headers'] = 'X-Quote-Number'
    return response


def _build_pdf(buffer, data, quote_num):
    # ── Colores ────────────────────────────────────────────────────────────────
    BRAND      = colors.HexColor('#c8541a')
    DARK       = colors.HexColor('#1a1814')
    LIGHT_GRAY = colors.HexColor('#f5f3ee')
    MID_GRAY   = colors.HexColor('#6b6660')
    GREEN      = colors.HexColor('#2d7a4f')
    BLUE       = colors.HexColor('#1a5fa8')
    PURPLE     = colors.HexColor('#6b3fa0')
    WHITE      = colors.white
    RED10      = colors.HexColor('#c62828')

    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        leftMargin=0.75*inch, rightMargin=0.75*inch,
        topMargin=0.6*inch, bottomMargin=0.7*inch,
    )
    W = letter[0] - 1.5*inch
    story = []

    def S(name, **kw):
        return ParagraphStyle(name, parent=getSampleStyleSheet()['Normal'], **kw)

    # ── EMPRESA + NÚMERO ───────────────────────────────────────────────────────
    company_name  = "Sanagua Lodge S.A."
    company_ruc   = "RUC: 155761744-2-2025"
    company_tel   = "Tel: +507 6166-0114"
    company_email = "sanagualodge@gmail.com"

    hdr = Table([[
        Paragraph(f'<font color="#c8541a"><b>{company_name}</b></font>',
                  S('cn', fontSize=18, fontName='Helvetica-Bold')),
        Paragraph(
            f'<font size="9">Cotización Sanagua Lodge</font><br/>'
            f'<font color="#c8541a" size="24"><b>#{quote_num}</b></font>',
            S('qn', fontSize=9, alignment=TA_RIGHT, leading=28)
        )
    ]], colWidths=[W*0.6, W*0.4])
    hdr.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE')]))
    story.append(hdr)
    story.append(Spacer(1,4))
    story.append(Paragraph(f'{company_ruc} | {company_tel} | {company_email}',
                            S('si', fontSize=8, textColor=MID_GRAY)))
    story.append(Spacer(1,6))
    story.append(HRFlowable(width=W, thickness=2, color=BRAND))
    story.append(Spacer(1,12))

    # ── CLIENTE ────────────────────────────────────────────────────────────────
    client   = data.get('client', {})
    date_str = _fmt_date(data.get('date',''))
    valid_str= _fmt_date(data.get('valid_until',''))

    left  = '<br/>'.join([
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
        ('BACKGROUND',(0,0),(-1,-1), LIGHT_GRAY),
        ('BOX',(0,0),(-1,-1),0.5, colors.HexColor('#e0dbd4')),
        ('PADDING',(0,0),(-1,-1),10),
    ]))
    story.append(ct)
    story.append(Spacer(1,16))

    # ── BANNER DESCUENTO (si aplica) ───────────────────────────────────────────
    disc_label  = data.get('discount_label')
    disc_pct    = data.get('discount_pct', 0)
    disc_amount = data.get('discount_amount', 0)

    if disc_pct and disc_pct > 0:
        # Color según tipo
        if 'Discapacidad' in (disc_label or ''):
            banner_color = PURPLE
        else:
            banner_color = BLUE

        banner_txt = (
            f'<font color="white"><b>🏷 {disc_label} — '
            f'{int(disc_pct)}% de descuento aplicado sobre precio base</b></font>'
        )
        bt = Table([[Paragraph(banner_txt, S('bn', fontSize=9, textColor=WHITE))]],
                   colWidths=[W])
        bt.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,-1), banner_color),
            ('PADDING',(0,0),(-1,-1),8),
            ('ROUNDEDCORNERS',[5]),
        ]))
        story.append(bt)
        story.append(Spacer(1,10))

    # ── TABLA DE ÍTEMS ─────────────────────────────────────────────────────────
    def th(txt, align=TA_CENTER):
        return Paragraph(f'<b>{txt}</b>', S('th', fontSize=8, textColor=WHITE, alignment=align))
    def td(txt, align=TA_LEFT, bold=False):
        t = f'<b>{txt}</b>' if bold else txt
        return Paragraph(t, S('td', fontSize=8.5, alignment=align))

    has_7  = any(it.get('itbms_pct')==7  for it in data.get('items',[]))
    has_10 = any(it.get('itbms_pct')==10 for it in data.get('items',[]))
    has_disc = disc_pct and disc_pct > 0

    # Columnas: Descripción | Cant | P.Unit | ITBMS | [Desc%] | ITBMS$ | Total
    col_w = [W*0.35, W*0.07, W*0.13, W*0.09, W*0.13, W*0.23]
    headers = [th('Descripción', TA_LEFT), th('Cant.'), th('P. Unitario'),
               th('ITBMS'), th('Monto ITBMS'), th('Total')]

    rows = [headers]
    for it in data.get('items', []):
        itbms_pct = it.get('itbms_pct', 0)
        pct_label = f'{itbms_pct}%' if itbms_pct else 'Sin'
        rows.append([
            td(it.get('desc','')),
            td(str(it.get('qty',1)), TA_CENTER),
            td(f"${it.get('price',0):.2f}", TA_RIGHT),
            td(pct_label, TA_CENTER),
            td(f"${it.get('itbms_amount',0):.2f}", TA_RIGHT),
            td(f"${it.get('line_total',0):.2f}", TA_RIGHT, bold=True),
        ])

    it_table = Table(rows, colWidths=col_w, repeatRows=1)
    it_table.setStyle(TableStyle([
        ('BACKGROUND',  (0,0),(-1,0), DARK),
        ('TEXTCOLOR',   (0,0),(-1,0), WHITE),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[WHITE, LIGHT_GRAY]),
        ('GRID',        (0,0),(-1,-1), 0.4, colors.HexColor('#e0dbd4')),
        ('VALIGN',      (0,0),(-1,-1), 'MIDDLE'),
        ('TOPPADDING',  (0,0),(-1,-1), 7),
        ('BOTTOMPADDING',(0,0),(-1,-1), 7),
        ('LEFTPADDING', (0,0),(-1,-1), 7),
        ('RIGHTPADDING',(0,0),(-1,-1), 7),
    ]))
    story.append(it_table)
    story.append(Spacer(1,12))

    # ── TOTALES ────────────────────────────────────────────────────────────────
    subtotal       = data.get('subtotal', 0)
    base_after     = data.get('base_after_discount', subtotal)
    itbms7_total   = data.get('itbms7_total', 0)
    itbms10_total  = data.get('itbms10_total', 0)
    total          = data.get('total', 0)

    def tot_row(label, amount, color=MID_GRAY, bold=False, size=9):
        lbl = f'<b>{label}</b>' if bold else label
        amt = f'<b>{amount}</b>' if bold else amount
        return [
            Paragraph('', S('x')),
            Paragraph(lbl, S('tl', fontSize=size, alignment=TA_RIGHT, textColor=color)),
            Paragraph(amt, S('tr', fontSize=size, alignment=TA_RIGHT, textColor=color)),
        ]

    tot_data = []
    tot_data.append(tot_row('Subtotal (sin impuestos):', f'${subtotal:.2f}'))

    if disc_pct and disc_pct > 0:
        tot_data.append(tot_row(
            f'{disc_label} (−{int(disc_pct)}%):',
            f'−${disc_amount:.2f}',
            color=GREEN
        ))
        tot_data.append(tot_row('Base gravable:', f'${base_after:.2f}'))

    if itbms7_total > 0 or has_7:
        tot_data.append(tot_row('ITBMS 7%:', f'${itbms7_total:.2f}'))
    if itbms10_total > 0 or has_10:
        tot_data.append(tot_row('ITBMS 10%:', f'${itbms10_total:.2f}', color=RED10))

    abono_50 = data.get('abono_50', total * 0.5)
    tot_data.append(tot_row('TOTAL:', f'${total:.2f}', color=BRAND, bold=True, size=11))
    tot_data.append(tot_row('Abono requerido (50%):', f'${abono_50:.2f}', color=BLUE, bold=True, size=10))

    tc = [W*0.52, W*0.28, W*0.20]
    tot_table = Table(tot_data, colWidths=tc)
    disc_row_idx = 1 if (disc_pct and disc_pct > 0) else None
    ts = [
        ('LINEABOVE',    (1, len(tot_data)-2), (-1, len(tot_data)-2), 1.5, BRAND),
        ('LINEABOVE',    (1, len(tot_data)-1), (-1, len(tot_data)-1), 0.5, BLUE),
        ('BACKGROUND',   (0, len(tot_data)-1), (-1, len(tot_data)-1), colors.HexColor('#e8f0fa')),
        ('ROUNDEDCORNERS', [4]),
        ('TOPPADDING',   (0,0),(-1,-1), 5),
        ('BOTTOMPADDING',(0,0),(-1,-1), 5),
        ('RIGHTPADDING', (0,0),(-1,-1), 4),
    ]
    if disc_row_idx is not None:
        ts.append(('TEXTCOLOR', (1, disc_row_idx), (-1, disc_row_idx), GREEN))
    tot_table.setStyle(TableStyle(ts))
    story.append(tot_table)

    # ── NOTAS ──────────────────────────────────────────────────────────────────
    notes = data.get('notes','').strip()
    if notes:
        story.append(Spacer(1,16))
        story.append(HRFlowable(width=W, thickness=0.5, color=colors.HexColor('#e0dbd4')))
        story.append(Spacer(1,8))
        story.append(Paragraph('<b>Notas y Condiciones:</b>', S('nt', fontSize=9, textColor=MID_GRAY)))
        story.append(Spacer(1,4))
        story.append(Paragraph(notes, S('nb', fontSize=9, textColor=DARK, leading=14)))

    # ── PIE ────────────────────────────────────────────────────────────────────
    story.append(Spacer(1,20))
    story.append(HRFlowable(width=W, thickness=0.5, color=colors.HexColor('#e0dbd4')))
    story.append(Spacer(1,6))
    story.append(Paragraph(
        f'Esta cotización es válida hasta el {valid_str}. Gracias por su confianza en {company_name}.',
        S('ft', fontSize=7.5, textColor=MID_GRAY, alignment=TA_CENTER)
    ))

    doc.build(story)


def _fmt_date(d):
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
