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
</script>

<template>
  <UApp>
    <AppHeader />

    <div class="flex items-start min-h-[calc(100vh-64px)]">
      <AppSidebar class="hidden md:block" />
      <UMain class="flex-1 p-4 md:p-8">
        <NuxtPage />
      </UMain>
    </div>

    <AppFooter />
  </UApp>
</template>
