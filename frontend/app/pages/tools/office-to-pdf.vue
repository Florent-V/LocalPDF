<script setup>
const { loading, submit } = useToolSubmit()

const file = ref(null)

async function onSubmit() {
  if (!file.value) return
  const form = new FormData()
  form.append('file', file.value)
  await submit('/api/v1/convert/office-to-pdf', form, 'converted.pdf', 'Erreur lors de la conversion')
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
