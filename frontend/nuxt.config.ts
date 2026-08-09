// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({

  modules: [
    '@nuxt/eslint',
    '@nuxt/ui'
  ],

  components: [
    { path: '~/components/layout', pathPrefix: false },
    { path: '~/components/pdf', pathPrefix: false },
    '~/components'
  ],

  devtools: {
    enabled: true
  },

  css: ['~/assets/css/main.css'],

  runtimeConfig: {
    public: {
      apiBaseUrl: process.env.NUXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'
    }
  },

  routeRules: {
    '/': { prerender: true },
    '/outils/pivoter': { redirect: '/outils/organiser' }
  },
  compatibilityDate: '2026-06-30',

  vite: {
    optimizeDeps: {
      include: ['pdfjs-dist']
    }
  },

  eslint: {
    config: {
      stylistic: {
        commaDangle: 'never',
        braceStyle: '1tbs'
      }
    }
  }
})
