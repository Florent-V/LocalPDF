export function useApi() {
  const config = useRuntimeConfig()

  const baseURL = config.public.apiBaseUrl as string

  async function uploadForm(path: string, form: FormData) {
    return $fetch(`${baseURL}${path}`, {
      method: 'POST',
      body: form,
      responseType: 'blob'
    })
  }

  async function postJson(path: string, body?: object) {
    return $fetch(`${baseURL}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body
    })
  }

  async function patchJson(path: string, body?: object) {
    return $fetch(`${baseURL}${path}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body
    })
  }

  async function getFile(path: string) {
    return $fetch(`${baseURL}${path}`, {
      method: 'GET',
      responseType: 'blob'
    })
  }

  return { baseURL, uploadForm, postJson, patchJson, getFile }
}
