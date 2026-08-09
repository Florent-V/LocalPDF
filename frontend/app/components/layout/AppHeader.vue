<script setup>
const mobileNavOpen = ref(false)
</script>

<template>
  <header class="sticky top-0 z-50 border-b border-(--ui-border) bg-(--ui-bg)/80 backdrop-blur-md">
    <div class="flex items-center justify-between h-16 px-4 md:px-6">
      <div class="flex items-center gap-1">
        <UButton
          icon="i-lucide-menu"
          color="neutral"
          variant="ghost"
          class="md:hidden -ml-2"
          aria-label="Ouvrir le menu des outils"
          @click="mobileNavOpen = true"
        />
        <NuxtLink
          to="/"
          class="flex items-center gap-2"
        >
          <UIcon
            name="i-lucide-file-lock-2"
            class="w-6 h-6 text-(--ui-primary)"
          />
          <span class="text-lg font-bold tracking-tight">LocalPDF</span>
        </NuxtLink>
      </div>

      <div class="flex items-center gap-1">
        <UButton
          to="/parametres"
          icon="i-lucide-settings"
          color="neutral"
          variant="ghost"
          aria-label="Paramètres"
        />
        <UColorModeButton />
      </div>
    </div>

    <AppMobileNav v-model:open="mobileNavOpen" />
  </header>
</template>
