// ── Sesión pública real (Supabase Auth) ──────────────────────────────────
// Reemplaza la vieja verificación por sessionStorage (fácilmente falsificable
// desde la consola del navegador). Requiere que la página ya haya cargado
// @supabase/supabase-js y definido `supaPub` con createClient(...).
//
// Uso en cada página de servicio:
//   <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
//   <script>
//     const supaPub = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
//   </script>
//   <script src="<ruta-relativa>/assets/js/public-session.js"></script>
//
// Y donde antes se llamaba getSesionPublica() (síncrono), ahora:
//   const sesion = await getSesionPublicaAsync();

async function getSesionPublicaAsync() {
  try {
    const { data: { session } } = await supaPub.auth.getSession();
    if (!session) return null;
    const { data: profile, error } = await supaPub
      .from('profiles')
      .select('name, email, cedula, phone, puntos, role')
      .eq('id', session.user.id)
      .single();
    if (error || !profile) return null;
    if (profile.role === 'admin' || profile.role === 'superadmin') {
      return { tipo: 'admin', name: profile.name || profile.email };
    }
    return { tipo: 'publico', name: profile.name, email: profile.email, cedula: profile.cedula, phone: profile.phone, puntos: profile.puntos };
  } catch {
    return null;
  }
}

async function verificarYReservarAsync(fn) {
  const sesion = await getSesionPublicaAsync();
  if (sesion) { fn(); return; }
  if (typeof mostrarAvisoLogin === 'function') mostrarAvisoLogin();
}
