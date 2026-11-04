<script setup>
const route = useRoute()
</script>

<template>
  <aside class="w-64 shrink-0 sticky top-16 max-h-[calc(100vh-64px)] overflow-y-auto border-r border-(--ui-border) bg-(--ui-bg) p-4">
    <nav class="space-y-6">
      <div
        v-for="category in TOOL_CATEGORIES"
        :key="category.title"
      >
        <div class="flex items-center gap-2 px-2 py-1 text-xs font-semibold tracking-wide text-(--ui-text-muted) uppercase">
          <span
            class="flex h-5 w-5 items-center justify-center rounded"
            :class="TOOL_COLOR_BADGE[category.color]"
          >
            <UIcon
              :name="category.icon"
              class="h-3 w-3"
            />
          </span>
          {{ category.title }}
        </div>
        <ul class="mt-1 space-y-0.5">
          <li
            v-for="tool in category.tools"
            :key="tool.to"
          >
            <UButton
              :to="tool.to"
              variant="ghost"
              :color="route.path === tool.to ? 'primary' : 'neutral'"
              class="w-full justify-start border-l-2 rounded-l-none pl-3"
              :class="route.path === tool.to ? TOOL_COLOR_ACTIVE_BORDER[category.color] : 'border-transparent'"
              size="sm"
            >
              {{ tool.title }}
            </UButton>
          </li>
        </ul>
      </div>
    </nav>
  </aside>
</template>
