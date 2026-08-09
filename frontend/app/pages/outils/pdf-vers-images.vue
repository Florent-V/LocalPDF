<script setup>
import PdfPageGrid from '~/components/pdf/PdfPageGrid.vue'

const { uploadForm } = useApi()

const file = ref(null)
const dpi = ref(150)
const fmt = ref('png')
const loading = ref(false)

async function onSubmit() {
  if (!file.value) return
  loading.value = true
  try {
    const form = new FormData()
    form.append('file', file.value)
    form.append('dpi', String(dpi.value))
    form.append('fmt', fmt.value)
    const blob = await uploadForm('/api/v1/convert/pdf-to-images', form)
    downloadBlob(blob, 'images.zip')
  } catch (e) {
    alert('Erreur lors de l\'extraction : ' + (e?.message || 'inconnue'))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div>
    <h1 class="mb-2 text-2xl font-bold">
      PDF vers Images
    </h1>
    <p class="mb-6 text-(--ui-text-muted)">
      Extrayez chaque page d'un PDF sous forme d'images.
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

    <div class="mt-6 grid gap-4 sm:grid-cols-2">
      <UFormField label="Résolution (DPI)">
        <UInput
          v-model="dpi"
          type="number"
          min="72"
          max="600"
        />
      </UFormField>
      <UFormField label="Format">
        <USelect
          v-model="fmt"
          :items="[{ label: 'PNG', value: 'png' }, { label: 'JPG', value: 'jpg' }, { label: 'WEBP', value: 'webp' }]"
        />
      </UFormField>
    </div>

    <UButton
      class="mt-6"
      size="lg"
      :loading="loading"
      :disabled="!file"
      @click="onSubmit"
    >
      Extraire les images
    </UButton>
  </div>
</template>
