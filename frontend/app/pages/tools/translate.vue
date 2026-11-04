<script setup>
import PdfPageGrid from '~/components/pdf/PdfPageGrid.vue'

const { job, loading, create, requireConfig, call } = useAiJob()

const file = ref(null)
const targetLanguage = ref('anglais')
const result = ref('')

async function onUpload() {
  if (!file.value) return
  const created = await create(file.value)
  if (created) await onTranslate()
}

async function onTranslate() {
  const config = requireConfig()
  if (!config) return
  const response = await call('translate', config, { target_language: targetLanguage.value })
  if (response !== null) result.value = response
}
</script>

<template>
  <div>
    <h1 class="mb-2 text-2xl font-bold">
      Traduction par IA
    </h1>
    <p class="mb-6 text-(--ui-text-muted)">
      Traduisez le contenu d'un PDF dans une langue cible.
    </p>

    <FileDropzone
      accept=".pdf"
      @files-selected="file = $event[0]; onUpload()"
    />

    <PdfPageGrid
      v-if="file"
      class="mt-4"
      :file="file"
    />

    <div class="mt-6 rounded-lg border border-(--ui-border) p-4">
      <UFormField label="Langue cible">
        <UInput v-model="targetLanguage" />
      </UFormField>
    </div>

    <div
      v-if="result"
      class="mt-6 rounded-lg bg-(--ui-bg-elevated) p-4"
    >
      <pre class="whitespace-pre-wrap text-sm">{{ result }}</pre>
    </div>

    <UButton
      v-if="job"
      class="mt-4"
      :loading="loading"
      @click="onTranslate"
    >
      Retraduire
    </UButton>
  </div>
</template>
