<script setup>
const { uploadForm } = useApi()

const mode = ref('file')
const file = ref(null)
const text = ref('')
const loading = ref(false)

const canSubmit = computed(() => {
  return mode.value === 'file' ? !!file.value : text.value.trim().length > 0
})

async function onSubmit() {
  if (!canSubmit.value) return
  loading.value = true
  try {
    const form = new FormData()
    if (mode.value === 'file') {
      form.append('file', file.value)
    } else {
      form.append('text', text.value)
    }
    const blob = await uploadForm('/api/v1/convert/markdown-to-pdf', form)
    downloadBlob(blob, 'document.pdf')
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
      Markdown vers PDF
    </h1>
    <p class="mb-6 text-(--ui-text-muted)">
      Générez un PDF à partir de texte rédigé en Markdown.
    </p>

    <div class="mb-4 flex gap-2">
      <UButton
        :variant="mode === 'file' ? 'solid' : 'outline'"
        @click="mode = 'file'; text = ''"
      >
        Fichier
      </UButton>
      <UButton
        :variant="mode === 'text' ? 'solid' : 'outline'"
        @click="mode = 'text'; file = null"
      >
        Texte
      </UButton>
    </div>

    <FileDropzone
      v-if="mode === 'file'"
      accept=".md,.markdown"
      @files-selected="file = $event[0]"
    />

    <UTextarea
      v-else
      v-model="text"
      :rows="14"
      class="w-full"
      placeholder="# Titre&#10;&#10;Rédigez votre **Markdown** ici..."
    />

    <UButton
      class="mt-6"
      size="lg"
      :loading="loading"
      :disabled="!canSubmit"
      @click="onSubmit"
    >
      Convertir en PDF
    </UButton>
  </div>
</template>
