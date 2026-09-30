// ── Nav panel admin — Sanagua Lodge v4
// Sidebar fijo en desktop, drawer en mobile.

(function () {
  if (document.getElementById('side-menu')) return;

  function buildMenuHtml() {
    return `
    <div class="side-menu-overlay" id="menu-overlay" onclick="closeMenu()"></div>
    <div class="side-menu" id="side-menu">

      <!-- Brand -->
      <div class="side-menu-brand">
        <div class="side-menu-brand-icon">
          <i class="fa-solid fa-leaf"></i>
        </div>
        <div>
          <div class="side-menu-brand-name">Sanagua Lodge</div>
          <div class="side-menu-brand-sub">Panel de gestión</div>
        </div>
      </div>

      <!-- Usuario -->
      <div class="side-menu-user" id="side-menu-user" style="display:none">
        <div class="side-menu-avatar">
          <i class="fa-solid fa-user"></i>
        </div>
        <div style="min-width:0">
          <div class="side-menu-user-name" id="menu-user-name">—</div>
          <span id="rol-badge" class="rol-badge" style="display:none;margin-top:3px"></span>
        </div>
      </div>

      <!-- Nav -->
      <nav>
        <button onclick="irA('achive.html')" style="font-weight:700">
          <i class="fa-solid fa-house"></i> Dashboard
        </button>

        <div class="side-menu-divider"></div>

        <button class="menu-group-btn" onclick="toggleMenuGroup('grp-reservas',this)">
          <span style="display:flex;align-items:center;gap:8px"><i class="fa-solid fa-calendar-days"></i> Reservas</span>
          <span class="menu-group-arrow">▾</span>
        </button>
        <div class="menu-group-items" id="grp-reservas">
          <button onclick="irA('calendario.html')"><i class="fa-solid fa-calendar-days"></i> Calendario</button>
          <button onclick="irA('nueva-cotizacion.html')"><i class="fa-solid fa-file-invoice"></i> Nueva cotización</button>
          <button onclick="irA('history.html')"><i class="fa-solid fa-box-archive"></i> Historial</button>
          <button onclick="irA('solicitudes.html')"><i class="fa-solid fa-inbox"></i> Solicitudes</button>
        </div>

        <div class="side-menu-divider"></div>

        <button class="menu-group-btn" onclick="toggleMenuGroup('grp-servicios',this)">
          <span style="display:flex;align-items:center;gap:8px"><i class="fa-solid fa-concierge-bell"></i> Servicios</span>
          <span class="menu-group-arrow">▾</span>
        </button>
        <div class="menu-group-items" id="grp-servicios">
          <button onclick="irA('mis-servicios.html')"><i class="fa-solid fa-tags"></i> Mis servicios</button>
          <button onclick="window.open('populares.html','_blank');closeMenu()"><i class="fa-solid fa-star"></i> Populares web</button>
          <button onclick="irA('menu-editor.html')"><i class="fa-solid fa-utensils"></i> Editor de menú</button>
        </div>

        <div class="side-menu-divider"></div>

        <button class="menu-group-btn" onclick="toggleMenuGroup('grp-sistema',this)">
          <span style="display:flex;align-items:center;gap:8px"><i class="fa-solid fa-gear"></i> Sistema</span>
          <span class="menu-group-arrow">▾</span>
        </button>
        <div class="menu-group-items" id="grp-sistema">
          <button onclick="irA('usuarios.html')"><i class="fa-solid fa-users"></i> Usuarios</button>
          <button onclick="irA('editor-sitio.html')"><i class="fa-solid fa-pen-ruler"></i> Editor del sitio</button>
          <button onclick="irA('configuracion.html')"><i class="fa-solid fa-gear"></i> Configuración</button>
        </div>
      </nav>

      <!-- Footer sidebar -->
      <div class="side-menu-footer">
        <button onclick="irComoUsuarioAdmin ? irComoUsuarioAdmin() : null" style="display:flex;align-items:center;gap:8px;width:100%;padding:10px 12px;background:none;border:none;color:rgba(255,255,255,.4);font-family:var(--font-sans);font-size:.8rem;cursor:pointer;border-radius:8px;transition:all .2s" onmouseover="this.style.background='rgba(255,255,255,.07)';this.style.color='rgba(255,255,255,.7)'" onmouseout="this.style.background='none';this.style.color='rgba(255,255,255,.4)'">
          <i class="fa-solid fa-eye"></i> Ver como usuario
        </button>
        <button onclick="cerrarSesionAdmin()" style="display:flex;align-items:center;gap:8px;width:100%;padding:10px 12px;background:none;border:none;color:rgba(220,100,100,.7);font-family:var(--font-sans);font-size:.8rem;cursor:pointer;border-radius:8px;transition:all .2s" onmouseover="this.style.background='rgba(220,100,100,.08)';this.style.color='rgba(220,100,100,.9)'" onmouseout="this.style.background='none';this.style.color='rgba(220,100,100,.7)'">
          <i class="fa-solid fa-right-from-bracket"></i> Cerrar sesión
        </button>
      </div>
    </div>`;
  }

  function injectTopbar() {
    // Hamburger para mobile en el topbar existente
    const header = document.querySelector('header, .hh-header');
    if (!header) return;
    const btn = document.createElement('button');
    btn.className = 'hamburger';
    btn.id = 'hamburger-btn';
    btn.setAttribute('aria-label', 'Menú');
    btn.innerHTML = '<span></span><span></span><span></span>';
    btn.onclick = () => toggleMenu();
    header.prepend(btn);
  }

  window.irA = function (pagina) {
    const actual = location.pathname.split('/').pop();
    if (actual === pagina) { closeMenu(); return; }
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
    sessionStorage.clear();
    localStorage.removeItem('stats_unlocked');
    localStorage.removeItem('poll_interval');
    if (window.supa) supa.auth.signOut().finally(() => { window.location.href = '../index.html'; });
    else window.location.href = '../index.html';
  };
  window.irComoUsuarioAdmin = function () {
    sessionStorage.setItem('admin_preview', '1');
    window.location.href = '../index.html';
  };

  function aplicarRolBadge() {
    const badge = document.getElementById('rol-badge');
    const userEl = document.getElementById('side-menu-user');
    const nameEl = document.getElementById('menu-user-name');
    if (!badge || !window.currentAdmin) return;
    const labels = {
      superadmin: '<i class="fa-solid fa-star"></i> Super Admin',
      admin:      '<i class="fa-solid fa-crown"></i> Admin',
      desarrollador: '<i class="fa-solid fa-screwdriver-wrench"></i> Dev',
    };
    const cls = { superadmin:'rol-super', admin:'rol-admin', desarrollador:'rol-dev' };
    badge.innerHTML = labels[window.currentAdmin.role] || window.currentAdmin.role;
    badge.className = `rol-badge ${cls[window.currentAdmin.role] || 'rol-admin'}`;
    badge.style.display = 'inline-flex';
    if (nameEl) nameEl.textContent = window.currentAdmin.name || window.currentAdmin.email;
    if (userEl) userEl.style.display = 'flex';
  }

  function init() {
    document.body.insertAdjacentHTML('afterbegin', buildMenuHtml());
    injectTopbar();
    document.addEventListener('keydown', e => { if (e.key === 'Escape') closeMenu(); });
    if (window.currentAdmin) aplicarRolBadge();
    document.addEventListener('admin-ready', () => aplicarRolBadge());
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
