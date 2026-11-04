<script setup>
import FileThumbnailList from '~/components/pdf/FileThumbnailList.vue'

const { loading, submit } = useToolSubmit()

const files = ref([])

async function onSubmit() {
  if (files.value.length < 2) return
  const form = new FormData()
  files.value.forEach(f => form.append('files', f))
  await submit('/api/v1/organize/merge', form, 'merged.pdf', 'Erreur lors de la fusion')
}
</script>

<template>
  <div>
    <h1 class="mb-2 text-2xl font-bold">
      Fusionner des PDF
    </h1>
    <p class="mb-6 text-(--ui-text-muted)">
      Assemblez plusieurs fichiers PDF dans l'ordre souhaité.
    </p>

    <FileDropzone
      accept=".pdf"
      multiple
      :files="files"
      @files-selected="files = $event"
    />

    <template v-if="files.length">
      <p class="mt-4 text-sm text-(--ui-text-muted)">
        Glissez-déposez les fichiers pour changer l'ordre de fusion.
      </p>

      <FileThumbnailList
        class="mt-4"
        :files="files"
        @update:files="files = $event"
      />

      <UButton
        class="mt-6"
        size="lg"
        :loading="loading"
        :disabled="files.length < 2"
        @click="onSubmit"
      >
        Fusionner
      </UButton>
    </template>
  </div>
</template>
