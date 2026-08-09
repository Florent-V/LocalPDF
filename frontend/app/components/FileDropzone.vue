<script setup>
const props = defineProps({
  accept: { type: String, default: '.pdf' },
  multiple: { type: Boolean, default: false },
  maxSizeMb: { type: Number, default: 200 }
})

const emit = defineEmits(['files-selected'])

const dragging = ref(false)
const files = ref([])

function handleFiles(fileList) {
  const selected = Array.from(fileList)
  const maxBytes = props.maxSizeMb * 1024 * 1024
  const valid = selected.filter((f) => {
    if (f.size > maxBytes) {
      alert(`Fichier trop volumineux : ${f.name} (max ${props.maxSizeMb} Mo)`)
      return false
    }
    return true
  })
  files.value = props.multiple ? [...files.value, ...valid] : valid
  emit('files-selected', files.value)
}

function onDrop(e) {
  dragging.value = false
  handleFiles(e.dataTransfer.files)
}

function onFileInput(e) {
  handleFiles(e.target.files)
}

function removeFile(index) {
  files.value.splice(index, 1)
  emit('files-selected', files.value)
}
</script>

<template>
  <div>
    <div
      class="border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer"
      :class="dragging ? 'border-(--ui-primary) bg-(--ui-primary)/5' : 'border-(--ui-border) hover:border-(--ui-text-muted)'"
      @dragenter.prevent="dragging = true"
      @dragover.prevent="dragging = true"
      @dragleave.prevent="dragging = false"
      @drop.prevent="onDrop"
      @click="$refs.input.click()"
    >
      <UIcon
        name="i-lucide-upload-cloud"
        class="w-10 h-10 mx-auto text-(--ui-text-muted)"
      />
      <p class="mt-2 text-sm text-(--ui-text-muted)">
        Glissez-déposez vos fichiers ici ou cliquez pour parcourir
      </p>
      <p class="text-xs text-(--ui-text-muted)">
        {{ multiple ? 'Plusieurs fichiers acceptés' : 'Un seul fichier' }} · max {{ maxSizeMb }} Mo
      </p>
      <input
        ref="input"
        type="file"
        class="hidden"
        :accept="accept"
        :multiple="multiple"
        @change="onFileInput"
      >
    </div>

    <ul
      v-if="files.length"
      class="mt-4 space-y-2"
    >
      <li
        v-for="(file, index) in files"
        :key="file.name + index"
        class="flex items-center justify-between rounded-md border border-(--ui-border) px-3 py-2 text-sm"
      >
        <span class="truncate">{{ file.name }}</span>
        <UButton
          icon="i-lucide-x"
          size="xs"
          color="neutral"
          variant="ghost"
          @click.stop="removeFile(index)"
        />
      </li>
    </ul>
  </div>
</template>
