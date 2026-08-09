<script setup>
import PdfPageGrid from '~/components/pdf/PdfPageGrid.vue'

const { uploadForm } = useApi()

const file = ref(null)
const start = ref(1)
const end = ref(null)
const mode = ref('range')
const everyN = ref(1)
const loading = ref(false)
const selectedPages = ref([])
const pageCount = ref(0)

const modeItems = [
  { value: 'range', label: 'Plage personnalisée', description: 'Extraire un intervalle de pages en un seul PDF.' },
  { value: 'every', label: 'Toutes les X pages', description: 'Découpe le document tous les X pages (X = 1 pour une page par fichier). Retour en ZIP.' }
]

function onPagesSelected(next) {
  if (!next.length) {
    selectedPages.value = []
    return
  }
  const min = Math.min(...next)
  const max = Math.max(...next)
  const range = Array.from({ length: max - min + 1 }, (_, i) => min + i)
  selectedPages.value = range
  start.value = min
  end.value = max
}

const everyGroups = computed(() => {
  if (mode.value !== 'every' || !pageCount.value) return null
  const n = Math.max(1, Math.floor(everyN.value) || 1)
  const groups = {}
  for (let page = 1; page <= pageCount.value; page++) {
    groups[page] = Math.floor((page - 1) / n)
  }
  return groups
})

const everySummary = computed(() => {
  if (mode.value !== 'every' || !pageCount.value) return ''
  const n = Math.max(1, Math.floor(everyN.value) || 1)
  const fileCount = Math.ceil(pageCount.value / n)
  if (n === 1) return `${fileCount} fichiers, une page chacun.`
  const lastSize = pageCount.value - n * (fileCount - 1)
  return lastSize === n
    ? `${fileCount} fichiers de ${n} pages chacun.`
    : `${fileCount} fichiers : ${fileCount - 1} de ${n} pages, 1 dernier de ${lastSize} page(s).`
})

async function onSubmit() {
  if (!file.value) return
  loading.value = true
  try {
    const form = new FormData()
    form.append('file', file.value)
    if (mode.value === 'range') {
      form.append('start', String(start.value || 1))
      if (end.value) form.append('end', String(end.value))
    } else {
      form.append('every_n', String(Math.max(1, Math.floor(everyN.value) || 1)))
    }
    const blob = await uploadForm('/api/v1/organize/split', form)
    const extension = mode.value === 'range' ? 'pdf' : 'zip'
    downloadBlob(blob, `split.${extension}`)
  } catch (e) {
    alert('Erreur lors de la division : ' + (e?.message || 'inconnue'))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div>
    <h1 class="mb-2 text-2xl font-bold">
      Diviser un PDF
    </h1>
    <p class="mb-6 text-(--ui-text-muted)">
      Extrayez une plage de pages ou découpez le document toutes les X pages.
    </p>

    <FileDropzone
      accept=".pdf"
      class="mb-6"
      @files-selected="file = $event[0]; selectedPages = []"
    />

    <div class="lg:grid lg:grid-cols-[22rem_1fr] lg:items-start lg:gap-6">
      <div class="lg:sticky lg:top-6">
        <div class="space-y-4 rounded-lg border border-(--ui-border) p-4">
          <URadioGroup
            v-model="mode"
            :items="modeItems"
          />

          <div
            v-if="mode === 'range'"
            class="flex gap-4"
          >
            <UFormField label="Page de début">
              <UInput
                v-model="start"
                type="number"
                min="1"
              />
            </UFormField>
            <UFormField label="Page de fin (optionnel)">
              <UInput
                v-model="end"
                type="number"
                min="1"
                placeholder="jusqu'à la fin"
              />
            </UFormField>
          </div>
          <p
            v-if="mode === 'range' && file"
            class="text-sm text-(--ui-text-muted)"
          >
            Cliquez la première puis la dernière page de la plage à extraire, ou saisissez directement les numéros ci-dessus (fonctionne même pour des pages non affichées).
          </p>

          <div v-if="mode === 'every'">
            <UFormField label="Nombre de pages par fichier">
              <UInput
                v-model="everyN"
                type="number"
                min="1"
                :max="pageCount || undefined"
                class="max-w-32"
              />
            </UFormField>
            <p
              v-if="everySummary"
              class="mt-2 text-sm text-(--ui-text-muted)"
            >
              {{ everySummary }}
            </p>
          </div>

          <UButton
            block
            size="lg"
            :loading="loading"
            :disabled="!file"
            @click="onSubmit"
          >
            Diviser
          </UButton>
        </div>
      </div>

      <div class="mt-6 lg:mt-0">
        <PdfPageGrid
          v-if="file"
          :file="file"
          :selectable="mode === 'range'"
          :model-value="selectedPages"
          :groups="everyGroups"
          @update:model-value="onPagesSelected"
          @loaded="pageCount = $event"
        />
        <div
          v-else
          class="flex min-h-70 flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-(--ui-border) p-8 text-center text-(--ui-text-muted)"
        >
          <UIcon
            name="i-lucide-layout-grid"
            class="h-8 w-8"
          />
          <p class="text-sm">
            L'aperçu des pages du PDF apparaîtra ici une fois le fichier chargé.
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
