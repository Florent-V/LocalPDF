<script setup>
import PdfPageGrid from '~/components/pdf/PdfPageGrid.vue'

const { baseURL } = useApi()
const { getFile } = useApi()

const file = ref(null)
const loading = ref(false)
const job = ref(null)
const order = ref([])
const pageAngles = ref({})

function onLoaded(pageCount) {
  order.value = Array.from({ length: pageCount }, (_, i) => i + 1)
  const next = {}
  for (let p = 1; p <= pageCount; p++) {
    next[p] = pageAngles.value[p] || 0
  }
  pageAngles.value = next
}

function rotatePage(page, delta) {
  pageAngles.value = {
    ...pageAngles.value,
    [page]: (pageAngles.value[page] || 0) + delta
  }
}

function rotateAll(delta) {
  const next = {}
  for (const p of Object.keys(pageAngles.value)) {
    next[p] = pageAngles.value[p] + delta
  }
  pageAngles.value = next
}

async function onUpload() {
  if (!file.value) return
  loading.value = true
  try {
    const form = new FormData()
    form.append('file', file.value)
    job.value = await $fetch(`${baseURL}/api/v1/organize/jobs`, {
      method: 'POST',
      body: form
    })
  } catch (e) {
    alert('Erreur lors de la création du job : ' + (e?.message || 'inconnue'))
  } finally {
    loading.value = false
  }
}

async function onApply() {
  if (!job.value) return
  loading.value = true
  try {
    const nonZero = Object.fromEntries(
      Object.entries(pageAngles.value)
        .map(([p, a]) => [Number(p), a])
        .filter(([, a]) => a % 360 !== 0)
    )
    await $fetch(`${baseURL}/api/v1/organize/jobs/${job.value.job_id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: { new_order: order.value, rotations: nonZero }
    })
    const blob = await getFile(`/api/v1/organize/jobs/${job.value.job_id}/download`)
    downloadBlob(blob, 'organized.pdf')
    job.value = null
    order.value = []
    pageAngles.value = {}
  } catch (e) {
    alert('Erreur lors de l\'organisation : ' + (e?.message || 'inconnue'))
  } finally {
    loading.value = false
  }
}

async function onAbandon() {
  if (!job.value) return
  await $fetch(`${baseURL}/api/v1/organize/jobs/${job.value.job_id}`, { method: 'DELETE' })
  job.value = null
  order.value = []
  pageAngles.value = {}
}
</script>

<template>
  <div>
    <h1 class="mb-2 text-2xl font-bold">
      Organiser les pages
    </h1>
    <p class="mb-6 text-(--ui-text-muted)">
      Changez l'ordre des pages, supprimez celles qui ne vous intéressent pas, ou pivotez-les.
    </p>

    <div
      v-if="loading && !job"
      class="flex flex-col items-center justify-center gap-3 py-16 text-(--ui-text-muted)"
    >
      <UIcon
        name="i-lucide-loader-2"
        class="w-10 h-10 animate-spin"
      />
      <p class="text-sm font-medium">
        Analyse du document et génération des aperçus…
      </p>
      <p class="text-xs">
        Cela peut prendre quelques secondes pour un document volumineux.
      </p>
    </div>

    <FileDropzone
      v-else-if="!job"
      accept=".pdf"
      @files-selected="file = $event[0]; onUpload()"
    />

    <div
      v-else
      class="space-y-4"
    >
      <p class="text-sm text-(--ui-text-muted)">
        Glissez-déposez les pages pour changer l'ordre, supprimez celles à retirer, ou survolez une page pour la pivoter.
      </p>

      <div class="flex flex-wrap items-center gap-4">
        <div class="flex gap-2">
          <UButton
            :loading="loading"
            @click="onApply"
          >
            Télécharger le PDF réorganisé
          </UButton>
          <UButton
            color="neutral"
            variant="ghost"
            @click="onAbandon"
          >
            Annuler
          </UButton>
        </div>

        <div class="flex items-center gap-2">
          <span class="text-sm text-(--ui-text-muted)">Tout pivoter :</span>
          <UButton
            icon="i-lucide-rotate-ccw"
            size="sm"
            color="neutral"
            variant="soft"
            @click="rotateAll(-90)"
          />
          <UButton
            icon="i-lucide-rotate-cw"
            size="sm"
            color="neutral"
            variant="soft"
            @click="rotateAll(90)"
          />
        </div>
      </div>

      <PdfPageGrid
        :thumbnails="job.thumbnails"
        reorderable
        removable
        rotatable
        :rotations="pageAngles"
        @update:order="order = $event"
        @loaded="onLoaded"
        @rotate-page="rotatePage($event.page, $event.delta)"
      />

      <div class="flex gap-2">
        <UButton
          :loading="loading"
          @click="onApply"
        >
          Télécharger le PDF réorganisé
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
