<script setup>
const toast = useToast()

const provider = ref('ollama')
const baseUrl = ref('http://localhost:11434')
const apiKey = ref('')
const model = ref('llama3.1:8b')

const presets = {
  ollama: { baseUrl: 'http://localhost:11434', model: 'llama3.1:8b' },
  openai: { baseUrl: '', model: 'gpt-4o-mini' },
  anthropic: { baseUrl: '', model: 'claude-3-5-sonnet-20241022' },
  openrouter: { baseUrl: '', model: 'openai/gpt-4o-mini' }
}

onMounted(() => {
  const saved = localStorage.getItem('localpdf-ai-config')
  if (saved) {
    const config = JSON.parse(saved)
    provider.value = config.provider
    baseUrl.value = config.base_url || ''
    apiKey.value = config.api_key || ''
    model.value = config.model
  }
})

function applyPreset() {
  const preset = presets[provider.value]
  baseUrl.value = preset.baseUrl
  model.value = preset.model
  apiKey.value = ''
}

function saveConfig() {
  const config = {
    provider: provider.value,
    base_url: baseUrl.value || undefined,
    api_key: apiKey.value || undefined,
    model: model.value
  }
  localStorage.setItem('localpdf-ai-config', JSON.stringify(config))
  toast.add({ title: 'Configuration enregistrée', description: 'Vos paramètres IA sont enregistrés dans le navigateur.', color: 'success' })
}
</script>

<template>
  <div>
    <h1 class="mb-2 text-2xl font-bold">
      Paramètres IA
    </h1>
    <p class="mb-6 text-(--ui-text-muted)">
      Configurez votre provider IA. Les informations restent dans le localStorage de votre navigateur.
    </p>

    <div class="max-w-xl space-y-4 rounded-lg border border-(--ui-border) p-6">
      <UFormField label="Provider">
        <USelect
          v-model="provider"
          :items="[{ label: 'Ollama (local)', value: 'ollama' }, { label: 'OpenAI', value: 'openai' }, { label: 'Anthropic', value: 'anthropic' }, { label: 'OpenRouter', value: 'openrouter' }]"
          @update:model-value="applyPreset"
        />
      </UFormField>

      <UFormField
        v-if="provider === 'ollama'"
        label="URL Ollama"
      >
        <UInput v-model="baseUrl" />
      </UFormField>

      <UFormField
        v-if="provider !== 'ollama'"
        label="Clé API"
      >
        <UInput
          v-model="apiKey"
          type="password"
        />
      </UFormField>

      <UFormField
        v-if="provider === 'openrouter'"
        label="URL de base (optionnel)"
      >
        <UInput
          v-model="baseUrl"
          placeholder="https://openrouter.ai/api/v1"
        />
      </UFormField>

      <UFormField
        label="Modèle"
        :help="provider === 'openrouter' ? 'Voir openrouter.ai/models pour la liste des modèles disponibles (ex: openai/gpt-4o-mini, anthropic/claude-3-5-sonnet, meta-llama/llama-3.1-70b-instruct)' : undefined"
      >
        <UInput v-model="model" />
      </UFormField>

      <UButton @click="saveConfig">
        Enregistrer
      </UButton>
    </div>
  </div>
</template>
