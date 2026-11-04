/**
 * Pointer-driven rectangle drawing on a canvas: tracks the in-progress
 * draft rect in canvas-pixel space and converts any rect to a CSS style
 * for display-space overlay (extracted out of PdfRedactCanvas, which
 * previously duplicated the display-ratio math for the draft rect and for
 * each already-placed rect).
 */
const MIN_RECT_SIZE_PX = 6

export function useRectDrawing(canvasEl: Ref<HTMLCanvasElement | null>) {
  const drawing = ref(false)
  const draftRect = ref<{ x1: number, y1: number, x2: number, y2: number } | null>(null)

  function canvasPoint(evt: PointerEvent) {
    const rect = canvasEl.value!.getBoundingClientRect()
    const ratioX = canvasEl.value!.width / rect.width
    const ratioY = canvasEl.value!.height / rect.height
    return {
      x: (evt.clientX - rect.left) * ratioX,
      y: (evt.clientY - rect.top) * ratioY
    }
  }

  function onPointerDown(evt: PointerEvent) {
    const start = canvasPoint(evt)
    drawing.value = true
    draftRect.value = { x1: start.x, y1: start.y, x2: start.x, y2: start.y }
    ;(evt.target as Element).setPointerCapture(evt.pointerId)
  }

  function onPointerMove(evt: PointerEvent) {
    if (!drawing.value) return
    const point = canvasPoint(evt)
    draftRect.value = { ...draftRect.value!, x2: point.x, y2: point.y }
  }

  /** Finalizes the draft. Returns the normalized canvas-space rect, or null if too small/absent. */
  function onPointerUp() {
    if (!drawing.value || !draftRect.value) return null
    drawing.value = false
    const { x1, y1, x2, y2 } = draftRect.value
    draftRect.value = null
    if (Math.abs(x2 - x1) < MIN_RECT_SIZE_PX || Math.abs(y2 - y1) < MIN_RECT_SIZE_PX) return null
    return {
      x1: Math.min(x1, x2),
      y1: Math.min(y1, y2),
      x2: Math.max(x1, x2),
      y2: Math.max(y1, y2)
    }
  }

  function rectToStyle(rect: { x1: number, y1: number, x2: number, y2: number } | null) {
    if (!rect || !canvasEl.value) return {}
    const displayRatio = canvasEl.value.getBoundingClientRect().width / canvasEl.value.width
    const { x1, y1, x2, y2 } = rect
    return {
      left: `${Math.min(x1, x2) * displayRatio}px`,
      top: `${Math.min(y1, y2) * displayRatio}px`,
      width: `${Math.abs(x2 - x1) * displayRatio}px`,
      height: `${Math.abs(y2 - y1) * displayRatio}px`
    }
  }

  return { drawing, draftRect, onPointerDown, onPointerMove, onPointerUp, rectToStyle }
}
