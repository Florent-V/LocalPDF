<script setup>
const { loading, submit } = useToolSubmit()

const file = ref(null)
const userPassword = ref('')
const ownerPassword = ref('')
const allowPrinting = ref(true)
const allowCopying = ref(false)

async function onSubmit() {
  if (!file.value || !userPassword.value) return
  const form = new FormData()
  form.append('file', file.value)
  form.append('user_password', userPassword.value)
  if (ownerPassword.value) form.append('owner_password', ownerPassword.value)
  form.append('allow_printing', String(allowPrinting.value))
  form.append('allow_copying', String(allowCopying.value))
  await submit('/api/v1/security/protect', form, 'protected.pdf', 'Erreur lors de la protection')
}
</script>

<template>
  <div>
    <h1 class="mb-2 text-2xl font-bold">
      Protéger par mot de passe
    </h1>
    <p class="mb-6 text-(--ui-text-muted)">
      Chiffrez un PDF avec un mot de passe utilisateur (et optionnellement propriétaire).
    </p>

    <FileDropzone
      accept=".pdf"
      @files-selected="file = $event[0]"
    />

    <div class="mt-6 space-y-4 rounded-lg border border-(--ui-border) p-4">
      <UFormField label="Mot de passe utilisateur">
        <UInput
          v-model="userPassword"
          type="password"
        />
      </UFormField>
      <UFormField label="Mot de passe propriétaire (optionnel)">
        <UInput
          v-model="ownerPassword"
          type="password"
        />
      </UFormField>
      <UCheckbox
        v-model="allowPrinting"
        label="Autoriser l'impression"
      />
      <UCheckbox
        v-model="allowCopying"
        label="Autoriser la copie/extraction"
      />
    </div>

    <UButton
      class="mt-6"
      size="lg"
      :loading="loading"
      :disabled="!file || !userPassword"
      @click="onSubmit"
    >
      Protéger
    </UButton>
  </div>
</template>
