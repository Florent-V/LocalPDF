<script setup>
const { uploadForm } = useApi()

const file = ref(null)
const loading = ref(false)

async function onSubmit() {
  if (!file.value) return
  loading.value = true
  try {
    const form = new FormData()
    form.append('file', file.value)
    const blob = await uploadForm('/api/v1/convert/office-to-pdf', form)
    downloadBlob(blob, 'converted.pdf')
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
      Office vers PDF
    </h1>
    <p class="mb-6 text-(--ui-text-muted)">
      Convertissez un document Word, Excel ou PowerPoint en PDF.
    </p>

    <FileDropzone
      accept=".docx,.xlsx,.pptx,.doc,.xls,.ppt"
      @files-selected="file = $event[0]"
    />

    <UButton
      class="mt-6"
      size="lg"
      :loading="loading"
      :disabled="!file"
      @click="onSubmit"
    >
      Convertir
    </UButton>
  </div>
</template>
