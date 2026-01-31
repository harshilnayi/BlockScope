import { describe, test, expect } from 'vitest'
import { isNonEmptyString, clampNumber, formatFileSize } from '../utils'

describe('utils functions', () => {
  test('isNonEmptyString returns true for valid string', () => {
    expect(isNonEmptyString('hello')).toBe(true)
  })

  test('isNonEmptyString returns false for empty or invalid input', () => {
    expect(isNonEmptyString('')).toBe(false)
    expect(isNonEmptyString('   ')).toBe(false)
    expect(isNonEmptyString(null)).toBe(false)
  })

  test('clampNumber clamps values within range', () => {
    expect(clampNumber(5, 0, 10)).toBe(5)
    expect(clampNumber(-5, 0, 10)).toBe(0)
    expect(clampNumber(20, 0, 10)).toBe(10)
  })

  test('formatFileSize formats bytes correctly', () => {
    expect(formatFileSize(500)).toBe('500 B')
    expect(formatFileSize(2048)).toBe('2.0 KB')
    expect(formatFileSize(5 * 1024 * 1024)).toBe('5.0 MB')
  })
})
