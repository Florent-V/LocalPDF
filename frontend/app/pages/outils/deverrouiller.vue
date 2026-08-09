<script setup>
const { uploadForm } = useApi()

const file = ref(null)
const password = ref('')
const loading = ref(false)

async function onSubmit() {
  if (!file.value || !password.value) return
  loading.value = true
  try {
    const form = new FormData()
    form.append('file', file.value)
    form.append('password', password.value)
    const blob = await uploadForm('/api/v1/security/unlock', form)
    downloadBlob(blob, 'unlocked.pdf')
  } catch (e) {
    alert('Erreur lors du déverrouillage : ' + (e?.message || 'inconnue'))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div>
    <h1 class="mb-2 text-2xl font-bold">
      Déverrouiller un PDF
    </h1>
    <p class="mb-6 text-(--ui-text-muted)">
      Retirez la protection par mot de passe d'un PDF (nécessite le mot de passe actuel).
    </p>

    <FileDropzone
      accept=".pdf"
      @files-selected="file = $event[0]"
    />

    <div class="mt-6 rounded-lg border border-(--ui-border) p-4">
      <UFormField label="Mot de passe actuel">
        <UInput
          v-model="password"
          type="password"
        />
      </UFormField>
    </div>

    <UButton
      class="mt-6"
      size="lg"
      :loading="loading"
      :disabled="!file || !password"
      @click="onSubmit"
    >
      Déverrouiller
    </UButton>
  </div>
</template>
