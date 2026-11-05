export const CABIN_CLASS_OPTIONS = [
  { value: 'ECONOMY', label: '經濟艙' },
  { value: 'PREMIUM_ECONOMY', label: '豪華經濟艙' },
  { value: 'BUSINESS', label: '商務艙' },
  { value: 'FIRST', label: '頭等艙' },
] as const

export const MAX_STOPS_OPTIONS = [
  { value: 'ANY', label: '不限' },
  { value: 'NON_STOP', label: '直飛' },
  { value: 'ONE_STOP', label: '1 次轉機' },
  { value: 'TWO_PLUS_STOPS', label: '2 次或以上轉機' },
] as const

/** Uppercase, 2-3 alphanumeric IATA code, or null when invalid. */
export function normalizeAirlineCode(raw: string): string | null {
  const code = raw.trim().toUpperCase()
  return /^[A-Z0-9]{2,3}$/.test(code) ? code : null
}
