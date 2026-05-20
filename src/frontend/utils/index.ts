import type { Itinerary } from '@/types'

export function fmtFare(amount: number | null, currencyCode: string = null) {
  if (amount === null || amount === undefined) {
    return '—'
  }

  if (currencyCode === null) {
    return `$${amount.toString()}`
  }

  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currencyCode,
    maximumFractionDigits: 0,
  }).format(amount)
}

export function fmtDate(iso: string | null) {
  return iso ? iso.replace(/-/g, '/') : '—'
}

export function fmtTime(iso: string | null) {
  return iso
    ? new Date(iso).toLocaleTimeString('zh-HK', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
      })
    : '—'
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
