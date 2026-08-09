<script setup>
const search = ref('')

const filteredCategories = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return TOOL_CATEGORIES

  return TOOL_CATEGORIES
    .map(category => ({
      ...category,
      tools: category.tools.filter(tool =>
        tool.title.toLowerCase().includes(q) || tool.description.toLowerCase().includes(q)
      )
    }))
    .filter(category => category.tools.length > 0)
})

const totalTools = computed(() => filteredCategories.value.reduce((n, c) => n + c.tools.length, 0))
</script>

<template>
  <div>
    <div class="mb-10 grid gap-6 rounded-2xl border border-(--ui-border) bg-(--ui-bg-elevated) p-6 md:grid-cols-[1.3fr_1fr] md:p-10">
      <div class="flex flex-col justify-center">
        <h1 class="text-2xl font-bold tracking-tight md:text-4xl">
          Vos PDF, jamais stockés, jamais partagés.
        </h1>
        <p class="mt-3 max-w-md text-(--ui-text-muted)">
          Fusionnez, convertissez, protégez et modifiez vos documents. Aucun compte, aucune base de données, aucun tiers : le traitement a lieu sur ce serveur, sans jamais rien conserver.
        </p>

        <UInput
          v-model="search"
          icon="i-lucide-search"
          placeholder="Rechercher un outil… (fusionner, protéger, traduire)"
          size="lg"
          class="mt-6 max-w-md"
          :ui="{ base: 'rounded-full' }"
        />
      </div>

      <div class="flex flex-col justify-center rounded-xl border border-(--ui-border) bg-(--ui-bg) p-5">
        <div class="flex items-center gap-2 text-sm font-semibold text-emerald-500">
          <span class="relative flex h-2 w-2">
            <span class="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-500 opacity-75" />
            <span class="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
          </span>
          Service 100% privé
        </div>
        <div class="mt-3 flex items-baseline gap-2">
          <span class="text-sm text-(--ui-text-muted)">🔒 Aucun tiers, aucune BDD, aucun fichier conservé</span>
        </div>
        <p class="mt-2 text-xs text-(--ui-text-muted)">
          Vos fichiers sont traités en mémoire par ce serveur, jamais partagés avec un tiers, puis supprimés immédiatement.
        </p>
      </div>
    </div>

    <div
      v-if="search && totalTools === 0"
      class="rounded-xl border border-dashed border-(--ui-border) p-10 text-center text-(--ui-text-muted)"
    >
      Aucun outil ne correspond à « {{ search }} ».
    </div>

    <div
      v-for="category in filteredCategories"
      :key="category.title"
      class="mb-10"
    >
      <h2 class="mb-4 flex items-center gap-2 text-xl font-semibold">
        <UIcon
          :name="category.icon"
          class="h-5 w-5 text-(--ui-text-muted)"
        />
        {{ category.title }}
      </h2>
      <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <ToolCard
          v-for="tool in category.tools"
          :key="tool.to"
          v-bind="tool"
          :color="category.color"
        />
      </div>
    </div>
  </div>
</template>
