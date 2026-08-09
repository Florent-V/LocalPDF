<script setup>
import FileThumbnailList from '~/components/pdf/FileThumbnailList.vue'

const { uploadForm } = useApi()

const files = ref([])
const loading = ref(false)

async function onSubmit() {
  if (!files.value.length) return
  loading.value = true
  try {
    const form = new FormData()
    files.value.forEach(f => form.append('files', f))
    const blob = await uploadForm('/api/v1/convert/images-to-pdf', form)
    downloadBlob(blob, 'images.pdf')
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
      Images vers PDF
    </h1>
    <p class="mb-6 text-(--ui-text-muted)">
      Compilez plusieurs images (JPG, PNG, WEBP) dans un seul PDF.
    </p>

    <FileDropzone
      accept="image/*"
      multiple
      @files-selected="files = $event"
    />

    <p
      v-if="files.length"
      class="mt-4 text-sm text-(--ui-text-muted)"
    >
      Glissez-déposez les images pour changer l'ordre des pages du PDF.
    </p>
    <FileThumbnailList
      v-if="files.length"
      class="mt-2"
      :files="files"
      @update:files="files = $event"
    />

    <UButton
      class="mt-6"
      size="lg"
      :loading="loading"
      :disabled="!files.length"
      @click="onSubmit"
    >
      Convertir en PDF
    </UButton>
  </div>
</template>
