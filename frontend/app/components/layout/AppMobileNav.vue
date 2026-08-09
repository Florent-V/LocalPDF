<script setup>
const open = defineModel('open', { type: Boolean, default: false })

const route = useRoute()
watch(() => route.fullPath, () => {
  open.value = false
})

const colorClasses = {
  indigo: 'text-indigo-500 bg-indigo-500/10',
  amber: 'text-amber-500 bg-amber-500/10',
  emerald: 'text-emerald-500 bg-emerald-500/10',
  sky: 'text-sky-500 bg-sky-500/10',
  fuchsia: 'text-fuchsia-500 bg-fuchsia-500/10'
}
</script>

<template>
  <USlideover
    v-model:open="open"
    side="left"
    title="Outils PDF"
  >
    <template #body>
      <nav class="space-y-6">
        <div
          v-for="category in TOOL_CATEGORIES"
          :key="category.title"
        >
          <div class="flex items-center gap-2 px-1 text-sm font-semibold text-(--ui-text-muted)">
            <span
              class="flex h-6 w-6 items-center justify-center rounded-md"
              :class="colorClasses[category.color]"
            >
              <UIcon
                :name="category.icon"
                class="h-3.5 w-3.5"
              />
            </span>
            {{ category.title }}
          </div>
          <ul class="mt-2 space-y-0.5">
            <li
              v-for="tool in category.tools"
              :key="tool.to"
            >
              <UButton
                :to="tool.to"
                variant="ghost"
                color="neutral"
                icon="i-lucide-arrow-right"
                trailing
                class="w-full justify-between"
              >
                {{ tool.title }}
              </UButton>
            </li>
          </ul>
        </div>
      </nav>
    </template>
  </USlideover>
</template>
