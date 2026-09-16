// ── Guard de sesión para el panel de administración (Supabase Auth) ─────
// Incluir con <script src=".../assets/js/admin-guard.js"></script> DESPUÉS
// de cargar @supabase/supabase-js. Al terminar de verificar, dispara el
// evento 'admin-ready' en `document` con { detail: currentAdmin } si todo
// está en orden, o redirige a index.html si no hay sesión de admin válida.
//
// Expone:
//   window.currentAdmin   → { id, email, name, role, permisos, accessToken }
//   window.authFetch(url, opts) → fetch con el JWT del admin ya adjunto

(function () {
  // Si esta página se restaura desde el bfcache del navegador (botón
  // "atrás"/"adelante"), forzamos una recarga real para que la sesión se
  // vuelva a verificar — evita que, tras cerrar sesión, "atrás" muestre el
  // panel tal como quedó congelado, sin re-chequear si sigue siendo válido.
  window.addEventListener('pageshow', (e) => {
    if (e.persisted) window.location.reload();
  });

  const SUPABASE_URL      = 'https://cjgdlskybcaacbpnncuw.supabase.co';
  const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNqZ2Rsc2t5YmNhYWNicG5uY3V3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQ4MTAwNjMsImV4cCI6MjEwMDM4NjA2M30.6UVRJBUxmLBo1ffTd7tZtfLald6Sm0qTmWi5Tx4HH98';
  // URL del backend Flask (app.py). Este proyecto ya no usa Render.
  // Mientras corras app.py en tu máquina, esto debe apuntar a localhost.
  // Cuando decidas dónde desplegarlo, cambia este valor (y el mismo en
  // sanagua-cot/achive.html) por la URL real.
  const API_BASE = 'http://localhost:5000';

  if (!window.supabase) {
    console.error('admin-guard.js requiere que @supabase/supabase-js esté cargado antes.');
    return;
  }
  const supaGuard = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

  function urlIndex() {
    // Funciona sin importar la profundidad (sanagua-cot/ o sanagua-cot/page/)
    const base = window.location.href.split('/sanagua-cot/')[0];
    return base + '/index.html';
  }

  function irAIndex() {
    window.location.href = urlIndex();
  }

  window.authFetch = function (url, options = {}) {
    const headers = { ...(options.headers || {}), 'Authorization': `Bearer ${window.currentAdmin?.accessToken || ''}` };
    return fetch(url, { ...options, headers });
  };

  (async function verificar() {
    try {
      // Espera a que supabase-js termine de leer la sesión guardada en
      // localStorage antes de decidir que "no hay sesión". En una pestaña
      // recién abierta (ej. al hacer clic en "Editor de Menú" o
      // "Mis Productos"), getSession() a veces se resuelve antes de que
      // el cliente termine de hidratarse — este pequeño margen evita un
      // falso negativo que mandaría al admin de vuelta al index.
      let { data: { session } } = await supaGuard.auth.getSession();
      if (!session) {
        session = await new Promise(resolve => {
          const { data: sub } = supaGuard.auth.onAuthStateChange((event, s) => {
            if (event === 'INITIAL_SESSION' || s) { sub.subscription.unsubscribe(); resolve(s); }
          });
          setTimeout(() => { sub.subscription.unsubscribe(); resolve(null); }, 1500);
        });
      }
      if (!session) {
        console.warn('admin-guard: no hay sesión activa de Supabase Auth — redirigiendo a index.');
        irAIndex();
        return;
      }

      // Leemos el profile directamente de Supabase (protegido por RLS).
      // No depende de que el backend Flask esté desplegado — el backend
      // sigue protegiendo cada acción de escritura por su cuenta.
      const { data: { user } } = await supaGuard.auth.getUser();
      const { data: profile, error } = await supaGuard.from('profiles').select('*').eq('id', user.id).single();
      if (error || !profile) {
        // OJO: ya no cerramos la sesión aquí — un error transitorio de red
        // o de RLS no debería desloguear al admin de todas sus pestañas.
        console.error('admin-guard: no se pudo leer el perfil de administrador.', error);
        irAIndex();
        return;
      }
      if (profile.role !== 'admin' && profile.role !== 'superadmin') {
        console.warn('admin-guard: la cuenta autenticada no tiene rol admin/superadmin (role="'+profile.role+'").');
        irAIndex();
        return;
      }

      window.currentAdmin = {
        id: profile.id, email: profile.email, name: profile.name || profile.email,
        role: profile.role, permisos: profile.permisos || {},
        accessToken: session.access_token,
      };
      document.dispatchEvent(new CustomEvent('admin-ready', { detail: window.currentAdmin }));
    } catch (e) {
      console.error('Error verificando sesión de admin:', e);
      irAIndex();
    }
  })();

  window.cerrarSesionAdmin = function () {
    supaGuard.auth.signOut().finally(irAIndex);
  };
})();
