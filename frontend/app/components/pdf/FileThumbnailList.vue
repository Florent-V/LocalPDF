<script setup>
import PageThumbCard from './PageThumbCard.vue'

const props = defineProps({
  files: { type: Array, default: () => [] }
})

const emit = defineEmits(['update:files'])

const { loadDocument, renderPageThumbnail } = usePdfRenderer()

const FALLBACK_THUMB = `data:image/svg+xml,${encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="140"><rect width="100" height="140" fill="#e5e7eb"/></svg>')}`

const thumbCache = new Map()
const entries = ref([])
const dragIndex = ref(null)

function isPdf(file) {
  return file.type === 'application/pdf' || file.name?.toLowerCase().endsWith('.pdf')
}

function isImage(file) {
  return file.type?.startsWith('image/')
}

async function thumbFor(file) {
  if (thumbCache.has(file)) return thumbCache.get(file)
  let src = null
  try {
    if (isPdf(file)) {
      const doc = await loadDocument(file)
      src = await renderPageThumbnail(doc, 1, 220)
    } else if (isImage(file)) {
      src = URL.createObjectURL(file)
    }
  } catch {
    src = null
  }
  thumbCache.set(file, src)
  return src
}

async function sync(files) {
  const next = []
  for (const file of files) {
    next.push({ file, src: await thumbFor(file) })
  }
  entries.value = next
}

watch(() => props.files, (files) => {
  sync(files)
}, { immediate: true, deep: false })

function remove(index) {
  const next = [...props.files]
  next.splice(index, 1)
  emit('update:files', next)
}

function onDragStart(index) {
  dragIndex.value = index
}

function onDrop(index) {
  if (dragIndex.value === null || dragIndex.value === index) return
  const next = [...props.files]
  const moved = next.splice(dragIndex.value, 1)[0]
  next.splice(index, 0, moved)
  dragIndex.value = null
  emit('update:files', next)
}

function onDragEnd() {
  dragIndex.value = null
}
</script>

<template>
  <div
    v-if="entries.length"
    class="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6"
  >
    <PageThumbCard
      v-for="(entry, index) in entries"
      :key="entry.file.name + entry.file.size + index"
      :src="entry.src || FALLBACK_THUMB"
      :label="entry.file.name"
      removable
      draggable
      @remove="remove(index)"
      @dragstart="onDragStart(index)"
      @drop="onDrop(index)"
      @dragend="onDragEnd"
    />
  </div>
</template>
