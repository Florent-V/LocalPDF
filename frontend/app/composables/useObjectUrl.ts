/**
 * Tracks an object URL for a reactive Blob/File source: creates it when the
 * source changes, revokes the previous one, and revokes on unmount.
 * Extracted out of WatermarkPreview, which previously mixed this lifecycle
 * with canvas rendering and font-size logic.
 */
export function useObjectUrl(source: Ref<Blob | File | null | undefined>) {
  const url = ref<string | null>(null)

  watch(source, (value) => {
    if (url.value) URL.revokeObjectURL(url.value)
    url.value = value ? URL.createObjectURL(value) : null
  }, { immediate: true })

  onBeforeUnmount(() => {
    if (url.value) URL.revokeObjectURL(url.value)
  })

  return url
}
