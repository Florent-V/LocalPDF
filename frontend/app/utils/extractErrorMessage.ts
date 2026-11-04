/**
 * uploadForm/getFile request `responseType: 'blob'` for the success path,
 * but ofetch also parses non-2xx bodies according to that same
 * responseType — so a JSON error body (e.g. `{"detail": "..."}`) arrives
 * in `error.data` as a Blob, not a parsed object. This reads through that.
 */
export async function extractErrorMessage(e: unknown, fallback = 'Erreur inconnue.'): Promise<string> {
  const err = e as { data?: unknown, message?: string }

  if (err?.data instanceof Blob) {
    try {
      const parsed = JSON.parse(await err.data.text())
      if (parsed && typeof parsed.detail === 'string') return parsed.detail
    } catch {
      // Not JSON — fall through to the generic message below.
    }
  } else {
    const data = err?.data as { detail?: string } | undefined
    if (data?.detail) return data.detail
  }

  return err?.message || fallback
}
