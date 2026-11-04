/**
 * Measures rendered text width via an offscreen canvas. The 2D context is
 * created once and reused — the previous inline version in WatermarkPreview
 * allocated a throwaway <canvas> on every reactive recalculation.
 */
let measureCtx: CanvasRenderingContext2D | null = null

export function measureTextWidth(text: string, font = 'bold 100px sans-serif'): number {
  if (!measureCtx) {
    measureCtx = document.createElement('canvas').getContext('2d')
  }
  if (!measureCtx) return 0
  measureCtx.font = font
  return measureCtx.measureText(text).width
}
