import type { Itinerary } from '@/types'

const CURRENCY_SIGNS: Record<string, string> = {
  HKD: '$',
  USD: '$',
  EUR: '€',
  GBP: '£',
  JPY: '¥',
  AUD: '$',
  CAD: '$',
  SGD: '$',
  CNY: '¥',
  KRW: '₩',
  TWD: '$',
  NZD: '$',
  CHF: 'Fr.',
  THB: '฿',
  MYR: 'RM',
  IDR: 'Rp',
  PHP: '₱',
  INR: '₹',
  AED: 'د.إ',
  SAR: '﷼',
  ZAR: 'R',
  MXN: '$',
  BRL: 'R$',
  TRY: '₺',
}

export function getCurrencySign(code: string): string {
  return !code ? '$' : CURRENCY_SIGNS[code.toUpperCase()] || '$'
}
export function fmtFare(amount: number | null, currencyCode: string | null = null) {
  if (amount === null || amount === undefined) {
    return '—'
  }

  const formatted = new Intl.NumberFormat('en-US', {
    maximumFractionDigits: 0,
  }).format(amount)
  return `${getCurrencySign(currencyCode)}${formatted}`
}

export function fmtDate(iso: string | null) {
  return iso ? iso.replace(/-/g, '/') : '—'
}

export function fmtTime(iso: string | null) {
  if (!iso) {
    return '—'
  }

  // flight scheduled times arrive without a zone suffix (flight-local by
  // design); render them literally instead of shifting through Date
  const naive = iso.match(/^\d{4}-\d{2}-\d{2}[T ](\d{2}:\d{2})(?::\d{2})?/)
  if (naive) {
    return naive[1]
  }

  return new Date(iso).toLocaleTimeString('zh-HK', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

export function fmtTz(iso: string | null) {
  return iso ? (iso.match(/([+-]\d{2}:\d{2}|Z)$/) || [''])[0] : ''
}

export function fmtItineraryName(itinerary: Itinerary) {
  if (!itinerary.flights || itinerary.flights.length === 0) {
    return ''
  }
  if (itinerary.tripType === 'SINGLE') {
    return `${itinerary.flights[0].origin} → ${itinerary.flights[0].destination}`
  } else if (itinerary.tripType === 'ROUND_TRIP') {
    return `${itinerary.flights[0].origin} ⇄ ${itinerary.flights[0].destination}`
  }
  return itinerary.flights.map((f) => `${f.origin} → ${f.destination}`).join(' | ')
}
