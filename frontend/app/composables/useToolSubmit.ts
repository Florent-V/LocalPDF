export function useToolSubmit() {
  const { uploadForm } = useApi()
  const toast = useToast()
  const loading = ref(false)

  async function submit(path: string, form: FormData, filename: string, errorTitle: string) {
    loading.value = true
    try {
      const blob = await uploadForm(path, form)
      downloadBlob(blob, filename)
      return true
    } catch (e: unknown) {
      toast.add({
        title: errorTitle,
        description: await extractErrorMessage(e),
        color: 'error'
      })
      return false
    } finally {
      loading.value = false
    }
  }

  return { loading, submit }
}
