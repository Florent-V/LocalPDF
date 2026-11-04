<script setup>
import FileThumbnailList from '~/components/pdf/FileThumbnailList.vue'

const { loading, submit } = useToolSubmit()

const files = ref([])

async function onSubmit() {
  if (!files.value.length) return
  const form = new FormData()
  files.value.forEach(f => form.append('files', f))
  await submit('/api/v1/convert/images-to-pdf', form, 'images.pdf', 'Erreur lors de la conversion')
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
      :files="files"
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
