<script setup>
import PdfPageGrid from '~/components/pdf/PdfPageGrid.vue'
import WatermarkPreview from '~/components/pdf/WatermarkPreview.vue'

const { loading, submit } = useToolSubmit()

const file = ref(null)
const mode = ref('text')
const text = ref('Confidentiel')
const image = ref(null)
const position = ref('center')
const opacity = ref(0.3)
const width = ref(100)
const allPages = ref(true)
const selectedPages = ref([])

async function onSubmit() {
  if (!file.value) return
  const form = new FormData()
  form.append('file', file.value)
  if (mode.value === 'text') {
    form.append('text', text.value)
  } else if (image.value) {
    form.append('image', image.value)
    form.append('width', String(width.value))
  }
  form.append('position', position.value)
  form.append('opacity', String(opacity.value))
  if (!allPages.value && selectedPages.value.length) {
    form.append('pages', selectedPages.value.join(','))
  }
  await submit('/api/v1/modify/watermark', form, 'watermarked.pdf', 'Erreur lors de l\'ajout du filigrane')
}
</script>

<template>
  <div>
    <h1 class="mb-2 text-2xl font-bold">
      Ajouter un filigrane
    </h1>
    <p class="mb-6 text-(--ui-text-muted)">
      Insérez un texte ou une image en filigrane sur chaque page.
    </p>

    <FileDropzone
      accept=".pdf"
      @files-selected="file = $event[0]; selectedPages = []"
    />

    <WatermarkPreview
      v-if="file"
      class="mt-6"
      :file="file"
      :mode="mode"
      :text="text"
      :image="image"
      :image-width="width"
      :position="position"
      :opacity="opacity"
    />

    <div class="mt-6 space-y-4 rounded-lg border border-(--ui-border) p-4">
      <USelect
        v-model="mode"
        :items="[{ label: 'Texte', value: 'text' }, { label: 'Image', value: 'image' }]"
      />

      <UFormField
        v-if="mode === 'text'"
        label="Texte"
      >
        <UInput v-model="text" />
      </UFormField>

      <UFormField
        v-if="mode === 'image'"
        label="Image"
      >
        <input
          type="file"
          accept="image/*"
          @change="image = $event.target.files[0]"
        >
      </UFormField>
      <UFormField
        v-if="mode === 'image'"
        label="Largeur (px)"
      >
        <UInput
          v-model="width"
          type="number"
          min="16"
        />
      </UFormField>

      <UFormField label="Position">
        <USelect
          v-model="position"
          :items="[
            { label: 'Haut', value: 'top' },
            { label: 'Centre', value: 'center' },
            { label: 'Bas', value: 'bottom' },
            { label: 'Diagonale', value: 'diagonal' }
          ]"
        />
      </UFormField>
      <UFormField label="Opacité (0-1)">
        <UInput
          v-model="opacity"
          type="number"
          min="0"
          max="1"
          step="0.1"
        />
      </UFormField>
      <UFormField label="Pages">
        <UCheckbox
          v-model="allPages"
          label="Toutes les pages"
        />
      </UFormField>
    </div>

    <div
      v-if="file && !allPages"
      class="mt-4"
    >
      <p class="mb-2 text-sm text-(--ui-text-muted)">
        Cliquez les pages concernées par le filigrane.
      </p>
      <PdfPageGrid
        :file="file"
        selectable
        :model-value="selectedPages"
        @update:model-value="selectedPages = $event"
      />
    </div>

    <UButton
      class="mt-6"
      size="lg"
      :loading="loading"
      :disabled="!file || (mode === 'image' && !image)"
      @click="onSubmit"
    >
      Appliquer le filigrane
    </UButton>
  </div>
</template>
