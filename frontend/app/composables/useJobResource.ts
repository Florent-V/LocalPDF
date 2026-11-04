/**
 * Shared create/apply/abandon job lifecycle for the two-step tools
 * (organize, redact): upload a file to get a job, PATCH it with the
 * edits, download the result. `basePath` is the router prefix, e.g.
 * "/api/v1/organize" or "/api/v1/security/redact" — job routes are always
 * `${basePath}/jobs` and `${basePath}/jobs/{id}`.
 */
export function useJobResource(basePath: string) {
  const { api, getFile } = useApi()
  const toast = useToast()
  const loading = ref(false)
  const job = ref<Record<string, unknown> & { job_id: string } | null>(null)

  async function create(file: File) {
    loading.value = true
    try {
      const form = new FormData()
      form.append('file', file)
      job.value = await api(`${basePath}/jobs`, {
        method: 'POST',
        body: form
      })
      return job.value
    } catch (e) {
      toast.add({
        title: 'Erreur lors de la création du job',
        description: await extractErrorMessage(e),
        color: 'error'
      })
      return null
    } finally {
      loading.value = false
    }
  }

  async function apply(patchBody: object, downloadFilename: string, errorTitle: string) {
    if (!job.value) return false
    loading.value = true
    try {
      await api(`${basePath}/jobs/${job.value.job_id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: patchBody
      })
      const blob = await getFile(`${basePath}/jobs/${job.value.job_id}/download`)
      downloadBlob(blob, downloadFilename)
      job.value = null
      return true
    } catch (e) {
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

  async function abandon() {
    if (!job.value) return
    try {
      await api(`${basePath}/jobs/${job.value.job_id}`, { method: 'DELETE' })
    } catch (e) {
      toast.add({
        title: 'Erreur lors de l\'annulation',
        description: await extractErrorMessage(e),
        color: 'error'
      })
    } finally {
      job.value = null
    }
  }

  return { job, loading, create, apply, abandon }
}
