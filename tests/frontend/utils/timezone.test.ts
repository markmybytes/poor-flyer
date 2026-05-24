import {
  calculateDaysRemaining,
  formatLocalDateTime,
  parsePureCalendarDate,
} from '@/utils/timezone'
import { describe, expect, it } from 'vitest'

describe('parsePureCalendarDate', () => {
  it('returns null for null input', () => {
    expect(parsePureCalendarDate(null)).toBeNull()
  })

  it('returns null for undefined input', () => {
    expect(parsePureCalendarDate(undefined)).toBeNull()
  })

  it('returns null for empty string', () => {
    expect(parsePureCalendarDate('')).toBeNull()
  })

  it('parses YYYY-MM-DD as local date without UTC shift', () => {
    const result = parsePureCalendarDate('2024-06-15')
    expect(result).not.toBeNull()
    expect(result!.getFullYear()).toBe(2024)
    expect(result!.getMonth()).toBe(5)
    expect(result!.getDate()).toBe(15)
  })

  it('parses first day of year correctly', () => {
    const result = parsePureCalendarDate('2025-01-01')
    expect(result!.getFullYear()).toBe(2025)
    expect(result!.getMonth()).toBe(0)
    expect(result!.getDate()).toBe(1)
  })

  it('parses last day of year correctly', () => {
    const result = parsePureCalendarDate('2024-12-31')
    expect(result!.getFullYear()).toBe(2024)
    expect(result!.getMonth()).toBe(11)
    expect(result!.getDate()).toBe(31)
  })

  it('does not shift day forward due to UTC interpretation', () => {
    const result = parsePureCalendarDate('2024-01-31')
    expect(result!.getDate()).toBe(31)
  })

  it('returns a Date for a non-standard string', () => {
    const result = parsePureCalendarDate('2024-06')
    expect(result).toBeInstanceOf(Date)
  })
})

describe('formatLocalDateTime', () => {
  it('returns fallback for null', () => {
    expect(formatLocalDateTime(null)).toBe('—')
  })

  it('returns fallback for undefined', () => {
    expect(formatLocalDateTime(undefined)).toBe('—')
  })

  it('returns custom fallback when provided', () => {
    expect(formatLocalDateTime(null, 'N/A')).toBe('N/A')
  })

  it('formats a valid ISO string', () => {
    const result = formatLocalDateTime('2024-06-15T10:30:00Z')
    expect(typeof result).toBe('string')
    expect(result).not.toBe('—')
    expect(result.length).toBeGreaterThan(0)
  })

  it('normalizes Python comma milliseconds format', () => {
    const result = formatLocalDateTime('2024-06-15 10:30:00,123')
    expect(typeof result).toBe('string')
    expect(result).not.toBe('2024-06-15 10:30:00,123')
  })

  it('returns the original string for unparseable values', () => {
    expect(formatLocalDateTime('not-a-date')).toBe('not-a-date')
  })
})

describe('calculateDaysRemaining', () => {
  it('returns 0 for null', () => {
    expect(calculateDaysRemaining(null)).toBe(0)
  })

  it('returns 0 for undefined', () => {
    expect(calculateDaysRemaining(undefined)).toBe(0)
  })

  it('returns a positive number for a future date', () => {
    const today = new Date()
    const nextYear = new Date(today.getFullYear() + 1, today.getMonth(), today.getDate())
    const yyyy = String(nextYear.getFullYear())
    const mm = String(nextYear.getMonth() + 1).padStart(2, '0')
    const dd = String(nextYear.getDate()).padStart(2, '0')
    expect(calculateDaysRemaining(`${yyyy}-${mm}-${dd}`)).toBeGreaterThanOrEqual(364)
    expect(calculateDaysRemaining(`${yyyy}-${mm}-${dd}`)).toBeLessThanOrEqual(366)
  })

  it('returns a negative number for a past date', () => {
    const today = new Date()
    const tenDaysAgo = new Date(today.getFullYear(), today.getMonth(), today.getDate() - 10)
    const yyyy = String(tenDaysAgo.getFullYear())
    const mm = String(tenDaysAgo.getMonth() + 1).padStart(2, '0')
    const dd = String(tenDaysAgo.getDate()).padStart(2, '0')
    expect(calculateDaysRemaining(`${yyyy}-${mm}-${dd}`)).toBe(-10)
  })

  it('returns 0 for today', () => {
    const today = new Date()
    const yyyy = String(today.getFullYear())
    const mm = String(today.getMonth() + 1).padStart(2, '0')
    const dd = String(today.getDate()).padStart(2, '0')
    expect(calculateDaysRemaining(`${yyyy}-${mm}-${dd}`)).toBe(0)
  })
})
