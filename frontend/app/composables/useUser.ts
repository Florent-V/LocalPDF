export interface AppUser {
  sub: string
  name: string | null
  email: string | null
  roles: string[]
}

// The session lives in the API (cookie HttpOnly, nothing readable here): the
// only thing the front knows is who is logged in, from GET /api/me.
export function useUser() {
  const user = useState<AppUser | null>('auth:user', () => null)
  const loaded = useState('auth:loaded', () => false)
  const loading = useState('auth:loading', () => false)

  async function refresh() {
    loading.value = true
    try {
      user.value = await $fetch<AppUser>('/api/me')
    } catch {
      user.value = null
    } finally {
      loaded.value = true
      loading.value = false
    }
  }

  // /api/me is asked once, then the answer is kept.
  async function ensureLoaded() {
    if (!loaded.value) {
      await refresh()
    }
  }

  // Full-page navigation to the API, which redirects to the OAuth server: not a router navigation.
  function login(returnTo: string = window.location.pathname + window.location.search) {
    window.location.href = `/auth/login?return_to=${encodeURIComponent(returnTo)}`
  }

  async function logout() {
    const { redirect } = await $fetch<{ redirect: string }>('/auth/logout', { method: 'POST' })
    window.location.href = redirect
  }

  return { user, loading, refresh, ensureLoaded, login, logout }
}
