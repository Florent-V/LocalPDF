<script setup>
import PdfPageGrid from '~/components/pdf/PdfPageGrid.vue'

const { baseURL } = useApi()
const { getConfig } = useAiConfig()

const file = ref(null)
const job = ref(null)
const language = ref('français')
const loading = ref(false)
const result = ref('')

async function onUpload() {
  if (!file.value) return
  loading.value = true
  try {
    const form = new FormData()
    form.append('file', file.value)
    job.value = await $fetch(`${baseURL}/api/v1/ai/jobs`, {
      method: 'POST',
      body: form
    })
    await onSummarize()
  } catch (e) {
    alert('Erreur : ' + (e?.message || 'inconnue'))
  } finally {
    loading.value = false
  }
}

async function onSummarize() {
  const config = getConfig()
  if (!config) {
    alert('Veuillez configurer un provider IA dans Paramètres.')
    return
  }
  loading.value = true
  try {
    const response = await $fetch(`${baseURL}/api/v1/ai/jobs/${job.value.job_id}/summarize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: { config, language: language.value }
    })
    result.value = response
  } catch (e) {
    alert('Erreur IA : ' + (e?.message || 'inconnue'))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div>
    <h1 class="mb-2 text-2xl font-bold">
      Résumé par IA
    </h1>
    <p class="mb-6 text-(--ui-text-muted)">
      Générez un résumé du contenu d'un PDF via un modèle d'IA.
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
      <UFormField label="Langue du résumé">
        <UInput v-model="language" />
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
      @click="onSummarize"
    >
      Regénérer le résumé
    </UButton>
  </div>
</template>
