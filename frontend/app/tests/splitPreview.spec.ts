import { describe, expect, it } from 'vitest'
import { computeEveryGroups, computeEverySummary } from '~/utils/splitPreview'

describe('computeEveryGroups', () => {
  it('returns null when pageCount is 0', () => {
    expect(computeEveryGroups(0, 2)).toBeNull()
  })

  it('groups pages into chunks of n', () => {
    expect(computeEveryGroups(5, 2)).toEqual({ 1: 0, 2: 0, 3: 1, 4: 1, 5: 2 })
  })

  it('treats n < 1 as n = 1', () => {
    expect(computeEveryGroups(3, 0)).toEqual({ 1: 0, 2: 1, 3: 2 })
  })
})

describe('computeEverySummary', () => {
  it('returns empty string when pageCount is 0', () => {
    expect(computeEverySummary(0, 2)).toBe('')
  })

  it('describes one page per file when n = 1', () => {
    expect(computeEverySummary(3, 1)).toBe('3 fichiers, une page chacun.')
  })

  it('describes even chunks', () => {
    expect(computeEverySummary(6, 2)).toBe('3 fichiers de 2 pages chacun.')
  })

  it('describes an uneven last chunk', () => {
    expect(computeEverySummary(5, 2)).toBe('3 fichiers : 2 de 2 pages, 1 dernier de 1 page(s).')
  })
})
