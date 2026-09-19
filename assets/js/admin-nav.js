// ── Menú de navegación del panel admin — compartido entre todas las
// páginas hijas de achive.html (calendario, historial, nueva cotización,
// resumen, solicitudes, configuración, usuarios). No lo incluye achive.html
// mismo, que ya trae su propio menú (idéntico a éste).
//
// Requiere: que la página ya tenga `supa` (cliente de Supabase) declarado
// como variable global antes de que el usuario haga clic en algo — esto
// script solo arma el HTML/CSS al cargar, no toca `supa` hasta el clic.

(function () {
  if (document.getElementById('side-menu')) return; // ya tiene su propio menú (achive.html)

  function injectStyles() {
    // Las clases (.side-menu, .hamburger, .menu-group-btn, etc.) ya viven
    // en achive.css, que todas estas páginas cargan. Solo agregamos lo
    // específico del botón que reemplaza al header viejo.
    const css = `
      .hh-hamburger{background:none;border:none;width:30px;height:24px;position:relative;cursor:pointer;flex-shrink:0}
      .hh-hamburger span{position:absolute;left:0;right:0;height:2px;background:#fff;border-radius:2px;transition:transform .25s,opacity .25s}
      .hh-hamburger span:nth-child(1){top:2px}
      .hh-hamburger span:nth-child(2){top:11px}
      .hh-hamburger span:nth-child(3){top:20px}
      .hh-hamburger.open span:nth-child(1){transform:translateY(9px) rotate(45deg)}
      .hh-hamburger.open span:nth-child(2){opacity:0}
      .hh-hamburger.open span:nth-child(3){transform:translateY(-9px) rotate(-45deg)}

      /* En PC el menú queda siempre visible (regla compartida en
         achive.css) — aquí solo ocultamos este botón, ya que usa una
         clase propia distinta al .hamburger de achive.html. */
      @media (min-width: 900px) {
        .hh-hamburger { display: none !important; }
      }
    `;
    const style = document.createElement('style');
    style.textContent = css;
    document.head.appendChild(style);
  }

  function buildMenuHtml() {
    return `
    <div class="side-menu-overlay" id="menu-overlay" onclick="closeMenu()"></div>
    <div class="side-menu" id="side-menu">
      <nav>
        <div style="padding:16px 24px 6px;">
          <span id="rol-badge" class="rol-badge" style="display:none"></span>
        </div>

        <button onclick="location.href='achive.html'" style="font-weight:700">🏠 Dashboard</button>

        <button class="menu-group-btn" onclick="toggleMenuGroup('grp-reservas',this)">
          📅 Reservas <span class="menu-group-arrow">▼</span>
        </button>
        <div class="menu-group-items" id="grp-reservas">
          <button onclick="location.href='calendario.html'">📅 Calendario</button>
          <button onclick="location.href='nueva-cotizacion.html'">📋 Nueva Cotización</button>
          <button onclick="location.href='history.html'">📁 Historial</button>
          <button onclick="location.href='resumen.html'">📊 Resumen</button>
          <button onclick="location.href='solicitudes.html'">📬 Solicitudes</button>
        </div>

        <div class="side-menu-divider"></div>

        <button class="menu-group-btn" onclick="toggleMenuGroup('grp-servicios',this)">
          🛎️ Mis Servicios <span class="menu-group-arrow">▼</span>
        </button>
        <div class="menu-group-items" id="grp-servicios">
          <button onclick="window.open('mis-servicios.html','_blank');closeMenu()">🛎️ Mis Servicios</button>
          <button onclick="window.open('populares.html','_blank');closeMenu()">⭐ Populares Web</button>
          <button onclick="window.open('menu-editor.html','_blank');closeMenu()">🍽️ Editor de Menú Web</button>
        </div>

        <div class="side-menu-divider"></div>

        <button class="menu-group-btn" onclick="toggleMenuGroup('grp-sistema',this)">
          ⚙️ Sistema <span class="menu-group-arrow">▼</span>
        </button>
        <div class="menu-group-items" id="grp-sistema">
          <button onclick="location.href='usuarios.html'">👥 Usuarios</button>
          <button onclick="location.href='configuracion.html'">⚙️ Configuración</button>
        </div>

        <div class="side-menu-divider"></div>
        <button onclick="cerrarSesionAdmin()" style="color:#e88;">🚪 Cerrar sesión</button>
      </nav>
      <div style="padding:12px 24px 16px;font-size:.75rem;color:#666;" id="menu-user-info"></div>
    </div>`;
  }

  function injectDom() {
    document.body.insertAdjacentHTML('afterbegin', buildMenuHtml());

    // Reemplazar el enlace "← Volver al sistema" del header de la página
    // por un botón de hamburguesa que abre este mismo menú.
    const backLink = document.querySelector('.hh-header a[href="achive.html"]');
    if (backLink) {
      const btn = document.createElement('button');
      btn.className = 'hh-hamburger';
      btn.id = 'hamburger-btn';
      btn.setAttribute('aria-label', 'Menú');
      btn.innerHTML = '<span></span><span></span><span></span>';
      btn.onclick = () => toggleMenu();
      backLink.replaceWith(btn);
    }
  }

  window.toggleMenu = function () {
    document.getElementById('hamburger-btn')?.classList.toggle('open');
    document.getElementById('side-menu').classList.toggle('open');
    document.getElementById('menu-overlay').classList.toggle('open');
  };
  window.closeMenu = function () {
    document.getElementById('hamburger-btn')?.classList.remove('open');
    document.getElementById('side-menu').classList.remove('open');
    document.getElementById('menu-overlay').classList.remove('open');
  };
  window.toggleMenuGroup = function (id, btn) {
    const items = document.getElementById(id);
    const isOpen = items.classList.contains('open');
    document.querySelectorAll('.menu-group-items').forEach(el => el.classList.remove('open'));
    document.querySelectorAll('.menu-group-btn').forEach(el => el.classList.remove('open'));
    if (!isOpen) { items.classList.add('open'); btn.classList.add('open'); }
  };
  window.cerrarSesionAdmin = function () {
    if (!confirm('¿Cerrar sesión?')) return;
    supa.auth.signOut().finally(() => { window.location.href = '../index.html'; });
  };

  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeMenu(); });

  function aplicarRolBadge() {
    const badge = document.getElementById('rol-badge');
    if (!badge || !window.currentAdmin) return;
    const roleLabels = { superadmin:'⭐ Super Admin', admin:'👑 Admin', desarrollador:'🛠️ Desarrollador' };
    const roleCls    = { superadmin:'rol-super', admin:'rol-admin', desarrollador:'rol-dev' };
    badge.textContent = roleLabels[window.currentAdmin.role] || window.currentAdmin.role;
    badge.className = `rol-badge ${roleCls[window.currentAdmin.role]||'rol-admin'}`;
    badge.style.display = 'inline-block';
  }

  function init() {
    injectStyles();
    injectDom();
    if (window.currentAdmin) {
      document.getElementById('menu-user-info').textContent =
        `${window.currentAdmin.name || window.currentAdmin.email} · ${window.currentAdmin.role}`;
      aplicarRolBadge();
    }
    document.addEventListener('admin-ready', () => {
      document.getElementById('menu-user-info').textContent =
        `${window.currentAdmin.name || window.currentAdmin.email} · ${window.currentAdmin.role}`;
      aplicarRolBadge();
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
