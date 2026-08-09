import type { PDFDocumentProxy } from 'pdfjs-dist'

let workerConfigured = false

async function loadPdfjs() {
  const pdfjsLib = await import('pdfjs-dist')
  if (!workerConfigured) {
    const workerUrl = (await import('pdfjs-dist/build/pdf.worker.min.mjs?url')).default
    pdfjsLib.GlobalWorkerOptions.workerSrc = workerUrl
    workerConfigured = true
  }
  return pdfjsLib
}

export function usePdfRenderer() {
  async function loadDocument(file: File): Promise<PDFDocumentProxy> {
    const pdfjsLib = await loadPdfjs()
    const data = await file.arrayBuffer()
    return pdfjsLib.getDocument({ data }).promise
  }

  async function renderPageThumbnail(doc: PDFDocumentProxy, pageNumber: number, maxWidth = 220): Promise<string> {
    const page = await doc.getPage(pageNumber)
    const scale = maxWidth / page.getViewport({ scale: 1 }).width
    const viewport = page.getViewport({ scale })
    const canvas = document.createElement('canvas')
    canvas.width = Math.ceil(viewport.width)
    canvas.height = Math.ceil(viewport.height)
    await page.render({ canvas, viewport }).promise
    const dataUrl = canvas.toDataURL('image/png')
    canvas.width = 0
    canvas.height = 0
    return dataUrl
  }

  async function renderThumbnails(doc: PDFDocumentProxy, opts: { maxWidth?: number } = {}): Promise<string[]> {
    const maxWidth = opts.maxWidth ?? 220
    const thumbnails: string[] = []
    for (let pageNumber = 1; pageNumber <= doc.numPages; pageNumber++) {
      thumbnails.push(await renderPageThumbnail(doc, pageNumber, maxWidth))
    }
    return thumbnails
  }

  async function renderPageToCanvas(
    doc: PDFDocumentProxy,
    pageNumber: number,
    canvasEl: HTMLCanvasElement,
    targetWidth: number
  ): Promise<{ scale: number, widthPt: number, heightPt: number }> {
    const page = await doc.getPage(pageNumber)
    const baseViewport = page.getViewport({ scale: 1 })
    const scale = targetWidth / baseViewport.width
    const viewport = page.getViewport({ scale })
    canvasEl.width = Math.ceil(viewport.width)
    canvasEl.height = Math.ceil(viewport.height)
    await page.render({ canvas: canvasEl, viewport }).promise
    return { scale, widthPt: baseViewport.width, heightPt: baseViewport.height }
  }

  return { loadDocument, renderPageThumbnail, renderThumbnails, renderPageToCanvas }
}
