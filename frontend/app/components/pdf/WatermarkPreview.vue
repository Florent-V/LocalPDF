<script setup>
const props = defineProps({
  file: { type: Object, default: null },
  mode: { type: String, default: 'text' },
  text: { type: String, default: '' },
  image: { type: Object, default: null },
  imageWidth: { type: Number, default: 100 },
  position: { type: String, default: 'center' },
  opacity: { type: Number, default: 0.3 }
})

const { loadDocument, renderPageToCanvas } = usePdfRenderer()

const canvasEl = ref(null)
const loading = ref(false)
const previewScale = ref(1)
const previewWidth = ref(0)
const imageObjectUrl = ref(null)

let resizeObserver = null

async function render() {
  if (!props.file || !canvasEl.value) return
  loading.value = true
  try {
    const doc = await loadDocument(props.file)
    const width = Math.min(canvasEl.value.parentElement?.clientWidth || 400, 420)
    const result = await renderPageToCanvas(doc, 1, canvasEl.value, width)
    previewScale.value = result.scale
    previewWidth.value = canvasEl.value.clientWidth
  } finally {
    loading.value = false
  }
}

// Le watch "immediate" se déclenche avant que le <canvas> ne soit monté (canvasEl.value
// est encore null) : on refait le rendu au montage pour ne pas rester avec previewWidth à 0.
watch(() => props.file, render)

onMounted(() => {
  render()
  resizeObserver = new ResizeObserver(() => {
    if (canvasEl.value) previewWidth.value = canvasEl.value.clientWidth
  })
  if (canvasEl.value) resizeObserver.observe(canvasEl.value)
})

watch(() => props.image, (image) => {
  if (imageObjectUrl.value) URL.revokeObjectURL(imageObjectUrl.value)
  imageObjectUrl.value = image ? URL.createObjectURL(image) : null
}, { immediate: true })

onBeforeUnmount(() => {
  if (imageObjectUrl.value) URL.revokeObjectURL(imageObjectUrl.value)
  resizeObserver?.disconnect()
})

const positionClass = computed(() => ({
  top: 'items-start justify-center',
  center: 'items-center justify-center',
  bottom: 'items-end justify-center',
  diagonal: 'items-center justify-center'
}[props.position] || 'items-center justify-center'))

function measureTextWidth(text) {
  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d')
  ctx.font = 'bold 100px sans-serif'
  return ctx.measureText(text).width
}

const DIAGONAL_SCALE = 1.25

const autoFontSize = computed(() => {
  if (!props.text) return 12
  let availWidth = Math.max(previewWidth.value - 32, 10)
  if (props.position === 'diagonal') availWidth *= DIAGONAL_SCALE
  const width100 = measureTextWidth(props.text)
  if (!width100) return 12
  return Math.min(Math.max((availWidth / width100) * 100, 6), 400)
})

const textStyle = computed(() => ({
  fontSize: `${autoFontSize.value}px`,
  opacity: props.opacity,
  transform: props.position === 'diagonal' ? 'rotate(-45deg)' : undefined
}))

const imageStyle = computed(() => ({
  width: `${props.imageWidth * previewScale.value}px`,
  opacity: props.opacity,
  transform: props.position === 'diagonal' ? 'rotate(-45deg)' : undefined
}))
</script>

<template>
  <div
    v-if="file"
    class="space-y-2"
  >
    <p class="text-sm text-(--ui-text-muted)">
      Aperçu (première page)
    </p>
    <div class="relative inline-block max-w-full overflow-hidden rounded border border-(--ui-border)">
      <canvas
        ref="canvasEl"
        class="block max-w-full"
      />
      <div
        v-if="!loading"
        class="absolute inset-0 flex p-4"
        :class="positionClass"
      >
        <span
          v-if="mode === 'text' && text"
          class="whitespace-nowrap font-bold text-black"
          :style="textStyle"
        >{{ text }}</span>
        <img
          v-else-if="mode === 'image' && imageObjectUrl"
          :src="imageObjectUrl"
          :style="imageStyle"
        >
      </div>
    </div>
  </div>
</template>
