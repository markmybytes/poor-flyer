/**
 * Parses a pure calendar date string (YYYY-MM-DD) safely as a local date block,
 * preventing Javascript from treating it as UTC midnight and shifting the day.
 */
export function parsePureCalendarDate(dateStr: string | null | undefined): Date | null {
  if (!dateStr) return null
  const parts = dateStr.split('-')
  if (parts.length !== 3) return new Date(dateStr)

  const year = parseInt(parts[0], 10)
  const month = parseInt(parts[1], 10) - 1 // JS months are 0-indexed
  const day = parseInt(parts[2], 10)

  return new Date(year, month, day)
}

/**
 * Standardizes display of exact timestamps across the API wire (e.g., logs, scrape points)
 */
export function formatLocalDateTime(value: string | null | undefined, fallback = '—'): string {
  if (!value) return fallback
  // Normalize old python comma milliseconds formats if present
  const normalized = value.replace(' ', 'T').replace(',', '.')
  const parsed = new Date(normalized)
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString()
}

/**
 * Safe utility to handle day count countdowns completely inside the user's local day context.
 */
export function calculateDaysRemaining(targetDateStr: string | null | undefined): number {
  const target = parsePureCalendarDate(targetDateStr)
  if (!target) return 0

  // Set both times to midnight local time to compute clean, integer day differences
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  target.setHours(0, 0, 0, 0)

  const diffTime = target.getTime() - today.getTime()
  return Math.ceil(diffTime / (1000 * 60 * 60 * 24))
}
