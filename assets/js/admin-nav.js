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

        <button onclick="irA('achive.html')" style="font-weight:700"><i class="fa-solid fa-house"></i> Dashboard</button>

        <button class="menu-group-btn" onclick="toggleMenuGroup('grp-reservas',this)">
          📅 Reservas <span class="menu-group-arrow">▼</span>
        </button>
        <div class="menu-group-items" id="grp-reservas">
          <button onclick="irA('calendario.html')"><i class="fa-solid fa-calendar-days"></i> Calendario</button>
          <button onclick="irA('nueva-cotizacion.html')"><i class="fa-solid fa-file-invoice"></i> Nueva Cotización</button>
          <button onclick="irA('history.html')"><i class="fa-solid fa-box-archive"></i> Historial</button>
          <button onclick="irA('resumen.html')"><i class="fa-solid fa-chart-column"></i> Resumen</button>
          <button onclick="irA('solicitudes.html')"><i class="fa-solid fa-inbox"></i> Solicitudes</button>
        </div>

        <div class="side-menu-divider"></div>

        <button class="menu-group-btn" onclick="toggleMenuGroup('grp-servicios',this)">
          <i class="fa-solid fa-concierge-bell"></i> Mis Servicios <span class="menu-group-arrow">▼</span>
        </button>
        <div class="menu-group-items" id="grp-servicios">
          <button onclick="irA('mis-servicios.html')"><i class="fa-solid fa-concierge-bell"></i> Mis Servicios</button>
          <button onclick="window.open('populares.html','_blank');closeMenu()"><i class="fa-solid fa-star"></i> Populares Web</button>
          <button onclick="irA('menu-editor.html')"><i class="fa-solid fa-utensils"></i> Editor de Menú Web</button>
        </div>

        <div class="side-menu-divider"></div>

        <button class="menu-group-btn" onclick="toggleMenuGroup('grp-sistema',this)">
          ⚙️ Sistema <span class="menu-group-arrow">▼</span>
        </button>
        <div class="menu-group-items" id="grp-sistema">
          <button onclick="irA('usuarios.html')"><i class="fa-solid fa-users"></i> Usuarios</button>
          <button onclick="irA('configuracion.html')"><i class="fa-solid fa-gear"></i> Configuración</button>
        </div>

        <div class="side-menu-divider"></div>
        <button onclick="cerrarSesionAdmin()" style="color:#e88;"><i class="fa-solid fa-right-from-bracket"></i> Cerrar sesión</button>
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

  window.irA = function (pagina) {
    const actual = location.pathname.split('/').pop();
    if (actual === pagina) { closeMenu(); return; } // ya estás aquí — no recargar
    location.href = pagina;
  };

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
    const roleLabels = { superadmin:'<i class="fa-solid fa-star"></i> Super Admin', admin:'<i class="fa-solid fa-crown"></i> Admin', desarrollador:'<i class="fa-solid fa-screwdriver-wrench"></i> Desarrollador' };
    const roleCls    = { superadmin:'rol-super', admin:'rol-admin', desarrollador:'rol-dev' };
    badge.innerHTML = roleLabels[window.currentAdmin.role] || window.currentAdmin.role;
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
