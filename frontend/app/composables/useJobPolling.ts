export function useJobPolling() {
  async function waitForResult(
    downloadFn: () => Promise<Blob>,
    readyFn: () => Promise<boolean>,
    options: { interval?: number, timeout?: number } = {}
  ) {
    const { interval = 1000, timeout = 60000 } = options
    const start = Date.now()
    while (Date.now() - start < timeout) {
      if (await readyFn()) {
        return downloadFn()
      }
      await new Promise(resolve => setTimeout(resolve, interval))
    }
    throw new Error('Timeout en attendant le résultat du traitement.')
  }

  return { waitForResult }
}
