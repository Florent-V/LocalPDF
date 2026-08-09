export function useAiConfig() {
  function getConfig(): object | null {
    if (typeof window === 'undefined') return null
    const raw = localStorage.getItem('localpdf-ai-config')
    return raw ? JSON.parse(raw) : null
  }

  return { getConfig }
}
