<script setup>
import PageThumbCard from './PageThumbCard.vue'

const props = defineProps({
  file: { type: Object, default: null },
  thumbnails: { type: Array, default: null },
  selectable: { type: Boolean, default: false },
  reorderable: { type: Boolean, default: false },
  removable: { type: Boolean, default: false },
  rotatable: { type: Boolean, default: false },
  modelValue: { type: Array, default: () => [] },
  rotations: { type: Object, default: () => ({}) },
  groups: { type: Object, default: null },
  pageSize: { type: Number, default: 50 }
})

const emit = defineEmits(['update:modelValue', 'update:order', 'loaded', 'rotate-page'])

const { loadDocument, renderPageThumbnail } = usePdfRenderer()

const items = ref([])
const loading = ref(false)
const loadingMore = ref(false)
const dragIndex = ref(null)
const totalPages = ref(0)
const doc = shallowRef(null)

async function renderRange(fromPage, toPage) {
  for (let page = fromPage; page <= toPage; page++) {
    const src = await renderPageThumbnail(doc.value, page)
    items.value.push({ page, src })
  }
}

async function buildFromFile(file) {
  loading.value = true
  items.value = []
  try {
    doc.value = await loadDocument(file)
    totalPages.value = doc.value.numPages
    emit('loaded', totalPages.value)
    await renderRange(1, Math.min(props.pageSize, totalPages.value))
  } finally {
    loading.value = false
  }
}

function buildFromThumbnails(thumbs) {
  doc.value = null
  totalPages.value = (thumbs || []).length
  items.value = (thumbs || []).map((src, i) => ({ page: i + 1, src }))
  emit('loaded', items.value.length)
}

watch(() => props.file, (file) => {
  if (file) buildFromFile(file)
}, { immediate: true })

watch(() => props.thumbnails, (thumbs) => {
  if (thumbs) buildFromThumbnails(thumbs)
}, { immediate: true })

const hasMore = computed(() => items.value.length < totalPages.value)
const remainingCount = computed(() => totalPages.value - items.value.length)

async function loadMore() {
  if (!doc.value || loadingMore.value) return
  loadingMore.value = true
  try {
    const from = items.value.length + 1
    const to = Math.min(items.value.length + props.pageSize, totalPages.value)
    await renderRange(from, to)
  } finally {
    loadingMore.value = false
  }
}

function isSelected(page) {
  return props.modelValue.includes(page)
}

function toggleSelect(page) {
  const next = isSelected(page)
    ? props.modelValue.filter(p => p !== page)
    : [...props.modelValue, page]
  emit('update:modelValue', next)
}

function remove(index) {
  items.value.splice(index, 1)
  emit('update:order', items.value.map(i => i.page))
}

function onDragStart(index) {
  dragIndex.value = index
}

function onDrop(index) {
  if (dragIndex.value === null || dragIndex.value === index) return
  const moved = items.value.splice(dragIndex.value, 1)[0]
  items.value.splice(index, 0, moved)
  dragIndex.value = null
  emit('update:order', items.value.map(i => i.page))
}

function onDragEnd() {
  dragIndex.value = null
}
</script>

<template>
  <div
    v-if="loading"
    class="flex flex-col items-center justify-center gap-3 py-16 text-(--ui-text-muted)"
  >
    <UIcon
      name="i-lucide-loader-2"
      class="w-10 h-10 animate-spin"
    />
    <p class="text-sm font-medium">
      Génération des aperçus de pages…
    </p>
    <p class="text-xs">
      Cela peut prendre quelques secondes pour un document volumineux.
    </p>
  </div>
  <template v-else-if="items.length">
    <div class="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
      <PageThumbCard
        v-for="(item, index) in items"
        :key="item.page"
        :src="item.src"
        :label="`Page ${item.page}`"
        :selected="isSelected(item.page)"
        :selectable="selectable"
        :removable="removable"
        :draggable="reorderable"
        :rotatable="rotatable"
        :rotation="rotations[item.page] || 0"
        :group-index="groups ? groups[item.page] ?? null : null"
        :group-label="groups && groups[item.page] != null ? `Fichier ${groups[item.page] + 1}` : ''"
        @select="toggleSelect(item.page)"
        @remove="remove(index)"
        @rotate="emit('rotate-page', { page: item.page, delta: $event })"
        @dragstart="onDragStart(index)"
        @drop="onDrop(index)"
        @dragend="onDragEnd"
      />
    </div>
    <div
      v-if="hasMore"
      class="mt-4 flex justify-center"
    >
      <UButton
        color="neutral"
        variant="soft"
        :loading="loadingMore"
        @click="loadMore"
      >
        Charger {{ Math.min(pageSize, remainingCount) }} pages de plus ({{ remainingCount }} restantes)
      </UButton>
    </div>
  </template>
  <p
    v-else
    class="text-sm text-(--ui-text-muted)"
  >
    Aucune page à afficher.
  </p>
</template>
