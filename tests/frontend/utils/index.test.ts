import type { Itinerary } from '@/types'
import { fmtDate, fmtFare, fmtItineraryName, fmtTime, fmtTz, getCurrencySign } from '@/utils'
import { describe, expect, it } from 'vitest'

describe('getCurrencySign', () => {
  it('returns $ for HKD', () => {
    expect(getCurrencySign('HKD')).toBe('$')
  })

  it('returns € for EUR', () => {
    expect(getCurrencySign('EUR')).toBe('€')
  })

  it('returns ¥ for JPY', () => {
    expect(getCurrencySign('JPY')).toBe('¥')
  })

  it('returns ₩ for KRW', () => {
    expect(getCurrencySign('KRW')).toBe('₩')
  })

  it('returns $ as default for unknown currency', () => {
    expect(getCurrencySign('ZZZ')).toBe('$')
  })

  it('returns $ for empty string', () => {
    expect(getCurrencySign('')).toBe('$')
  })

  it('is case insensitive', () => {
    expect(getCurrencySign('eur')).toBe('€')
  })
})

describe('fmtFare', () => {
  it('returns em dash for null', () => {
    expect(fmtFare(null)).toBe('—')
  })

  it('returns em dash for undefined', () => {
    expect(fmtFare(undefined as unknown as null)).toBe('—')
  })

  it('formats integer amount with currency sign', () => {
    expect(fmtFare(1200, 'HKD')).toBe('$1,200')
  })

  it('formats zero', () => {
    expect(fmtFare(0, 'HKD')).toBe('$0')
  })

  it('formats large number with comma separator', () => {
    expect(fmtFare(12345, 'USD')).toBe('$12,345')
  })

  it('truncates decimal places', () => {
    expect(fmtFare(99.99, 'EUR')).toBe('€100')
  })

  it('uses $ when currency is null', () => {
    expect(fmtFare(500, null)).toBe('$500')
  })
})

describe('fmtDate', () => {
  it('returns em dash for null', () => {
    expect(fmtDate(null)).toBe('—')
  })

  it('replaces dashes with slashes', () => {
    expect(fmtDate('2024-06-15')).toBe('2024/06/15')
  })

  it('handles already formatted date', () => {
    expect(fmtDate('2025-01-01')).toBe('2025/01/01')
  })
})

describe('fmtTime', () => {
  it('returns em dash for null', () => {
    expect(fmtTime(null)).toBe('—')
  })

  it('returns a time string for valid ISO', () => {
    const result = fmtTime('2024-06-15T09:30:00Z')
    expect(typeof result).toBe('string')
    expect(result).not.toBe('—')
  })

  it('renders naive flight-local times literally, no timezone shift', () => {
    expect(fmtTime('2026-12-05T21:30:00')).toBe('21:30')
    expect(fmtTime('2026-12-05 21:30')).toBe('21:30')
  })
})

describe('fmtTz', () => {
  it('returns empty string for null', () => {
    expect(fmtTz(null)).toBe('')
  })

  it('extracts Z suffix', () => {
    expect(fmtTz('2024-06-15T09:30:00Z')).toBe('Z')
  })

  it('extracts positive offset', () => {
    expect(fmtTz('2024-06-15T09:30:00+08:00')).toBe('+08:00')
  })

  it('extracts negative offset', () => {
    expect(fmtTz('2024-06-15T09:30:00-05:00')).toBe('-05:00')
  })
})

describe('fmtItineraryName', () => {
  it('returns empty string for no flights', () => {
    const it = { flights: [], tripType: 'SINGLE' } as unknown as Itinerary
    expect(fmtItineraryName(it)).toBe('')
  })

  it('formats SINGLE trip as origin → destination', () => {
    const it = {
      tripType: 'SINGLE',
      flights: [{ origin: 'HKG', destination: 'NRT' }],
    } as unknown as Itinerary
    expect(fmtItineraryName(it)).toBe('HKG → NRT')
  })

  it('formats ROUND_TRIP as origin ⇄ destination', () => {
    const it = {
      tripType: 'ROUND_TRIP',
      flights: [
        { origin: 'HKG', destination: 'NRT' },
        { origin: 'NRT', destination: 'HKG' },
      ],
    } as unknown as Itinerary
    expect(fmtItineraryName(it)).toBe('HKG ⇄ NRT')
  })

  it('formats MULTI_CITY as pipe-separated legs', () => {
    const it = {
      tripType: 'MULTI_CITY',
      flights: [
        { origin: 'HKG', destination: 'NRT' },
        { origin: 'NRT', destination: 'LHR' },
      ],
    } as unknown as Itinerary
    expect(fmtItineraryName(it)).toBe('HKG → NRT | NRT → LHR')
  })
})
