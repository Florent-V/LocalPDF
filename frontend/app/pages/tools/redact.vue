<script setup>
import PdfRedactCanvas from '~/components/pdf/PdfRedactCanvas.vue'

const { job, loading, create, apply, abandon } = useJobResource('/api/v1/security/redact')

const file = ref(null)
const mode = ref('manual')
const searchTerms = ref('')
const rectangles = ref([])

async function onUpload() {
  if (!file.value) return
  const result = await create(file.value)
  if (result) rectangles.value = []
}

async function onApply() {
  const body = mode.value === 'manual'
    ? { rectangles: rectangles.value }
    : { terms: searchTerms.value.split(',').map(t => t.trim()).filter(Boolean) }
  const ok = await apply(body, 'redacted.pdf', 'Erreur lors de la censure')
  if (ok) rectangles.value = []
}

async function onAbandon() {
  await abandon()
  rectangles.value = []
}
</script>

<template>
  <div>
    <div class="mb-2 flex items-start justify-between gap-4">
      <h1 class="text-2xl font-bold">
        Censurer un PDF
      </h1>
      <UButton
        v-if="job"
        :loading="loading"
        @click="onApply"
      >
        Télécharger le PDF censuré
      </UButton>
    </div>
    <p class="mb-6 text-(--ui-text-muted)">
      Masquez définitivement des zones sensibles ou recherchez et supprimez du texte.
    </p>

    <FileDropzone
      v-if="!job"
      accept=".pdf"
      @files-selected="file = $event[0]; onUpload()"
    />

    <div
      v-else
      class="space-y-4"
    >
      <USelect
        v-model="mode"
        :items="[{ label: 'Rectangles manuels', value: 'manual' }, { label: 'Recherche de texte', value: 'search' }]"
      />

      <div
        v-if="mode === 'search'"
        class="rounded-lg border border-(--ui-border) p-4"
      >
        <UFormField label="Termes à censurer (séparés par des virgules)">
          <UInput v-model="searchTerms" />
        </UFormField>
      </div>

      <PdfRedactCanvas
        v-if="mode === 'manual'"
        v-model="rectangles"
        :file="file"
      />

      <div class="flex gap-2">
        <UButton
          :loading="loading"
          @click="onApply"
        >
          Télécharger le PDF censuré
        </UButton>
        <UButton
          color="neutral"
          variant="ghost"
          @click="onAbandon"
        >
          Annuler
        </UButton>
      </div>
    </div>
  </div>
</template>
