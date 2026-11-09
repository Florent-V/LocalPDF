// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({

  modules: [
    '@nuxt/eslint',
    '@nuxt/ui'
  ],

  // Static single-page app (`nuxt generate`): Caddy serves the files, and the
  // Python API, which is the OAuth client, answers /api and /auth.
  ssr: false,

  components: [
    { path: '~/components/layout', pathPrefix: false },
    { path: '~/components/pdf', pathPrefix: false },
    '~/components'
  ],

  devtools: {
    enabled: false
  },

  css: ['~/assets/css/main.css'],

  compatibilityDate: '2026-06-30',

  // Dev only: same origin as in production (the session cookie needs it), so
  // /api and /auth go to the API. BACKEND_URL: where the API listens.
  nitro: {
    devProxy: {
      '/api': { target: `${process.env.BACKEND_URL ?? 'http://localhost:8000'}/api` },
      '/auth': { target: `${process.env.BACKEND_URL ?? 'http://localhost:8000'}/auth` }
    }
  },

  vite: {
    // Dev only: the OAuth server (in Docker) calls the back-channel logout URL
    // through host.docker.internal, which Vite would otherwise refuse.
    server: { allowedHosts: ['host.docker.internal'] },
    optimizeDeps: {
      include: ['pdfjs-dist']
    }
  },

  telemetry: false,

  eslint: {
    config: {
      stylistic: {
        commaDangle: 'never',
        braceStyle: '1tbs'
      }
    }
  },

  // Static build: there is no Nuxt server to serve icons, and the Iconify API
  // must not be called (privacy, CSP). Every icon used in the sources is bundled.
  icon: {
    provider: 'none',
    clientBundle: { scan: { globInclude: ['**/*.{vue,ts}'] } }
  }
})
