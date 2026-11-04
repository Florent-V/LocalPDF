// The whole app is reserved to users logged in through the OAuth server.
// The real protection is the API's (401 without a session); this only sends
// the visitor to the login instead of showing a page that cannot work.
export default defineNuxtRouteMiddleware(async (to) => {
  // The OAuth server refused the login: show why, do not loop back to it.
  if (to.query.auth_error) {
    return
  }
  const { user, ensureLoaded, login } = useUser()
  await ensureLoaded()
  if (!user.value) {
    login(to.fullPath)
    return abortNavigation()
  }
})
