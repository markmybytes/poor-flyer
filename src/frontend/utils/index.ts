export function fmtFare(fare: number | null) {
  return fare !== null ? `$${Math.round(fare)}` : '—'
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
