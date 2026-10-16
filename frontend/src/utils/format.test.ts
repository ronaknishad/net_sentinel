import { fmtBytes, fmtInt, fmtPct, statusLabel } from './format'

describe('format helpers', () => {
  it('formats counts and percentages', () => {
    expect(fmtInt(1250)).toBe('1,250')
    expect(fmtInt(null)).toBe('-')
    expect(fmtPct(0.9876, 1)).toBe('98.8%')
    expect(fmtPct(null)).toBe('n/a')
  })
  it('formats byte sizes', () => {
    expect(fmtBytes(512)).toBe('512 B')
    expect(fmtBytes(2048)).toBe('2.0 KB')
  })
  it('labels alert statuses', () => {
    expect(statusLabel('under_review')).toBe('Under review')
  })
})
