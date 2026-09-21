// ── Carrito de reservas — Sanagua Lodge ─────────────────────────────────
// Incluir con <script src="[ruta]/assets/js/cart.js"></script> en cualquier
// página pública DESPUÉS de cargar @supabase/supabase-js.
//
// Uso desde una página (ej. picnic.html, pasadia.html):
//   SanaguaCart.add({
//     producto_id: null,              // uuid del producto en "Mis Servicios" si aplica
//     categoria: 'Picnic',            // texto libre, se usa como etiqueta
//     nombre: 'Tabla de Picnic Mediana',
//     precio: 48.00,
//     itbms: 7,
//     cantidad: 1,
//     fecha_visita: '2026-10-05',     // opcional (YYYY-MM-DD)
//     fecha_visita_fin: null,         // opcional, para rangos (camping/cabañas)
//     notas: '',                      // opcional, texto libre del cliente
//     puntos_fidelidad: 5,            // opcional, informativo para el cliente
//   });
//
// El carrito se guarda en localStorage y persiste entre páginas del sitio.

(function () {
  const SUPABASE_URL      = 'https://cjgdlskybcaacbpnncuw.supabase.co';
  const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNqZ2Rsc2t5YmNhYWNicG5uY3V3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQ4MTAwNjMsImV4cCI6MjEwMDM4NjA2M30.6UVRJBUxmLBo1ffTd7tZtfLald6Sm0qTmWi5Tx4HH98';
  if (!window.supabase) { console.error('cart.js requiere que @supabase/supabase-js esté cargado antes.'); return; }
  const supaCart = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

  const STORAGE_KEY = 'sanagua_cart';
  const INDEX_URL = (() => {
    // Detecta la profundidad de la página actual para volver a index.html
    const path = window.location.pathname;
    const depth = (path.match(/\/assets\/pages\//) ? path.split('/assets/pages/')[1].split('/').length - 1 : 0);
    return '../'.repeat(depth) + (path.includes('/assets/pages/') ? '../../index.html' : 'index.html');
  })();

  function getItems() {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || []; }
    catch { return []; }
  }
  function saveItems(items) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
    renderBadge();
  }
  function addItem(item) {
    const items = getItems();
    items.push({ cantidad: 1, itbms: 7, puntos_fidelidad: 0, ...item, id: `ci_${Date.now()}_${Math.random().toString(36).slice(2,7)}` });
    saveItems(items);
    abrirCarrito();
    mostrarToastCarrito(`<i class="fa-solid fa-circle-check"></i> "${item.nombre}" añadido al carrito.`);
  }
  function removeItem(id) {
    saveItems(getItems().filter(i => i.id !== id));
    renderDrawer();
  }
  function clearItems() { saveItems([]); renderDrawer(); }

  function calcularTotales(items) {
    let subtotal = 0, itbmsTotal = 0;
    items.forEach(it => {
      const base = (parseFloat(it.precio)||0) * (parseInt(it.cantidad)||1);
      subtotal += base;
      itbmsTotal += base * ((parseFloat(it.itbms)||0)/100);
    });
    return { subtotal, itbms: itbmsTotal, total: subtotal + itbmsTotal };
  }

  // ── UI: botón flotante + panel lateral ──────────────────────────────────
  function injectStyles() {
    const css = `
      #sc-fab{position:fixed;bottom:24px;right:24px;z-index:850;background:var(--moss,#7fa0ac);
        color:#fff;border:none;border-radius:50px;width:58px;height:58px;font-size:1.5rem;
        box-shadow:0 6px 20px rgba(0,0,0,.25);cursor:pointer;display:flex;align-items:center;
        justify-content:center;transition:transform .2s}
      #sc-fab:hover{transform:scale(1.06)}
      #sc-fab-count{position:absolute;top:-4px;right:-4px;background:#c0392b;color:#fff;
        font-size:.68rem;font-weight:700;border-radius:20px;min-width:20px;height:20px;
        display:flex;align-items:center;justify-content:center;padding:0 5px}
      #sc-overlay{position:fixed;inset:0;z-index:950;background:rgba(0,0,0,.55);backdrop-filter:blur(4px);
        display:none;align-items:stretch;justify-content:flex-end}
      #sc-overlay.show{display:flex}
      #sc-panel{background:#fff;width:100%;max-width:400px;height:100%;overflow-y:auto;
        box-shadow:-10px 0 40px rgba(0,0,0,.2);font-family:'DM Sans','Jost',sans-serif;
        display:flex;flex-direction:column}
      #sc-panel-head{background:var(--moss,#7fa0ac);color:#fff;padding:18px 22px;
        display:flex;align-items:center;justify-content:space-between}
      #sc-panel-head span{font-weight:700;font-size:1rem}
      #sc-panel-head button{background:none;border:none;color:rgba(255,255,255,.8);font-size:1.3rem;cursor:pointer}
      #sc-items{flex:1;padding:16px 20px;overflow-y:auto}
      .sc-item{display:flex;gap:10px;padding:12px 0;border-bottom:1px solid #eee}
      .sc-item-info{flex:1;min-width:0}
      .sc-item-nombre{font-weight:700;font-size:.88rem;color:#222}
      .sc-item-cat{font-size:.72rem;color:#888;text-transform:uppercase;letter-spacing:.04em}
      .sc-item-fecha{font-size:.76rem;color:#666;margin-top:2px}
      .sc-item-precio{font-weight:700;font-size:.88rem;color:#333;white-space:nowrap}
      .sc-item-del{background:none;border:none;color:#c0392b;cursor:pointer;font-size:.95rem;padding:4px}
      #sc-empty{text-align:center;color:#999;padding:40px 20px;font-size:.88rem}
      #sc-footer{padding:18px 20px;border-top:1px solid #eee}
      .sc-total-row{display:flex;justify-content:space-between;font-size:.85rem;color:#555;margin-bottom:4px}
      .sc-total-row.grand{font-weight:700;font-size:1.05rem;color:#222;margin-top:8px}
      #sc-submit{width:100%;background:var(--moss,#7fa0ac);color:#fff;border:none;border-radius:8px;
        padding:13px;font-weight:700;font-size:.92rem;cursor:pointer;margin-top:12px}
      #sc-submit:disabled{opacity:.6;cursor:default}
      #sc-notas{width:100%;padding:9px 12px;border:1.5px solid #ddd;border-radius:7px;font-size:.85rem;
        margin-top:10px;resize:vertical;min-height:50px;font-family:inherit}
      .sc-toast{position:fixed;bottom:24px;left:50%;transform:translateX(-50%) translateY(20px);
        background:#222;color:#fff;padding:12px 22px;border-radius:8px;font-size:.85rem;
        opacity:0;pointer-events:none;transition:all .3s;z-index:1000;max-width:90vw;text-align:center}
      .sc-toast.show{opacity:1;transform:translateX(-50%) translateY(0)}
    `;
    const style = document.createElement('style');
    style.textContent = css;
    document.head.appendChild(style);
  }

  function injectDom() {
    const fab = document.createElement('button');
    fab.id = 'sc-fab';
    fab.innerHTML = `<i class="fa-solid fa-cart-shopping"></i><span id="sc-fab-count" style="display:none">0</span>`;
    fab.onclick = abrirCarrito;
    document.body.appendChild(fab);

    const overlay = document.createElement('div');
    overlay.id = 'sc-overlay';
    overlay.innerHTML = `
      <div id="sc-panel">
        <div id="sc-panel-head"><span><i class="fa-solid fa-cart-shopping"></i> Tu carrito</span><button id="sc-close"><i class="fa-solid fa-xmark"></i></button></div>
        <div id="sc-items"></div>
        <div id="sc-footer">
          <textarea id="sc-notas" placeholder="Notas para tu reserva (opcional)"></textarea>
          <div class="sc-total-row"><span>Subtotal</span><span id="sc-subtotal">$0.00</span></div>
          <div class="sc-total-row"><span>ITBMS</span><span id="sc-itbms">$0.00</span></div>
          <div class="sc-total-row grand"><span>Total</span><span id="sc-total">$0.00</span></div>
          <button id="sc-submit">Enviar solicitud de reserva</button>
        </div>
      </div>`;
    document.body.appendChild(overlay);
    overlay.addEventListener('click', e => { if (e.target === overlay) cerrarCarrito(); });
    document.getElementById('sc-close').onclick = cerrarCarrito;
    document.getElementById('sc-submit').onclick = enviarSolicitud;

    const toast = document.createElement('div');
    toast.className = 'sc-toast';
    toast.id = 'sc-toast';
    document.body.appendChild(toast);
  }

  function mostrarToastCarrito(msg) {
    const t = document.getElementById('sc-toast');
    if (!t) return;
    t.textContent = msg;
    t.classList.add('show');
    clearTimeout(t._tt);
    t._tt = setTimeout(() => t.classList.remove('show'), 3500);
  }

  function renderBadge() {
    const items = getItems();
    const el = document.getElementById('sc-fab-count');
    if (!el) return;
    if (items.length) { el.textContent = items.length; el.style.display = 'flex'; }
    else { el.style.display = 'none'; }
  }

  function renderDrawer() {
    const items = getItems();
    const cont = document.getElementById('sc-items');
    if (!items.length) {
      cont.innerHTML = `<div id="sc-empty"><i class="fa-solid fa-bag-shopping"></i><br>Tu carrito está vacío.<br>Agrega una pasadía, cabaña, tabla de picnic o lo que quieras reservar.</div>`;
    } else {
      cont.innerHTML = items.map(it => `
        <div class="sc-item">
          <div class="sc-item-info">
            <div class="sc-item-cat">${(it.categoria||'').toString()}</div>
            <div class="sc-item-nombre">${it.nombre} ${it.cantidad>1?`× ${it.cantidad}`:''}</div>
            ${it.fecha_visita ? `<div class="sc-item-fecha"><i class="fa-solid fa-calendar-days"></i> ${it.fecha_visita}${it.fecha_visita_fin && it.fecha_visita_fin!==it.fecha_visita ? ' → '+it.fecha_visita_fin : ''}</div>` : ''}
          </div>
          <div style="display:flex;flex-direction:column;align-items:flex-end;gap:6px">
            <span class="sc-item-precio">$${((parseFloat(it.precio)||0)*(it.cantidad||1)).toFixed(2)}</span>
            <button class="sc-item-del" onclick="SanaguaCart.remove('${it.id}')"><i class="fa-solid fa-trash"></i></button>
          </div>
        </div>`).join('');
    }
    const t = calcularTotales(items);
    document.getElementById('sc-subtotal').textContent = `$${t.subtotal.toFixed(2)}`;
    document.getElementById('sc-itbms').textContent    = `$${t.itbms.toFixed(2)}`;
    document.getElementById('sc-total').textContent    = `$${t.total.toFixed(2)}`;
    document.getElementById('sc-submit').disabled = !items.length;
    renderBadge();
  }

  async function abrirCarrito() {
    const { data: { session } } = await supaCart.auth.getSession();
    if (!session) {
      mostrarToastCarrito('<i class="fa-solid fa-triangle-exclamation"></i> Inicia sesión para ver tu carrito.');
      setTimeout(() => { window.location.href = `${INDEX_URL}?action=login`; }, 1200);
      return;
    }
    renderDrawer();
    document.getElementById('sc-overlay').classList.add('show');
  }
  function cerrarCarrito() { document.getElementById('sc-overlay').classList.remove('show'); }

  // Número de WhatsApp del lodge donde llegan las notificaciones de reserva.
  const WHATSAPP_NUMBER = '50766000000';

  async function enviarSolicitud() {
    const items = getItems();
    if (!items.length) return;
    const btn = document.getElementById('sc-submit');

    const { data: { session } } = await supaCart.auth.getSession();
    if (!session) {
      mostrarToastCarrito('<i class="fa-solid fa-triangle-exclamation"></i> Inicia sesión para enviar tu solicitud de reserva.');
      setTimeout(() => { window.location.href = `${INDEX_URL}?action=login`; }, 1200);
      return;
    }

    btn.disabled = true; btn.textContent = 'Enviando...';
    try {
      const { data: profile } = await supaCart.from('profiles')
        .select('name, email, phone, cedula, edad, verificado').eq('id', session.user.id).single();

      const t = calcularTotales(items);
      const notas = document.getElementById('sc-notas').value.trim();
      const contacto = {
        nombre: profile?.name || '', email: profile?.email || session.user.email,
        telefono: profile?.phone || '', cedula: profile?.cedula || '', edad: profile?.edad || null,
        verificado: !!profile?.verificado,
      };

      const { error } = await supaCart.from('solicitudes').insert({
        user_id: session.user.id,
        items: items.map(({id, ...rest}) => rest), // no persistimos el id local del carrito
        estado: 'pendiente',
        subtotal: Math.round(t.subtotal*100)/100,
        itbms: Math.round(t.itbms*100)/100,
        total: Math.round(t.total*100)/100,
        notas_cliente: notas,
        contacto,
      });
      if (error) throw error;

      // Notificar por WhatsApp — el cliente ya no escribe sus datos a mano,
      // se toman directo de su perfil verificado.
      const detalle = items.map(it => `• ${it.categoria ? it.categoria+': ' : ''}${it.nombre}${it.cantidad>1?` × ${it.cantidad}`:''}${it.fecha_visita?` (📅 ${it.fecha_visita}${it.fecha_visita_fin && it.fecha_visita_fin!==it.fecha_visita?' → '+it.fecha_visita_fin:''})`:''}`).join('\n');
      const msg = encodeURIComponent(
        `Hola Sanagua Lodge! Quiero hacer la siguiente solicitud de reserva:\n\n${detalle}\n\n`+
        `💰 Total: $${t.total.toFixed(2)}\n`+
        `👤 ${contacto.nombre}${contacto.verificado?' ✓ (verificado)':''}\n`+
        `🪪 ${contacto.cedula||'—'}\n`+
        `📱 ${contacto.telefono||'—'}\n📧 ${contacto.email}`+
        `${notas?`\n📝 Notas: ${notas}`:''}`
      );
      window.open(`https://wa.me/${WHATSAPP_NUMBER}?text=${msg}`, '_blank');

      clearItems();
      cerrarCarrito();
      mostrarToastCarrito('<i class="fa-solid fa-circle-check"></i> ¡Solicitud enviada! Podrás ver su estado en tu perfil.');
    } catch (e) {
      console.error(e);
      mostrarToastCarrito('<i class="fa-solid fa-circle-xmark"></i> No se pudo enviar la solicitud. Intenta de nuevo.');
    } finally {
      btn.disabled = false; btn.textContent = 'Enviar solicitud de reserva';
    }
  }

  function init() {
    injectStyles();
    injectDom();
    renderBadge();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();

  window.SanaguaCart = {
    add: addItem,
    remove: removeItem,
    clear: clearItems,
    items: getItems,
    open: abrirCarrito,
    close: cerrarCarrito,
  };
})();
