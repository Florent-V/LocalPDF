import { describe, expect, it } from 'vitest'
import { extractErrorMessage } from '~/utils/extractErrorMessage'

describe('extractErrorMessage', () => {
  it('reads .detail from a Blob error body (uploadForm/getFile use responseType: "blob", so ofetch parses error bodies as Blob too)', async () => {
    const blob = new Blob([JSON.stringify({ detail: 'Mot de passe incorrect.' })], { type: 'application/json' })
    const message = await extractErrorMessage({ data: blob })
    expect(message).toBe('Mot de passe incorrect.')
  })

  it('reads .detail from a plain parsed JSON error body', async () => {
    const message = await extractErrorMessage({ data: { detail: 'Fichier trop volumineux.' } })
    expect(message).toBe('Fichier trop volumineux.')
  })

  it('falls back to .message when the Blob body is not valid JSON', async () => {
    const blob = new Blob(['not json'], { type: 'text/plain' })
    const message = await extractErrorMessage({ data: blob, message: 'Network Error' })
    expect(message).toBe('Network Error')
  })

  it('falls back to .message when there is no data at all', async () => {
    const message = await extractErrorMessage({ message: 'Network Error' })
    expect(message).toBe('Network Error')
  })

  it('falls back to the default message when nothing is usable', async () => {
    const message = await extractErrorMessage({})
    expect(message).toBe('Erreur inconnue.')
  })
})
