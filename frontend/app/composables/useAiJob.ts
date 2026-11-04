/**
 * Shared "create a job from a PDF, then call an AI action on it" flow used
 * by summarize, translate and chat — previously copy-pasted 3x with chat.vue
 * missing the try/catch entirely (silent failure on job creation).
 */
export function useAiJob() {
  const { api } = useApi()
  const { getConfig } = useAiConfig()
  const toast = useToast()
  const loading = ref(false)
  const job = ref<Record<string, unknown> & { job_id: string } | null>(null)

  function requireConfig() {
    const config = getConfig()
    if (!config) {
      toast.add({
        title: 'Configuration requise',
        description: 'Veuillez configurer un provider IA dans Paramètres.',
        color: 'warning'
      })
      return null
    }
    return config
  }

  async function create(file: File) {
    loading.value = true
    try {
      const form = new FormData()
      form.append('file', file)
      job.value = await api(`/api/v1/ai/jobs`, {
        method: 'POST',
        body: form
      })
      return job.value
    } catch (e) {
      toast.add({ title: 'Erreur', description: await extractErrorMessage(e), color: 'error' })
      return null
    } finally {
      loading.value = false
    }
  }

  async function call(action: string, config: object, body: object = {}) {
    if (!job.value) return null
    loading.value = true
    try {
      return await api(`/api/v1/ai/jobs/${job.value.job_id}/${action}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: { config, ...body }
      })
    } catch (e) {
      toast.add({ title: 'Erreur IA', description: await extractErrorMessage(e), color: 'error' })
      return null
    } finally {
      loading.value = false
    }
  }

  return { job, loading, create, requireConfig, call }
}
