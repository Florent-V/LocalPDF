<script setup>
const props = defineProps({
  file: { type: Object, default: null }
})

const rectangles = defineModel({ type: Array, default: () => [] })

const { loadDocument, renderPageToCanvas, renderPageThumbnail } = usePdfRenderer()

const doc = shallowRef(null)
const pageCount = ref(0)
const currentPage = ref(1)
const scale = ref(1)
const loading = ref(false)
const canvasEl = ref(null)
const containerEl = ref(null)
const stripThumbs = ref([])

const drawing = ref(false)
const draftRect = ref(null)

const pageRects = computed(() => rectangles.value
  .map((r, index) => ({ ...r, index }))
  .filter(r => r.page === currentPage.value))

async function openDocument(file) {
  if (!file) return
  loading.value = true
  stripThumbs.value = []
  try {
    doc.value = await loadDocument(file)
    pageCount.value = doc.value.numPages
    currentPage.value = 1
  } finally {
    loading.value = false
  }
  await nextTick()
  await renderCurrentPage()
  for (let i = 1; i <= pageCount.value; i++) {
    stripThumbs.value.push(await renderPageThumbnail(doc.value, i, 100))
  }
}

async function renderCurrentPage() {
  if (!doc.value || !canvasEl.value) return
  const width = Math.min(containerEl.value?.clientWidth || 1300, 1300)
  const result = await renderPageToCanvas(doc.value, currentPage.value, canvasEl.value, width)
  scale.value = result.scale
}

watch(() => props.file, (file) => {
  openDocument(file)
}, { immediate: true })
watch(currentPage, () => {
  renderCurrentPage()
})

function goToPage(page) {
  if (page < 1 || page > pageCount.value) return
  currentPage.value = page
}

function canvasPoint(evt) {
  const rect = canvasEl.value.getBoundingClientRect()
  const ratioX = canvasEl.value.width / rect.width
  const ratioY = canvasEl.value.height / rect.height
  return {
    x: (evt.clientX - rect.left) * ratioX,
    y: (evt.clientY - rect.top) * ratioY
  }
}

function onPointerDown(evt) {
  const start = canvasPoint(evt)
  drawing.value = true
  draftRect.value = { x1: start.x, y1: start.y, x2: start.x, y2: start.y }
  evt.target.setPointerCapture(evt.pointerId)
}

function onPointerMove(evt) {
  if (!drawing.value) return
  const point = canvasPoint(evt)
  draftRect.value = { ...draftRect.value, x2: point.x, y2: point.y }
}

function onPointerUp() {
  if (!drawing.value || !draftRect.value) return
  drawing.value = false
  const { x1, y1, x2, y2 } = draftRect.value
  draftRect.value = null
  const widthPx = Math.abs(x2 - x1)
  const heightPx = Math.abs(y2 - y1)
  if (widthPx < 6 || heightPx < 6) return
  const rect = {
    x1: Math.min(x1, x2) / scale.value,
    y1: Math.min(y1, y2) / scale.value,
    x2: Math.max(x1, x2) / scale.value,
    y2: Math.max(y1, y2) / scale.value
  }
  rectangles.value = [...rectangles.value, { page: currentPage.value, rect }]
}

function removeRect(index) {
  rectangles.value = rectangles.value.filter((_, i) => i !== index)
}

function draftStyle() {
  if (!draftRect.value || !canvasEl.value) return {}
  const displayRatio = canvasEl.value.getBoundingClientRect().width / canvasEl.value.width
  const { x1, y1, x2, y2 } = draftRect.value
  return {
    left: `${Math.min(x1, x2) * displayRatio}px`,
    top: `${Math.min(y1, y2) * displayRatio}px`,
    width: `${Math.abs(x2 - x1) * displayRatio}px`,
    height: `${Math.abs(y2 - y1) * displayRatio}px`
  }
}

function existingRectStyle(r) {
  if (!canvasEl.value) return {}
  const displayRatio = canvasEl.value.getBoundingClientRect().width / canvasEl.value.width
  return {
    left: `${r.rect.x1 * scale.value * displayRatio}px`,
    top: `${r.rect.y1 * scale.value * displayRatio}px`,
    width: `${(r.rect.x2 - r.rect.x1) * scale.value * displayRatio}px`,
    height: `${(r.rect.y2 - r.rect.y1) * scale.value * displayRatio}px`
  }
}
</script>

<template>
  <div
    v-if="loading"
    class="flex items-center gap-2 py-8 text-sm text-(--ui-text-muted)"
  >
    <UIcon
      name="i-lucide-loader-2"
      class="w-4 h-4 animate-spin"
    />
    Chargement du document…
  </div>
  <div
    v-else-if="doc"
    ref="containerEl"
    class="space-y-3"
  >
    <p class="text-sm text-(--ui-text-muted)">
      Dessinez des rectangles directement sur la page pour censurer une zone.
    </p>

    <div class="flex justify-center">
      <div class="relative inline-block max-w-full select-none">
        <canvas
          ref="canvasEl"
          class="max-w-full cursor-crosshair rounded border border-(--ui-border)"
          @pointerdown="onPointerDown"
          @pointermove="onPointerMove"
          @pointerup="onPointerUp"
        />
        <div
          v-for="r in pageRects"
          :key="r.index"
          class="pointer-events-none absolute border-2 border-red-500 bg-red-500/30"
          :style="existingRectStyle(r)"
        />
        <div
          v-if="draftRect"
          class="pointer-events-none absolute border-2 border-(--ui-primary) bg-(--ui-primary)/20"
          :style="draftStyle()"
        />
      </div>
    </div>

    <div class="flex items-center justify-center gap-2">
      <UButton
        icon="i-lucide-chevron-left"
        size="sm"
        color="neutral"
        variant="ghost"
        :disabled="currentPage <= 1"
        @click="goToPage(currentPage - 1)"
      />
      <span class="text-sm">Page {{ currentPage }} / {{ pageCount }}</span>
      <UButton
        icon="i-lucide-chevron-right"
        size="sm"
        color="neutral"
        variant="ghost"
        :disabled="currentPage >= pageCount"
        @click="goToPage(currentPage + 1)"
      />
      <span class="text-xs text-(--ui-text-muted)">
        {{ rectangles.length }} zone(s) au total
      </span>
    </div>

    <div
      v-if="pageRects.length"
      class="flex flex-wrap justify-center gap-2"
    >
      <UBadge
        v-for="r in pageRects"
        :key="r.index"
        color="error"
        variant="subtle"
        class="cursor-pointer"
        @click="removeRect(r.index)"
      >
        Zone {{ r.index + 1 }} <UIcon
          name="i-lucide-x"
          class="ml-1 w-3 h-3"
        />
      </UBadge>
    </div>

    <div class="flex flex-wrap justify-center gap-2 overflow-x-auto pb-1">
      <button
        v-for="(thumb, i) in stripThumbs"
        :key="i"
        type="button"
        class="shrink-0 overflow-hidden rounded border-2 transition"
        :class="currentPage === i + 1 ? 'border-(--ui-primary)' : 'border-transparent'"
        @click="goToPage(i + 1)"
      >
        <img
          :src="thumb"
          :alt="`Page ${i + 1}`"
          class="h-16 w-auto"
        >
      </button>
    </div>
  </div>
</template>
