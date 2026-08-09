import { describe, expect, it } from 'vitest'
import { downloadBlob } from '~/utils/downloadBlob'

describe('downloadBlob', () => {
  it('is defined', () => {
    expect(downloadBlob).toBeDefined()
  })
})
