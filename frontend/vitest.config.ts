import { defineConfig } from 'vitest/config';

// design-angular-kit's transitive bootstrap-italia is CommonJS-only. Angular's
// esbuild-based ng build handles the CJS->ESM interop fine on its own, but
// Vitest's module runner treats it as an external by default and fails with
// "Named export 'X' not found" - inlining forces it through Vitest's own
// transform, which does the interop correctly. See the commit that added this
// file for the two things that did NOT work first (optimizeDeps.include alone,
// top-level ssr.noExternal).
export default defineConfig({
  test: {
    server: {
      deps: {
        inline: ['bootstrap-italia', 'design-angular-kit'],
      },
    },
  },
});
