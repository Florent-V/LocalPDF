<script setup>
defineProps({
  title: { type: String, required: true },
  description: { type: String, required: true },
  icon: { type: String, default: 'i-lucide-file-text' },
  to: { type: String, required: true },
  color: { type: String, default: 'indigo' }
})

const colorClasses = {
  indigo: 'text-indigo-500 bg-indigo-500/10 group-hover:bg-indigo-500/15',
  amber: 'text-amber-500 bg-amber-500/10 group-hover:bg-amber-500/15',
  emerald: 'text-emerald-500 bg-emerald-500/10 group-hover:bg-emerald-500/15',
  sky: 'text-sky-500 bg-sky-500/10 group-hover:bg-sky-500/15',
  fuchsia: 'text-fuchsia-500 bg-fuchsia-500/10 group-hover:bg-fuchsia-500/15'
}

const ringClasses = {
  indigo: 'hover:border-indigo-500/60',
  amber: 'hover:border-amber-500/60',
  emerald: 'hover:border-emerald-500/60',
  sky: 'hover:border-sky-500/60',
  fuchsia: 'hover:border-fuchsia-500/60'
}
</script>

<template>
  <NuxtLink
    :to="to"
    class="group block rounded-xl border border-(--ui-border) bg-(--ui-bg-elevated) p-5 transition-all duration-150 hover:-translate-y-0.5 hover:shadow-md focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-(--ui-primary)"
    :class="ringClasses[color]"
  >
    <div class="flex items-center gap-3">
      <div
        class="rounded-lg p-2 transition-colors"
        :class="colorClasses[color]"
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
