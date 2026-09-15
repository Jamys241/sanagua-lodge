// ── Navegación compartida — Sanagua Lodge ───────────────────────────────
// Incluir con <script src="[ruta]/assets/js/site-nav.js"></script> en
// cualquier página pública, DESPUÉS de cargar @supabase/supabase-js.
// Agrega un botón de hamburguesa y un panel lateral (Servicios + Mi cuenta)
// consistentes en toda la web — antes cada página tenía su propio botón de
// "Reservar" con una clase distinta y ninguna mostraba el estado de sesión.
//
// No reemplaza el <nav> de cada página (logo + "← volver" siguen igual);
// solo le añade el botón de menú.
//
// index.html ya tiene su propio sistema de menú lateral más completo (hero,
// tagline, etc.) — este script se desactiva solo ahí para no duplicarlo.

(function () {
  if (document.getElementById('hamburger')) return; // index.html ya tiene el suyo

  const SUPABASE_URL      = 'https://cjgdlskybcaacbpnncuw.supabase.co';
  const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNqZ2Rsc2t5YmNhYWNicG5uY3V3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQ4MTAwNjMsImV4cCI6MjEwMDM4NjA2M30.6UVRJBUxmLBo1ffTd7tZtfLald6Sm0qTmWi5Tx4HH98';
  if (!window.supabase) { console.error('site-nav.js requiere que @supabase/supabase-js esté cargado antes.'); return; }
  const supaNav = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

  // ── Rutas relativas ──────────────────────────────────────────────────
  // En vez de adivinar la profundidad a partir de location.pathname (que
  // se rompe al abrir los archivos con file:// o si el sitio se sirve
  // desde una subcarpeta), leemos el href que ya tiene el logo "🌿 Sanagua
  // Lodge" de cada página — ese siempre apunta correctamente a index.html.
  function computeRoot() {
    const logo = document.querySelector('nav .nav-logo, nav a[href$="index.html"]');
    if (logo) {
      const href = logo.getAttribute('href');
      const idx  = href.lastIndexOf('index.html');
      if (idx !== -1) return href.slice(0, idx);
    }
    // Fallback: calcular por profundidad de carpetas (menos confiable)
    const path  = window.location.pathname;
    const dir   = path.substring(0, path.lastIndexOf('/'));
    const parts = dir.split('/').filter(Boolean);
    return '../'.repeat(parts.length);
  }
  const ROOT = computeRoot();
  const LINKS = {
    inicio:      ROOT + 'index.html',
    pasadia:     ROOT + 'assets/pages/pasadia.html',
    camping:     ROOT + 'assets/pages/camping.html',
    cabanas:     ROOT + 'assets/pages/cabanas.html',
    restaurante: ROOT + 'assets/pages/restaurante.html',
    sobre:       ROOT + 'index.html#sobre',
    experiencias:ROOT + 'index.html#experiencias',
    contacto:    ROOT + 'index.html#footer',
    login:       ROOT + 'index.html?action=login',
    registro:    ROOT + 'index.html?action=register',
  };

  function injectStyles() {
    const css = `
      .sn-hamburger{background:none;border:none;width:34px;height:34px;display:flex;
        flex-direction:column;align-items:center;justify-content:center;gap:5px;
        cursor:pointer;margin-left:16px;flex-shrink:0;padding:0}
      .sn-hamburger span{display:block;width:21px;height:2px;background:#fff;border-radius:2px;
        transition:transform .25s,opacity .25s}
      .sn-hamburger.open span:nth-child(1){transform:translateY(7px) rotate(45deg)}
      .sn-hamburger.open span:nth-child(2){opacity:0}
      .sn-hamburger.open span:nth-child(3){transform:translateY(-7px) rotate(-45deg)}

      .sn-overlay{position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:940;
        opacity:0;pointer-events:none;transition:opacity .3s}
      .sn-overlay.open{opacity:1;pointer-events:auto}
      .sn-drawer{position:fixed;top:0;right:-320px;width:min(320px,86vw);height:100%;
        background:#12181b;z-index:941;transition:right .35s cubic-bezier(.4,0,.2,1);
        overflow-y:auto;box-shadow:-10px 0 40px rgba(0,0,0,.35);font-family:'Jost',sans-serif;
        display:block}
      .sn-drawer.open{right:0}
      .sn-drawer-user{background:linear-gradient(135deg,var(--moss,#7fa0ac),var(--water,#566d75));
        padding:26px 24px;color:#fff}
      .sn-drawer-user-name{font-family:'Cormorant Garamond',serif;font-size:1.25rem;
        display:flex;align-items:center;gap:6px}
      .sn-drawer-user-pts{font-size:.78rem;opacity:.9;margin-top:4px}
      .sn-section-label{font-size:.66rem;font-weight:700;letter-spacing:.12em;
        text-transform:uppercase;color:rgba(255,255,255,.35);padding:18px 24px 8px}
      .sn-item{display:flex;align-items:center;gap:10px;padding:12px 24px;color:rgba(255,255,255,.88);
        text-decoration:none;font-size:.88rem;border:none;background:none;width:100%;
        text-align:left;cursor:pointer;font-family:'Jost',sans-serif}
      .sn-item:hover{background:rgba(255,255,255,.06);color:#fff}
      .sn-divider{height:1px;background:rgba(255,255,255,.08);margin:8px 0}
      .sn-auth-btns{padding:6px 24px 22px;display:flex;flex-direction:column;gap:9px}
      .sn-btn-primary{background:var(--moss,#7fa0ac);color:#fff;border:none;border-radius:8px;
        padding:12px;font-weight:700;cursor:pointer;font-family:'Jost',sans-serif;font-size:.86rem}
      .sn-btn-outline{background:none;border:1.5px solid rgba(255,255,255,.25);border-radius:8px;
        padding:11px;cursor:pointer;font-family:'Jost',sans-serif;font-size:.86rem;color:#fff}
      .sn-close{position:absolute;top:16px;right:16px;background:rgba(255,255,255,.2);
        border:none;width:30px;height:30px;border-radius:50%;color:#fff;cursor:pointer;
        display:flex;align-items:center;justify-content:center;font-size:1rem}
    `;
    const style = document.createElement('style');
    style.textContent = css;
    document.head.appendChild(style);
  }

  function badgeVerificado() {
    return '<span title="Cuenta verificada" style="display:inline-flex;align-items:center;justify-content:center;width:15px;height:15px;background:#3d8bfd;border-radius:50%;"><svg viewBox="0 0 24 24" style="width:9px;height:9px;fill:none;stroke:#fff;stroke-width:3.5;stroke-linecap:round;stroke-linejoin:round;"><polyline points="20 6 9 17 4 12"></polyline></svg></span>';
  }

  async function buildDrawerContent(profile) {
    const serviciosHtml = `
      <div class="sn-section-label">Servicios</div>
      <a class="sn-item" href="${LINKS.pasadia}">☀️ Pasadías</a>
      <a class="sn-item" href="${LINKS.camping}">⛺ Camping</a>
      <a class="sn-item" href="${LINKS.cabanas}">🏡 Cabañas</a>
      <a class="sn-item" href="${LINKS.restaurante}">🍽️ Restaurante</a>
      <div class="sn-divider"></div>
      <div class="sn-section-label">Explorar</div>
      <a class="sn-item" href="${LINKS.inicio}">🌿 Inicio</a>
      <a class="sn-item" href="${LINKS.sobre}">🌱 Sobre Sanagua</a>
      <a class="sn-item" href="${LINKS.experiencias}">📸 Experiencias</a>
      <a class="sn-item" href="${LINKS.contacto}">📍 Contacto</a>`;

    if (profile) {
      return `
        <div class="sn-drawer-user">
          <button class="sn-close" onclick="SanaguaNav.close()">✕</button>
          <div class="sn-drawer-user-name">${profile.name || 'Mi cuenta'}${profile.verificado?badgeVerificado():''}</div>
          <div class="sn-drawer-user-pts">✦ ${profile.puntos||0} puntos de fidelidad</div>
        </div>
        ${serviciosHtml}
        <div class="sn-divider"></div>
        <div class="sn-section-label">Mi cuenta</div>
        <a class="sn-item" href="${LINKS.inicio}">👤 Mi perfil y reservas</a>
        <button class="sn-item" style="color:#c0392b" onclick="SanaguaNav.logout()">🚪 Cerrar sesión</button>`;
    }
    return `
      <div class="sn-drawer-user" style="background:linear-gradient(135deg,#8a8a82,#5a5a54)">
        <button class="sn-close" onclick="SanaguaNav.close()">✕</button>
        <div class="sn-drawer-user-name">Sanagua Lodge</div>
        <div class="sn-drawer-user-pts">Inicia sesión para reservar</div>
      </div>
      ${serviciosHtml}
      <div class="sn-divider"></div>
      <div class="sn-auth-btns">
        <a class="sn-btn-primary" style="text-align:center;text-decoration:none;display:block" href="${LINKS.registro}">Hacer una reserva</a>
        <a class="sn-btn-outline" style="text-align:center;text-decoration:none;display:block" href="${LINKS.login}">Iniciar sesión</a>
      </div>`;
  }

  function injectDom() {
    const overlay = document.createElement('div');
    overlay.className = 'sn-overlay';
    overlay.id = 'sn-overlay';
    overlay.onclick = () => window.SanaguaNav.close();
    document.body.appendChild(overlay);

    const drawer = document.createElement('div');
    drawer.className = 'sn-drawer';
    drawer.id = 'sn-drawer';
    drawer.innerHTML = '<div style="padding:40px 24px;color:#999;font-size:.85rem;">Cargando...</div>';
    document.body.appendChild(drawer);

    // Botón de hamburguesa dentro del <nav> existente de la página
    const nav = document.querySelector('nav');
    if (nav) {
      const btn = document.createElement('button');
      btn.className = 'sn-hamburger';
      btn.id = 'sn-hamburger';
      btn.setAttribute('aria-label', 'Menú');
      btn.innerHTML = '<span></span><span></span><span></span>';
      btn.onclick = () => window.SanaguaNav.toggle();
      let right = nav.querySelector('.nav-right');
      if (!right) { right = document.createElement('div'); right.className = 'nav-right'; right.style.cssText='display:flex;align-items:center;gap:14px'; nav.appendChild(right); }
      right.appendChild(btn);
    }
  }

  async function refrescar() {
    let profile = null;
    try {
      const { data: { session } } = await supaNav.auth.getSession();
      if (session) {
        const { data } = await supaNav.from('profiles').select('name, puntos, verificado').eq('id', session.user.id).single();
        profile = data;
      }
    } catch (e) { console.warn('site-nav', e); }
    document.getElementById('sn-drawer').innerHTML = await buildDrawerContent(profile);
  }

  function open()  { document.getElementById('sn-overlay').classList.add('open'); document.getElementById('sn-drawer').classList.add('open'); document.getElementById('sn-hamburger')?.classList.add('open'); }
  function close() { document.getElementById('sn-overlay').classList.remove('open'); document.getElementById('sn-drawer').classList.remove('open'); document.getElementById('sn-hamburger')?.classList.remove('open'); }
  function toggle(){ document.getElementById('sn-drawer').classList.contains('open') ? close() : open(); }
  async function logout() { await supaNav.auth.signOut(); window.location.href = LINKS.inicio; }

  function init() {
    injectStyles();
    injectDom();
    refrescar();
    supaNav.auth.onAuthStateChange(() => refrescar());
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();

  window.SanaguaNav = { open, close, toggle, logout };
})();
