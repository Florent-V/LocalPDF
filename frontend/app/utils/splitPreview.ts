export function computeEveryGroups(pageCount: number, everyN: number): Record<number, number> | null {
  if (!pageCount) return null
  const n = Math.max(1, Math.floor(everyN) || 1)
  const groups: Record<number, number> = {}
  for (let page = 1; page <= pageCount; page++) {
    groups[page] = Math.floor((page - 1) / n)
  }
  return groups
}

export function computeEverySummary(pageCount: number, everyN: number): string {
  if (!pageCount) return ''
  const n = Math.max(1, Math.floor(everyN) || 1)
  const fileCount = Math.ceil(pageCount / n)
  if (n === 1) return `${fileCount} fichiers, une page chacun.`
  const lastSize = pageCount - n * (fileCount - 1)
  return lastSize === n
    ? `${fileCount} fichiers de ${n} pages chacun.`
    : `${fileCount} fichiers : ${fileCount - 1} de ${n} pages, 1 dernier de ${lastSize} page(s).`
}
