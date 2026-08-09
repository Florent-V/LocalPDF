<script setup>
import PdfPageGrid from '~/components/pdf/PdfPageGrid.vue'

const { baseURL } = useApi()
const { uploadForm } = useApi()

const file = ref(null)
const fields = ref([])
const values = ref({})
const flatten = ref(false)
const loading = ref(false)

async function onInspect() {
  if (!file.value) return
  loading.value = true
  try {
    const form = new FormData()
    form.append('file', file.value)
    const result = await $fetch(`${baseURL}/api/v1/forms/inspect`, {
      method: 'POST',
      body: form
    })
    fields.value = result.fields
    values.value = Object.fromEntries(result.fields.map(f => [f.name, f.value || '']))
  } catch (e) {
    alert('Erreur lors de l\'inspection : ' + (e?.message || 'inconnue'))
  } finally {
    loading.value = false
  }
}

async function onFill() {
  if (!file.value) return
  loading.value = true
  try {
    const form = new FormData()
    form.append('file', file.value)
    form.append('values', JSON.stringify(values.value))
    form.append('flatten', String(flatten.value))
    const blob = await uploadForm('/api/v1/forms/fill', form)
    downloadBlob(blob, 'filled.pdf')
  } catch (e) {
    alert('Erreur lors du remplissage : ' + (e?.message || 'inconnue'))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div>
    <h1 class="mb-2 text-2xl font-bold">
      Remplir un formulaire PDF
    </h1>
    <p class="mb-6 text-(--ui-text-muted)">
      Détectez les champs d'un formulaire et renseignez-les directement.
    </p>

    <FileDropzone
      accept=".pdf"
      @files-selected="file = $event[0]; onInspect()"
    />

    <PdfPageGrid
      v-if="file"
      class="mt-4"
      :file="file"
    />

    <div
      v-if="fields.length"
      class="mt-6 space-y-4 rounded-lg border border-(--ui-border) p-4"
    >
      <UCheckbox
        v-model="flatten"
        label="Aplatir les champs après remplissage"
      />

      <div class="grid gap-4">
        <UFormField
          v-for="field in fields"
          :key="field.name"
          :label="field.name"
        >
          <USelect
            v-if="field.options && field.options.length"
            v-model="values[field.name]"
            :items="field.options"
          />
          <UInput
            v-else
            v-model="values[field.name]"
          />
        </UFormField>
      </div>

      <UButton
        :loading="loading"
        @click="onFill"
      >
        Remplir et télécharger
      </UButton>
    </div>

    <p
      v-else-if="file"
      class="mt-4 text-sm text-(--ui-text-muted)"
    >
      Aucun champ de formulaire détecté dans ce PDF.
    </p>
  </div>
</template>
