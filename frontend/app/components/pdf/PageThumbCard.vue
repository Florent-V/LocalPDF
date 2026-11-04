<script setup>
const props = defineProps({
  src: { type: String, required: true },
  label: { type: String, default: '' },
  selected: { type: Boolean, default: false },
  selectable: { type: Boolean, default: false },
  removable: { type: Boolean, default: false },
  draggable: { type: Boolean, default: false },
  rotatable: { type: Boolean, default: false },
  rotation: { type: Number, default: 0 },
  groupIndex: { type: Number, default: null },
  groupLabel: { type: String, default: '' }
})

const emit = defineEmits(['select', 'remove', 'rotate', 'dragstart', 'drop', 'dragend'])

const GROUP_COLORS = [
  'bg-blue-500',
  'bg-purple-500',
  'bg-amber-500',
  'bg-emerald-500',
  'bg-pink-500',
  'bg-cyan-500'
]

const groupColor = computed(() => props.groupIndex === null
  ? null
  : GROUP_COLORS[props.groupIndex % GROUP_COLORS.length])
</script>

<template>
  <div
    class="group relative rounded-lg border p-2 pt-3 transition"
    :class="[
      selected ? 'border-(--ui-primary) ring-2 ring-(--ui-primary)/40' : 'border-(--ui-border)',
      selectable ? 'cursor-pointer' : ''
    ]"
    :draggable="draggable"
    @click="selectable && emit('select')"
    @dragstart="emit('dragstart', $event)"
    @dragover.prevent
    @drop.prevent="emit('drop', $event)"
    @dragend="emit('dragend', $event)"
  >
    <div
      v-if="groupColor"
      class="absolute inset-x-0 top-0 h-1.5 rounded-t-lg"
      :class="groupColor"
    />

    <div
      v-if="draggable"
      class="absolute left-1 top-1 z-10 cursor-grab rounded bg-(--ui-bg)/80 p-0.5 text-(--ui-text-muted) opacity-0 transition group-hover:opacity-100"
    >
      <UIcon
        name="i-lucide-grip-vertical"
        class="w-4 h-4"
      />
    </div>

    <div class="relative aspect-[3/4] overflow-hidden rounded bg-(--ui-bg-elevated)">
      <img
        :src="src"
        :alt="label"
        class="h-full w-full object-contain transition-transform"
        :style="{ transform: `rotate(${rotation}deg)` }"
      >
      <div
        v-if="rotatable"
        class="absolute inset-x-2 top-1/2 z-10 flex -translate-y-1/2 items-center justify-between opacity-70 transition group-hover:opacity-100"
      >
        <UButton
          icon="i-lucide-rotate-ccw"
          size="lg"
          color="neutral"
          variant="solid"
          class="rounded-full bg-(--ui-bg)/90"
          @click.stop="emit('rotate', -90)"
        />
        <UButton
          icon="i-lucide-rotate-cw"
          size="lg"
          color="neutral"
          variant="solid"
          class="rounded-full bg-(--ui-bg)/90"
          @click.stop="emit('rotate', 90)"
        />
      </div>
    </div>

    <div class="mt-2 flex items-center justify-between gap-1">
      <span class="truncate text-xs text-(--ui-text-muted)">
        {{ label }}
        <span
          v-if="groupLabel"
          class="ml-1"
        >· {{ groupLabel }}</span>
      </span>
      <UButton
        v-if="removable"
        icon="i-lucide-trash"
        size="2xs"
        color="error"
        variant="ghost"
        @click.stop="emit('remove')"
      />
    </div>

    <div
      v-if="selectable"
      class="absolute right-1 top-1 flex h-5 w-5 items-center justify-center rounded-full border"
      :class="selected ? 'border-(--ui-primary) bg-(--ui-primary) text-white' : 'border-(--ui-border) bg-(--ui-bg)/80'"
    >
      <UIcon
        v-if="selected"
        name="i-lucide-check"
        class="w-3 h-3"
      />
    </div>
  </div>
</template>
