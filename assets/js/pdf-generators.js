// ── Generadores de PDF (jsPDF) — compartidos entre achive.html y history.html ──
// Requiere que la página que lo incluya ya tenga cargado jsPDF y defina las
// variables globales `empresaData` y `logoBase64` (se usan como respaldo si
// el objeto `data` de la cotización no trae su propio logo/empresa).
  function generatePDFlocal(data, quoteNum, tipo) {
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF({ unit:'mm', format:'letter' });
    const emp = data.empresa || empresaData;
    const W = 216, margin = 20, cW = W - margin*2;
    let y = 20;

    const accent  = [200, 84, 26];
    const dark    = [26,  24, 20];
    const muted   = [107, 102, 96];
    const success = [45,  122, 79];

    // ── Logo ──────────────────────────────────────────────────────────────
    const logo = data.logo || logoBase64;
    if (logo && logo.startsWith('data:image')) {
      try {
        const ext = logo.includes('png') ? 'PNG' : 'JPEG';
        doc.addImage(logo, ext, margin, y, 40, 14);
      } catch {}
    }

    // ── Encabezado ────────────────────────────────────────────────────────
    doc.setFont('helvetica','bold');
    doc.setFontSize(14);
    doc.setTextColor(...accent);
    doc.text(emp.nombre || 'Sanagua Lodge S.A.', margin + (logo?44:0), y+8);

    const titulo = tipo === 'confirmacion'
      ? `Confirmación de Reserva\n#${quoteNum}`
      : `Cotización Sanagua Lodge\n#${quoteNum}`;
    doc.setFontSize(10);
    doc.setTextColor(...dark);
    doc.text(titulo, W - margin, y+4, {align:'right'});

    y += 18;
    doc.setFont('helvetica','normal');
    doc.setFontSize(8);
    doc.setTextColor(...muted);
    doc.text(`RUC: ${emp.ruc||''} | Tel: ${emp.tel||''} | ${emp.email||''}`, margin, y);
    y += 4;
    doc.setDrawColor(...accent);
    doc.setLineWidth(0.8);
    doc.line(margin, y, W-margin, y);
    y += 6;

    // ── Datos cliente ─────────────────────────────────────────────────────
    const cl = data.client || {};
    const tipoLabel = cl.tipo === 'natural' ? 'Persona Natural' : cl.tipo === 'juridica' ? 'Persona Jurídica' : 'Cliente Contado';
    const rucConDv  = cl.ruc ? (cl.dv ? `${cl.ruc} DV: ${cl.dv}` : cl.ruc) : '—';
    const esFormal  = cl.tipo && cl.tipo !== 'contado';
    const clH = esFormal ? 34 : 28;
    doc.setFillColor(245, 243, 238);
    doc.roundedRect(margin, y, cW, clH, 2, 2, 'F');
    doc.setFontSize(9); doc.setTextColor(...dark);

    // Helper: badge celeste para exento
    function drawExentoBadge(bx, by) {
      doc.setFillColor(173, 216, 230);
      doc.roundedRect(bx, by, 28, 5, 1.5, 1.5, 'F');
      doc.setFontSize(6.5); doc.setFont('helvetica','bold');
      doc.setTextColor(30, 90, 130);
      doc.text('EXENTO ITBMS', bx+3, by+3.8);
      doc.setTextColor(...dark); doc.setFontSize(9); doc.setFont('helvetica','normal');
    }

    if (esFormal) {
      // Badge tipo (naranja)
      doc.setFontSize(7); doc.setFont('helvetica','bold'); doc.setTextColor(200,84,26);
      doc.text(tipoLabel.toUpperCase(), margin+4, y+5);
      if (cl.exento) drawExentoBadge(margin+70, y+2);
      doc.setTextColor(...dark); doc.setFontSize(9);
      doc.setFont('helvetica','bold'); doc.text('Cliente:', margin+4, y+11);
      doc.setFont('helvetica','normal'); doc.text(cl.name||'—', margin+20, y+11);
      doc.setFont('helvetica','bold'); doc.text('RUC/Cédula:', margin+4, y+17);
      doc.setFont('helvetica','normal'); doc.text(rucConDv, margin+26, y+17);
      doc.setFont('helvetica','bold'); doc.text('Teléfono:', margin+4, y+23);
      doc.setFont('helvetica','normal'); doc.text(cl.phone||'—', margin+22, y+23);
      doc.setFont('helvetica','bold'); doc.text('Correo:', margin+4, y+29);
      doc.setFont('helvetica','normal'); doc.text(cl.email||'—', margin+18, y+29);
    } else {
      if (cl.exento) drawExentoBadge(margin+55, y+2);
      doc.setFont('helvetica','bold'); doc.text('Cliente:', margin+4, y+7);
      doc.setFont('helvetica','normal'); doc.text(cl.name||'—', margin+20, y+7);
      doc.setFont('helvetica','bold'); doc.text('RUC/Cédula:', margin+4, y+13);
      doc.setFont('helvetica','normal'); doc.text(cl.ruc||'—', margin+26, y+13);
      doc.setFont('helvetica','bold'); doc.text('Teléfono:', margin+4, y+19);
      doc.setFont('helvetica','normal'); doc.text(cl.phone||'—', margin+22, y+19);
      doc.setFont('helvetica','bold'); doc.text('Correo:', margin+4, y+25);
      doc.setFont('helvetica','normal'); doc.text(cl.email||'—', margin+18, y+25);
    }
    y += clH + 2;

    // Fecha y categoría a la derecha
    const fmtD = s => { if(!s)return'—'; try{const d=new Date(s+'T12:00:00');return d.toLocaleDateString('es-PA',{day:'2-digit',month:'short',year:'numeric'});}catch{return s;} };
    doc.setFont('helvetica','bold'); doc.text('Fecha:', W-margin-60, y+7);
    doc.setFont('helvetica','normal'); doc.text(fmtD(data.date), W-margin-40, y+7);
    if (data.visit_date) {
      doc.setFont('helvetica','bold'); doc.text('Entrada:', W-margin-60, y+13);
      doc.setFont('helvetica','normal'); doc.text(fmtD(data.visit_date), W-margin-40, y+13);
    }
    if (data.visit_date_end) {
      doc.setFont('helvetica','bold'); doc.text('Salida:', W-margin-60, y+19);
      doc.setFont('helvetica','normal'); doc.text(fmtD(data.visit_date_end), W-margin-40, y+19);
    }
    if (data.categoria) {
      doc.setFont('helvetica','bold'); doc.text('Categoría:', W-margin-60, y+25);
      doc.setFont('helvetica','normal'); doc.text(data.categoria, W-margin-35, y+25);
    }
    y += 34;

    // ── En confirmación ───────────────────────────────────────────────────
    if (tipo === 'confirmacion') {
      // Banner — color según estado
      const estado = (data.estado || 'Confirmada');
      const bannerColor = estado==='Completada' ? success
                        : estado==='Cancelada'  ? [192,57,43]
                        : estado==='Aplazada'   ? [176,131,0]
                        : success; // Confirmada y resto en verde
      doc.setFillColor(...bannerColor);
      doc.roundedRect(margin, y, cW, 10, 2, 2, 'F');
      doc.setFont('helvetica','bold'); doc.setFontSize(10); doc.setTextColor(255,255,255);
      doc.text(`RESERVA ${estado.toUpperCase()} - #${quoteNum}`, margin+4, y+6.5);
      y += 14;

      // ── Ítems reservados ──────────────────────────────────────────────
      const items = data.items || [];
      if (items.length) {
        doc.setFont('helvetica','bold'); doc.setFontSize(9); doc.setTextColor(...dark);
        doc.text('Servicios reservados:', margin, y); y += 5;
        doc.setFillColor(...dark); doc.rect(margin, y, cW, 6, 'F');
        doc.setFont('helvetica','bold'); doc.setFontSize(7.5); doc.setTextColor(255,255,255);
        doc.text('Descripción', margin+3, y+4.2);
        doc.text('Cant.', margin+cW*0.55, y+4.2);
        doc.text('Precio', margin+cW*0.66, y+4.2);
        doc.text('Total', margin+cW*0.85, y+4.2);
        y += 6;
        items.forEach((it,i) => {
          const bg = i%2===0 ? [255,255,255] : [245,243,238];
          doc.setFillColor(...bg); doc.rect(margin, y, cW, 5.5, 'F');
          doc.setFont('helvetica','normal'); doc.setFontSize(8); doc.setTextColor(...dark);
          doc.text(String(it.desc||'').substring(0,38), margin+3, y+3.8);
          doc.text(String(it.qty||1), margin+cW*0.55, y+3.8);
          doc.text(`$${Number(it.price||0).toFixed(2)}`, margin+cW*0.66, y+3.8);
          doc.text(`$${Number(it.line_total||0).toFixed(2)}`, margin+cW*0.85, y+3.8);
          y += 5.5;
          if (y > 245) { doc.addPage(); y = 20; }
        });
        y += 5;
      }

      // ── Resumen financiero ────────────────────────────────────────────
      doc.setFont('helvetica','bold'); doc.setFontSize(9); doc.setTextColor(...dark);
      doc.text('Resumen de pagos:', margin, y); y += 5;

      const total    = data.total||0;
      const abono50  = data.abono_50 || total*.5;
      const abono    = data.abono_pagado||0;
      const cancel   = data.cancelacion_pagada||0;
      const recibido = abono + cancel;
      const saldo    = Math.max(0, total - recibido);
      const pct      = total > 0 ? Math.round(recibido/total*100) : 0;

      doc.setFillColor(232,240,250);
      doc.roundedRect(margin, y, cW, 40, 2, 2, 'F');

      const rows = [
        ['Total de la reserva',    `$${total.toFixed(2)}`,    dark],
        ['Abono requerido (50%)',  `$${abono50.toFixed(2)}`,  muted],
        ['Abono recibido',         `$${abono.toFixed(2)}`,    success],
        ['Cancelación recibida',   `$${cancel.toFixed(2)}`,   success],
        ['Total recibido',         `$${recibido.toFixed(2)}`, success],
        ['Saldo pendiente',        `$${saldo.toFixed(2)}`,    saldo===0?success:accent],
      ];
      let ry = y + 5;
      rows.forEach(([lbl,val,col]) => {
        doc.setFont('helvetica','normal'); doc.setFontSize(8.5); doc.setTextColor(...muted);
        doc.text(lbl, margin+4, ry);
        doc.setFont('helvetica','bold'); doc.setTextColor(...col);
        doc.text(val, W-margin-4, ry, {align:'right'});
        ry += 6;
      });
      y += 42;

      // Barra de progreso de pago
      doc.setDrawColor(200,200,200); doc.setLineWidth(0.3);
      doc.roundedRect(margin, y, cW, 4, 2, 2, 'D');
      const barW = Math.min(cW, cW * pct/100);
      if (barW > 0) {
        doc.setFillColor(...(pct>=100?success:pct>=50?[26,95,168]:accent));
        doc.roundedRect(margin, y, barW, 4, 2, 2, 'F');
      }
      doc.setFont('helvetica','normal'); doc.setFontSize(7.5); doc.setTextColor(...muted);
      doc.text(`${pct}% pagado`, W-margin-4, y+3, {align:'right'});
      y += 9;

      // ── Notas internas / observaciones ───────────────────────────────
      if (data.notas_internas) {
        y += 4;
        doc.setFont('helvetica','bold'); doc.setFontSize(9); doc.setTextColor(...dark);
        doc.text('Observaciones:', margin, y); y += 5;
        doc.setFont('helvetica','normal'); doc.setFontSize(8.5); doc.setTextColor(...muted);
        const lines = doc.splitTextToSize(data.notas_internas, cW);
        lines.forEach(line => {
          doc.text(line, margin, y); y += 5;
          if (y > 250) { doc.addPage(); y = 20; }
        });
      }
    } else {
      // ── Tabla de ítems (cotización) ────────────────────────────────────
      const items = data.items || [];
      if (items.length) {
        // Cabecera
        doc.setFillColor(...dark); doc.rect(margin, y, cW, 7, 'F');
        doc.setFont('helvetica','bold'); doc.setFontSize(8); doc.setTextColor(255,255,255);
        doc.text('Descripción', margin+3, y+5);
        doc.text('Cant.', margin+cW*0.55, y+5);
        doc.text('P. Unit.', margin+cW*0.65, y+5);
        doc.text('ITBMS', margin+cW*0.77, y+5);
        doc.text('Total', margin+cW*0.88, y+5);
        y += 7;
        items.forEach((it,i) => {
          const bg = i%2===0 ? [255,255,255] : [245,243,238];
          doc.setFillColor(...bg); doc.rect(margin, y, cW, 6, 'F');
          doc.setFont('helvetica','normal'); doc.setFontSize(8); doc.setTextColor(...dark);
          doc.text(it.desc||'', margin+3, y+4.5, {maxWidth: cW*0.5});
          doc.text(String(it.qty||1), margin+cW*0.55, y+4.5);
          doc.text(`$${Number(it.price||0).toFixed(2)}`, margin+cW*0.65, y+4.5);
          doc.text(`$${Number(it.itbms_amount||0).toFixed(2)}`, margin+cW*0.77, y+4.5);
          doc.text(`$${Number(it.line_total||0).toFixed(2)}`, margin+cW*0.88, y+4.5);
          y += 6;
          if (y > 240) { doc.addPage(); y = 20; }
        });
        y += 4;
      }

      // ── Totales ─────────────────────────────────────────────────────────
      const sub   = data.subtotal||0;
      const disc  = data.discount_amount||0;
      const i7    = data.itbms7_total||0;
      const i10   = data.itbms10_total||0;
      const total = data.total||0;
      const abono50 = data.abono_50||total*.5;
      const totRows = [
        ['Subtotal', `$${sub.toFixed(2)}`],
        ...(disc>0?[[data.discount_label||'Descuento', `-$${disc.toFixed(2)}`]]:[]),
        ...(i7>0?[['ITBMS 7%', `$${i7.toFixed(2)}`]]:[]),
        ...(i10>0?[['ITBMS 10%', `$${i10.toFixed(2)}`]]:[]),
      ];
      const xL = margin + cW*0.55;
      const xR = W - margin - 4;
      doc.setFontSize(9);
      totRows.forEach(([lbl,val]) => {
        doc.setFont('helvetica','normal'); doc.setTextColor(...muted);
        doc.text(lbl, xL, y); doc.text(val, xR, y, {align:'right'}); y+=5.5;
      });
      doc.setDrawColor(...accent); doc.setLineWidth(0.6); doc.line(xL, y, xR, y); y+=4;
      doc.setFont('helvetica','bold'); doc.setFontSize(11); doc.setTextColor(...accent);
      doc.text('TOTAL', xL, y); doc.text(`$${total.toFixed(2)}`, xR, y, {align:'right'}); y+=5;
      doc.setFont('helvetica','normal'); doc.setFontSize(9); doc.setTextColor(...[26,95,168]);
      doc.text('Abono requerido (50%)', xL, y+5); doc.text(`$${abono50.toFixed(2)}`, xR, y+5, {align:'right'}); y+=12;

      // ── Notas ────────────────────────────────────────────────────────────
      if (data.notes) {
        doc.setFont('helvetica','bold'); doc.setFontSize(9); doc.setTextColor(...dark);
        doc.text('Notas y Condiciones:', margin, y); y+=5;
        doc.setFont('helvetica','normal'); doc.setTextColor(...muted);
        const lines = doc.splitTextToSize(data.notes, cW);
        doc.text(lines, margin, y); y += lines.length*4.5+4;
      }
    }

    // ── Pie ───────────────────────────────────────────────────────────────
    doc.setFont('helvetica','normal'); doc.setFontSize(7.5); doc.setTextColor(...muted);
    const footer = tipo==='confirmacion'
      ? `Gracias por elegir ${emp.nombre||'Sanagua Lodge S.A.'}. ¡Esperamos recibirle pronto!`
      : `Esta cotización es válida hasta el ${fmtD(data.valid_until)}. Gracias por su confianza en ${emp.nombre||'Sanagua Lodge S.A.'}.`;
    doc.text(footer, W/2, 275, {align:'center', maxWidth: cW});

    // ── Descargar ─────────────────────────────────────────────────────────
    const clientName = data.client?.name || 'Cliente';
    const filename = tipo==='confirmacion'
      ? `Confirmación Sanagua Lodge ${quoteNum} ${clientName}.pdf`
      : `Cotización Sanagua Lodge #${quoteNum}.pdf`;
    doc.save(filename);
  }


  function generatePDFlocalV2(data, quoteNum, tipo) {
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF({ unit:'mm', format:'letter' });
    const emp = data.empresa || empresaData;
    const W = 216, margin = 20, cW = W - margin*2;
    let y = 20;

    const accent  = [127, 160, 172];
    const gold    = [201, 168, 76];
    const dark    = [26,  34, 38];
    const muted   = [107, 102, 112];
    const success = [45,  122, 79];

    // ── Encabezado: franja de color insignia de borde a borde ──────────────
    const bandH = 38;
    doc.setFillColor(...accent);
    doc.rect(0, 0, W, bandH, 'F');

    const logo = data.logo || logoBase64;
    let logoDrawnWidth = 0;
    if (logo && logo.startsWith('data:image')) {
      try {
        const ext = logo.includes('png') ? 'PNG' : 'JPEG';
        // Respetar la proporción real del logo en vez de estirarlo — se
        // encaja dentro de una caja más grande (46x20mm) que antes.
        const maxW = 62, maxH = 30;
        const props = doc.getImageProperties(logo);
        const escala = Math.min(maxW / props.width, maxH / props.height);
        const drawW = props.width * escala, drawH = props.height * escala;
        doc.addImage(logo, ext, margin, (bandH - drawH) / 2, drawW, drawH);
        logoDrawnWidth = drawW;
      } catch {}
    }

    const textX = margin + (logo ? logoDrawnWidth + 6 : 0);
    doc.setFont('helvetica','bold');
    doc.setFontSize(17);
    doc.setTextColor(255,255,255);
    doc.text(emp.nombre || 'Sanagua Lodge S.A.', textX, bandH/2 - 2);

    doc.setFont('helvetica','normal');
    doc.setFontSize(8.5);
    doc.setTextColor(230,238,240);
    doc.text(`RUC: ${emp.ruc||''}  |  Tel: ${emp.tel||''}  |  ${emp.email||''}`, textX, bandH/2 + 6);

    const titulo = tipo === 'confirmacion' ? 'Confirmación de Reserva' : 'Cotización Sanagua Lodge';
    doc.setFont('helvetica','normal');
    doc.setFontSize(9);
    doc.setTextColor(230,238,240);
    doc.text(titulo, W - margin, bandH/2 - 3, {align:'right'});
    doc.setFont('helvetica','bold');
    doc.setFontSize(21);
    doc.setTextColor(255,255,255);
    doc.text(`#${quoteNum}`, W - margin, bandH/2 + 7, {align:'right'});

    // Línea dorada de cierre de la franja
    doc.setFillColor(...gold);
    doc.rect(0, bandH, W, 1.3, 'F');

    y = bandH + 10;

    // ── Datos cliente ─────────────────────────────────────────────────────
    const cl = data.client || {};
    const tipoLabel = cl.tipo === 'natural' ? 'Persona Natural' : cl.tipo === 'juridica' ? 'Persona Jurídica' : 'Cliente Contado';
    const rucConDv  = cl.ruc ? (cl.dv ? `${cl.ruc} DV: ${cl.dv}` : cl.ruc) : '—';
    const esFormal  = cl.tipo && cl.tipo !== 'contado';
    const clH = esFormal ? 34 : 28;
    doc.setFillColor(245, 243, 238);
    doc.roundedRect(margin, y, cW, clH, 2, 2, 'F');
    doc.setFontSize(9); doc.setTextColor(...dark);

    // Helper: badge celeste para exento
    function drawExentoBadge(bx, by) {
      doc.setFillColor(173, 216, 230);
      doc.roundedRect(bx, by, 28, 5, 1.5, 1.5, 'F');
      doc.setFontSize(6.5); doc.setFont('helvetica','bold');
      doc.setTextColor(30, 90, 130);
      doc.text('EXENTO ITBMS', bx+3, by+3.8);
      doc.setTextColor(...dark); doc.setFontSize(9); doc.setFont('helvetica','normal');
    }

    if (esFormal) {
      // Badge tipo (naranja)
      doc.setFontSize(7); doc.setFont('helvetica','bold'); doc.setTextColor(127,160,172);
      doc.text(tipoLabel.toUpperCase(), margin+4, y+5);
      if (cl.exento) drawExentoBadge(margin+70, y+2);
      doc.setTextColor(...dark); doc.setFontSize(9);
      doc.setFont('helvetica','bold'); doc.text('Cliente:', margin+4, y+11);
      doc.setFont('helvetica','normal'); doc.text(cl.name||'—', margin+20, y+11);
      doc.setFont('helvetica','bold'); doc.text('RUC/Cédula:', margin+4, y+17);
      doc.setFont('helvetica','normal'); doc.text(rucConDv, margin+26, y+17);
      doc.setFont('helvetica','bold'); doc.text('Teléfono:', margin+4, y+23);
      doc.setFont('helvetica','normal'); doc.text(cl.phone||'—', margin+22, y+23);
      doc.setFont('helvetica','bold'); doc.text('Correo:', margin+4, y+29);
      doc.setFont('helvetica','normal'); doc.text(cl.email||'—', margin+18, y+29);
    } else {
      if (cl.exento) drawExentoBadge(margin+55, y+2);
      doc.setFont('helvetica','bold'); doc.text('Cliente:', margin+4, y+7);
      doc.setFont('helvetica','normal'); doc.text(cl.name||'—', margin+20, y+7);
      doc.setFont('helvetica','bold'); doc.text('RUC/Cédula:', margin+4, y+13);
      doc.setFont('helvetica','normal'); doc.text(cl.ruc||'—', margin+26, y+13);
      doc.setFont('helvetica','bold'); doc.text('Teléfono:', margin+4, y+19);
      doc.setFont('helvetica','normal'); doc.text(cl.phone||'—', margin+22, y+19);
      doc.setFont('helvetica','bold'); doc.text('Correo:', margin+4, y+25);
      doc.setFont('helvetica','normal'); doc.text(cl.email||'—', margin+18, y+25);
    }
    y += clH + 2;

    // Fecha y categoría a la derecha
    const fmtD = s => { if(!s)return'—'; try{const d=new Date(s+'T12:00:00');return d.toLocaleDateString('es-PA',{day:'2-digit',month:'short',year:'numeric'});}catch{return s;} };
    doc.setFont('helvetica','bold'); doc.text('Fecha:', W-margin-60, y+7);
    doc.setFont('helvetica','normal'); doc.text(fmtD(data.date), W-margin-40, y+7);
    if (data.visit_date) {
      doc.setFont('helvetica','bold'); doc.text('Entrada:', W-margin-60, y+13);
      doc.setFont('helvetica','normal'); doc.text(fmtD(data.visit_date), W-margin-40, y+13);
    }
    if (data.visit_date_end) {
      doc.setFont('helvetica','bold'); doc.text('Salida:', W-margin-60, y+19);
      doc.setFont('helvetica','normal'); doc.text(fmtD(data.visit_date_end), W-margin-40, y+19);
    }
    if (data.categoria) {
      doc.setFont('helvetica','bold'); doc.text('Categoría:', W-margin-60, y+25);
      doc.setFont('helvetica','normal'); doc.text(data.categoria, W-margin-35, y+25);
    }
    y += 34;

    // ── En confirmación ───────────────────────────────────────────────────
    if (tipo === 'confirmacion') {
      // Banner — color según estado
      const estado = (data.estado || 'Confirmada');
      const bannerColor = estado==='Completada' ? success
                        : estado==='Cancelada'  ? [192,57,43]
                        : estado==='Aplazada'   ? [176,131,0]
                        : success; // Confirmada y resto en verde
      doc.setFillColor(...bannerColor);
      doc.roundedRect(margin, y, cW, 10, 2, 2, 'F');
      doc.setFont('helvetica','bold'); doc.setFontSize(10); doc.setTextColor(255,255,255);
      doc.text(`RESERVA ${estado.toUpperCase()} - #${quoteNum}`, margin+4, y+6.5);
      y += 14;

      // ── Ítems reservados ──────────────────────────────────────────────
      const items = data.items || [];
      if (items.length) {
        doc.setFont('helvetica','bold'); doc.setFontSize(9); doc.setTextColor(...dark);
        doc.text('Servicios reservados:', margin, y); y += 5;
        doc.setFillColor(244, 239, 230); doc.rect(margin, y, cW, 6, 'F');
        doc.setFont('helvetica','bold'); doc.setFontSize(7.5); doc.setTextColor(...dark);
        doc.text('Descripción', margin+3, y+4.2);
        doc.text('Cant.', margin+cW*0.55, y+4.2);
        doc.text('Precio', margin+cW*0.66, y+4.2);
        doc.text('Total', margin+cW*0.85, y+4.2);
        y += 6;
        items.forEach((it,i) => {
          const bg = i%2===0 ? [255,255,255] : [245,243,238];
          doc.setFillColor(...bg); doc.rect(margin, y, cW, 5.5, 'F');
          doc.setFont('helvetica','normal'); doc.setFontSize(8); doc.setTextColor(...dark);
          doc.text(String(it.desc||'').substring(0,38), margin+3, y+3.8);
          doc.text(String(it.qty||1), margin+cW*0.55, y+3.8);
          doc.text(`$${Number(it.price||0).toFixed(2)}`, margin+cW*0.66, y+3.8);
          doc.text(`$${Number(it.line_total||0).toFixed(2)}`, margin+cW*0.85, y+3.8);
          y += 5.5;
          if (y > 245) { doc.addPage(); y = 20; }
        });
        y += 5;
      }

      // ── Resumen financiero ────────────────────────────────────────────
      doc.setFont('helvetica','bold'); doc.setFontSize(9); doc.setTextColor(...dark);
      doc.text('Resumen de pagos:', margin, y); y += 5;

      const total    = data.total||0;
      const abono50  = data.abono_50 || total*.5;
      const abono    = data.abono_pagado||0;
      const cancel   = data.cancelacion_pagada||0;
      const recibido = abono + cancel;
      const saldo    = Math.max(0, total - recibido);
      const pct      = total > 0 ? Math.round(recibido/total*100) : 0;

      doc.setFillColor(238,244,245);
      doc.roundedRect(margin, y, cW, 40, 2, 2, 'F');

      const rows = [
        ['Total de la reserva',    `$${total.toFixed(2)}`,    dark],
        ['Abono requerido (50%)',  `$${abono50.toFixed(2)}`,  muted],
        ['Abono recibido',         `$${abono.toFixed(2)}`,    success],
        ['Cancelación recibida',   `$${cancel.toFixed(2)}`,   success],
        ['Total recibido',         `$${recibido.toFixed(2)}`, success],
        ['Saldo pendiente',        `$${saldo.toFixed(2)}`,    saldo===0?success:accent],
      ];
      let ry = y + 5;
      rows.forEach(([lbl,val,col]) => {
        doc.setFont('helvetica','normal'); doc.setFontSize(8.5); doc.setTextColor(...muted);
        doc.text(lbl, margin+4, ry);
        doc.setFont('helvetica','bold'); doc.setTextColor(...col);
        doc.text(val, W-margin-4, ry, {align:'right'});
        ry += 6;
      });
      y += 42;

      // Barra de progreso de pago
      doc.setDrawColor(200,200,200); doc.setLineWidth(0.3);
      doc.roundedRect(margin, y, cW, 4, 2, 2, 'D');
      const barW = Math.min(cW, cW * pct/100);
      if (barW > 0) {
        doc.setFillColor(...(pct>=100?success:pct>=50?[86,109,117]:accent));
        doc.roundedRect(margin, y, barW, 4, 2, 2, 'F');
      }
      doc.setFont('helvetica','normal'); doc.setFontSize(7.5); doc.setTextColor(...muted);
      doc.text(`${pct}% pagado`, W-margin-4, y+3, {align:'right'});
      y += 9;

      // ── Notas internas / observaciones ───────────────────────────────
      if (data.notas_internas) {
        y += 4;
        doc.setFont('helvetica','bold'); doc.setFontSize(9); doc.setTextColor(...dark);
        doc.text('Observaciones:', margin, y); y += 5;
        doc.setFont('helvetica','normal'); doc.setFontSize(8.5); doc.setTextColor(...muted);
        const lines = doc.splitTextToSize(data.notas_internas, cW);
        lines.forEach(line => {
          doc.text(line, margin, y); y += 5;
          if (y > 250) { doc.addPage(); y = 20; }
        });
      }
    } else {
      // ── Tabla de ítems (cotización) ────────────────────────────────────
      const items = data.items || [];
      if (items.length) {
        // Cabecera
        doc.setFillColor(244, 239, 230); doc.rect(margin, y, cW, 7, 'F');
        doc.setFont('helvetica','bold'); doc.setFontSize(8); doc.setTextColor(...dark);
        doc.text('Descripción', margin+3, y+5);
        doc.text('Cant.', margin+cW*0.55, y+5);
        doc.text('P. Unit.', margin+cW*0.65, y+5);
        doc.text('ITBMS', margin+cW*0.77, y+5);
        doc.text('Total', margin+cW*0.88, y+5);
        y += 7;
        items.forEach((it,i) => {
          const bg = i%2===0 ? [255,255,255] : [245,243,238];
          doc.setFillColor(...bg); doc.rect(margin, y, cW, 6, 'F');
          doc.setFont('helvetica','normal'); doc.setFontSize(8); doc.setTextColor(...dark);
          doc.text(it.desc||'', margin+3, y+4.5, {maxWidth: cW*0.5});
          doc.text(String(it.qty||1), margin+cW*0.55, y+4.5);
          doc.text(`$${Number(it.price||0).toFixed(2)}`, margin+cW*0.65, y+4.5);
          doc.text(`$${Number(it.itbms_amount||0).toFixed(2)}`, margin+cW*0.77, y+4.5);
          doc.text(`$${Number(it.line_total||0).toFixed(2)}`, margin+cW*0.88, y+4.5);
          y += 6;
          if (y > 240) { doc.addPage(); y = 20; }
        });
        y += 4;
      }

      // ── Totales ─────────────────────────────────────────────────────────
      const sub   = data.subtotal||0;
      const disc  = data.discount_amount||0;
      const i7    = data.itbms7_total||0;
      const i10   = data.itbms10_total||0;
      const total = data.total||0;
      const abono50 = data.abono_50||total*.5;
      const totRows = [
        ['Subtotal', `$${sub.toFixed(2)}`],
        ...(disc>0?[[data.discount_label||'Descuento', `-$${disc.toFixed(2)}`]]:[]),
        ...(i7>0?[['ITBMS 7%', `$${i7.toFixed(2)}`]]:[]),
        ...(i10>0?[['ITBMS 10%', `$${i10.toFixed(2)}`]]:[]),
      ];
      const xL = margin + cW*0.55;
      const xR = W - margin - 4;
      doc.setFontSize(9);
      totRows.forEach(([lbl,val]) => {
        doc.setFont('helvetica','normal'); doc.setTextColor(...muted);
        doc.text(lbl, xL, y); doc.text(val, xR, y, {align:'right'}); y+=5.5;
      });
      doc.setDrawColor(...accent); doc.setLineWidth(0.6); doc.line(xL, y, xR, y); y+=4;
      doc.setFont('helvetica','bold'); doc.setFontSize(11); doc.setTextColor(...accent);
      doc.text('TOTAL', xL, y); doc.text(`$${total.toFixed(2)}`, xR, y, {align:'right'}); y+=5;
      doc.setFont('helvetica','normal'); doc.setFontSize(9); doc.setTextColor(...[86,109,117]);
      doc.text('Abono requerido (50%)', xL, y+5); doc.text(`$${abono50.toFixed(2)}`, xR, y+5, {align:'right'}); y+=12;

      // ── Notas ────────────────────────────────────────────────────────────
      if (data.notes) {
        doc.setFont('helvetica','bold'); doc.setFontSize(9); doc.setTextColor(...dark);
        doc.text('Notas y Condiciones:', margin, y); y+=5;
        doc.setFont('helvetica','normal'); doc.setTextColor(...muted);
        const lines = doc.splitTextToSize(data.notes, cW);
        doc.text(lines, margin, y); y += lines.length*4.5+4;
      }
    }

    // ── Pie ───────────────────────────────────────────────────────────────
    doc.setFont('helvetica','normal'); doc.setFontSize(7.5); doc.setTextColor(...muted);
    const footer = tipo==='confirmacion'
      ? `Gracias por elegir ${emp.nombre||'Sanagua Lodge S.A.'}. ¡Esperamos recibirle pronto!`
      : `Esta cotización es válida hasta el ${fmtD(data.valid_until)}. Gracias por su confianza en ${emp.nombre||'Sanagua Lodge S.A.'}.`;
    doc.text(footer, W/2, 275, {align:'center', maxWidth: cW});

    // ── Descargar ─────────────────────────────────────────────────────────
    const clientName = data.client?.name || 'Cliente';
    const filename = tipo==='confirmacion'
      ? `Confirmación Sanagua Lodge ${quoteNum} ${clientName}.pdf`
      : `Cotización Sanagua Lodge #${quoteNum}.pdf`;
    doc.save(filename);
  }



  function fmtDateShort(d) {
    if(!d) return '—';
    try { return new Date(d.slice(0,10)+'T12:00:00').toLocaleDateString('es-PA',{day:'2-digit',month:'short',year:'numeric'}); }
    catch { return d.slice(0,10); }
  }
