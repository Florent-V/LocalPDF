export function useApi() {
  // Same-origin calls: the session cookie goes along by itself, there is no
  // token to handle in the browser.
  const { login } = useUser()
  const api = $fetch.create({
    onResponseError({ response }) {
      // 401 = session closed (revoked, access removed, expired): log in
      // again, then come back to the current page.
      if (response.status === 401) {
        login()
      }
    }
  })

  async function uploadForm(path: string, form: FormData): Promise<Blob> {
    return api(path, {
      method: 'POST',
      body: form,
      responseType: 'blob'
    })
  }

  async function postJson(path: string, body?: object) {
    return api(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body
    })
  }

  async function patchJson(path: string, body?: object) {
    return api(path, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body
    })
  }

  async function getFile(path: string): Promise<Blob> {
    return api(path, {
      method: 'GET',
      responseType: 'blob'
    })
  }

  return { api, uploadForm, postJson, patchJson, getFile }
}
