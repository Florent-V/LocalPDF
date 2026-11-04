<script setup>
const { loading, submit } = useToolSubmit()

const file = ref(null)
const password = ref('')

async function onSubmit() {
  if (!file.value || !password.value) return
  const form = new FormData()
  form.append('file', file.value)
  form.append('password', password.value)
  await submit('/api/v1/security/unlock', form, 'unlocked.pdf', 'Erreur lors du déverrouillage')
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
