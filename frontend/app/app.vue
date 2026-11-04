<script setup>
useHead({
  meta: [
    { name: 'viewport', content: 'width=device-width, initial-scale=1' }
  ],
  link: [
    { rel: 'icon', href: '/favicon.ico' }
  ],
  htmlAttrs: {
    lang: 'fr'
  }
})

const title = 'LocalPDF'
const description = 'Alternative locale et privacy-first à iLovePDF. Manipulez vos PDF sans jamais les envoyer sur Internet.'

useSeoMeta({
  title,
  description,
  ogTitle: title,
  ogDescription: description,
  twitterCard: 'summary_large_image'
})

// The OAuth server refused the login (/auth/callback sends back ?auth_error=<code>)
const route = useRoute()
const { user } = useUser()
const loginRefused = computed(() => !user.value && typeof route.query.auth_error === 'string')
const refusal = computed(() => route.query.auth_error === 'access_denied'
  ? 'Votre compte n’a pas accès à cette application.'
  : 'La connexion a échoué.')
</script>

<template>
  <UApp>
    <UContainer
      v-if="loginRefused"
      class="flex min-h-screen items-center justify-center"
    >
      <UCard class="max-w-md text-center">
        <UIcon
          name="i-lucide-shield-x"
          class="mx-auto mb-3 h-10 w-10 text-(--ui-error)"
        />
        <h1 class="mb-1 text-lg font-semibold">
          Connexion refusée
        </h1>
        <p class="mb-4 text-(--ui-text-muted)">
          {{ refusal }}
        </p>
        <UButton
          href="/auth/login"
          external
          label="Réessayer"
        />
      </UCard>
    </UContainer>

    <template v-else>
      <AppHeader />

      <div class="flex items-start min-h-[calc(100vh-64px)]">
        <AppSidebar class="hidden md:block" />
        <UMain class="flex-1 p-4 md:p-8">
          <NuxtPage />
        </UMain>
      </div>

      <AppFooter />
    </template>
  </UApp>
</template>
