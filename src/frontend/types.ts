export interface PriceStats {
  latestVal: number | null
  allTimeHigh: number | null
  allTimeLow: number | null
}

export interface Rule37Analysis {
  phase: 'BUY_SIGNAL' | 'OBSERVING' | 'WAITING' | string
  cutoffDate: string
  historyBestVal: number | null
}

export interface FareSnapshot {
  id?: string
  flightNumber?: string | null
  departureAt?: string | null
  arrivalAt?: string | null
  fare: number | null
  currency: string
  scrapeStatus: string
  errorMessage?: string | null
  createdAt: string
}

export interface Flight {
  id: string
  sequence: number
  origin: string
  destination: string
  flightDate: string
  fareSnapshots?: FareSnapshot[]
}

export interface Itinerary {
  id: string
  tripType: string
  isActive: boolean
  deadline: string | null
  createdAt: string
  flights: Flight[]
  cabinClass?: string | null
  maxStops?: string | null
  airlines?: string[] | null
  statistics?: PriceStats | null
  rule37Analysis?: Rule37Analysis | null
}

export interface Settings {
  currency?: {
    baseCurrency?: string
    fxratesApiKey?: string
    cacheTtl?: string | number
  }
  email?: {
    recipients?: string
  }
  itinerary?: {
    disableDeparturedItineraries?: string
  }
  smtp?: {
    host?: string
    port?: string | number
    user?: string
    password?: string
    senderEmail?: string
    requireAuth?: string
    protocol?: string
  }
}
