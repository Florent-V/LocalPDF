<script setup>
import PdfPageGrid from '~/components/pdf/PdfPageGrid.vue'

const { uploadForm } = useApi()

const file = ref(null)
const loading = ref(false)

async function onSubmit() {
  if (!file.value) return
  loading.value = true
  try {
    const form = new FormData()
    form.append('file', file.value)
    const blob = await uploadForm('/api/v1/convert/pdf-to-word', form)
    downloadBlob(blob, 'document.docx')
  } catch (e) {
    alert('Erreur lors de la conversion : ' + (e?.message || 'inconnue'))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div>
    <h1 class="mb-2 text-2xl font-bold">
      PDF vers Word
    </h1>
    <p class="mb-6 text-(--ui-text-muted)">
      Convertissez un PDF en document Word éditable.
    </p>

    <FileDropzone
      accept=".pdf"
      @files-selected="file = $event[0]"
    />

    <PdfPageGrid
      v-if="file"
      class="mt-4"
      :file="file"
    />

    <UButton
      class="mt-6"
      size="lg"
      :loading="loading"
      :disabled="!file"
      @click="onSubmit"
    >
      Convertir en Word
    </UButton>
  </div>
</template>
