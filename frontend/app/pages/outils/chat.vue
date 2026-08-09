<script setup>
import PdfPageGrid from '~/components/pdf/PdfPageGrid.vue'

const { baseURL } = useApi()
const { getConfig } = useAiConfig()

const file = ref(null)
const job = ref(null)
const question = ref('')
const messages = ref([])
const loading = ref(false)

async function onUpload() {
  if (!file.value) return
  const form = new FormData()
  form.append('file', file.value)
  job.value = await $fetch(`${baseURL}/api/v1/ai/jobs`, {
    method: 'POST',
    body: form
  })
}

async function sendMessage() {
  if (!job.value || !question.value.trim()) return
  const config = getConfig()
  if (!config) {
    alert('Veuillez configurer un provider IA dans Paramètres.')
    return
  }
  loading.value = true
  const q = question.value
  messages.value.push({ role: 'user', content: q })
  question.value = ''
  try {
    const response = await $fetch(`${baseURL}/api/v1/ai/jobs/${job.value.job_id}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: { config, question: q }
    })
    messages.value.push({ role: 'assistant', content: response })
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
      Chat avec le PDF
    </h1>
    <p class="mb-6 text-(--ui-text-muted)">
      Posez des questions sur le contenu d'un PDF.
    </p>

    <FileDropzone
      v-if="!job"
      accept=".pdf"
      @files-selected="file = $event[0]; onUpload()"
    />

    <PdfPageGrid
      v-if="file"
      class="mb-4"
      :file="file"
    />

    <div
      v-else
      class="flex flex-col gap-2 rounded-lg border border-(--ui-border) p-4"
    >
      <div
        v-for="(msg, i) in messages"
        :key="i"
        :class="[msg.role === 'user' ? 'self-end bg-(--ui-primary) text-white' : 'self-start bg-(--ui-bg-elevated) text-(--ui-text)', 'max-w-[80%] rounded-lg px-3 py-2 text-sm']"
      >
        {{ msg.content }}
      </div>

      <div class="mt-2 flex gap-2">
        <UInput
          v-model="question"
          class="flex-1"
          placeholder="Votre question..."
          @keydown.enter="sendMessage"
        />
        <UButton
          :loading="loading"
          @click="sendMessage"
        >
          Envoyer
        </UButton>
      </div>
    </div>
  </div>
</template>
