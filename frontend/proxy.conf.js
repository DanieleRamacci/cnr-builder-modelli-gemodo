// Proxies /api/* to the real backend so the browser only ever talks to the
// Angular dev server's own origin (localhost:4200) - no CORS needed, no
// build-time base URL baked into the bundle. GEMODO_API_BASE_URL is already
// wired through infra/local/compose.yaml.
const target = process.env['GEMODO_API_BASE_URL'] || 'http://localhost:8000';

module.exports = {
  '/api': { target, secure: false, changeOrigin: true },
  '/openapi': { target, secure: false, changeOrigin: true },
  '/docs': { target, secure: false, changeOrigin: true },
  '/redoc': { target, secure: false, changeOrigin: true },
};
