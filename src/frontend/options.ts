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

export const COMMON_AIRLINES = [
  { value: 'UO', label: 'UO · 香港快運' },
  { value: 'GK', label: 'GK · 捷星日本' },
  { value: 'MM', label: 'MM · 樂桃航空' },
  { value: '7C', label: '7C · 濟州航空' },
  { value: 'TR', label: 'TR · 酷航' },
  { value: 'CX', label: 'CX · 國泰航空' },
  { value: 'JL', label: 'JL · 日本航空' },
  { value: 'NH', label: 'NH · 全日空' },
  { value: 'BR', label: 'BR · 長榮航空' },
  { value: 'CI', label: 'CI · 中華航空' },
  { value: 'VN', label: 'VN · 越南航空' },
  { value: 'HX', label: 'HX · 香港航空' },
] as const

/** Uppercase, 2-3 alphanumeric IATA code, or null when invalid. */
export function normalizeAirlineCode(raw: string): string | null {
  const code = raw.trim().toUpperCase()
  return /^[A-Z0-9]{2,3}$/.test(code) ? code : null
}

/** Normalizes camelCase prop arrays or legacy JSON/comma strings to a code list. */
export function parseAirlines(value: unknown): string[] | null {
  if (Array.isArray(value)) {
    return value.map((code) => String(code).toUpperCase()).filter(Boolean)
  }
  if (typeof value !== 'string' || !value.trim()) {
    return null
  }
  try {
    const parsed: unknown = JSON.parse(value)
    return Array.isArray(parsed) ? parseAirlines(parsed) : null
  } catch {
    return value
      .split(',')
      .map((code) => normalizeAirlineCode(code))
      .filter((code): code is string => code !== null)
  }
}
