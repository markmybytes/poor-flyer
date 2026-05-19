export interface Rule37Analysis {
  phase: 'BUY_SIGNAL' | 'OBSERVING' | 'WAITING' | string
  cutoffDate: string
  historyBestVal: number | null
  latestVal: number | null
  allTimeHigh: number | null
  allTimeLow: number | null
}

export interface FareSnapshot {
  id?: string
  flightNumber?: string | null
  departureAt?: string | null
  arrivalAt?: string | null
  fare: number | null
  scrapeStatus: string
  errorMessage?: string | null
  createdAt: string
}

export interface Flight {
  id: string
  origin: string
  destination: string
  flightDate: string
  deadline: string | null
  isActive: boolean
  createdAt?: string
  fareSnapshots?: FareSnapshot[]
  rule37Analysis?: Rule37Analysis | null
}
