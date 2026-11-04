<script setup>
defineProps({
  title: { type: String, required: true },
  description: { type: String, required: true },
  icon: { type: String, default: 'i-lucide-file-text' },
  to: { type: String, required: true },
  color: { type: String, default: 'indigo' }
})
</script>

<template>
  <NuxtLink
    :to="to"
    class="group block rounded-xl border border-(--ui-border) bg-(--ui-bg-elevated) p-5 transition-all duration-150 hover:-translate-y-0.5 hover:shadow-md focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-(--ui-primary)"
    :class="TOOL_COLOR_HOVER_BORDER[color]"
  >
    <div class="flex items-center gap-3">
      <div
        class="rounded-lg p-2 transition-colors"
        :class="[TOOL_COLOR_BADGE[color], TOOL_COLOR_BADGE_HOVER[color]]"
      >
        <UIcon
          :name="icon"
          class="w-5 h-5"
        />
      </div>
      <h3 class="font-semibold">{{ title }}</h3>
    </div>
    <p class="mt-3 text-sm text-(--ui-text-muted)">{{ description }}</p>
  </NuxtLink>
</template>
