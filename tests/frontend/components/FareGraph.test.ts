import FareGraph from '@/Components/FareGraph.vue'
import type { Itinerary } from '@/types'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

const baseItinerary: Itinerary = {
  id: 'it1',
  tripType: 'SINGLE',
  isActive: true,
  deadline: null,
  createdAt: '2024-01-01T00:00:00Z',
  flights: [],
}

describe('FareGraph', () => {
  it('renders without crashing when no flights present', () => {
    const wrapper = mount(FareGraph, {
      props: { itinerary: baseItinerary },
    })
    expect(wrapper.exists()).toBe(true)
  })

  it('shows empty state when itinerary has no flights', () => {
    const wrapper = mount(FareGraph, {
      props: { itinerary: baseItinerary },
    })
    expect(wrapper.text()).toContain('暫無趨勢數據')
  })

  it('renders canvas element when flights are present', () => {
    const wrapper = mount(FareGraph, {
      props: {
        itinerary: {
          ...baseItinerary,
          flights: [
            {
              id: 'f1',
              sequence: 0,
              origin: 'HKG',
              destination: 'NRT',
              flightDate: '2025-12-01',
              fareSnapshots: [
                {
                  id: 's1',
                  fare: 1200,
                  currency: 'HKD',
                  scrapeStatus: 'success',
                  createdAt: '2024-06-15T10:00:00Z',
                },
              ],
            },
          ],
        },
      },
    })
    expect(wrapper.find('canvas').exists()).toBe(true)
  })

  it('does not render canvas when itinerary has no flights', () => {
    const wrapper = mount(FareGraph, {
      props: { itinerary: baseItinerary },
    })
    expect(wrapper.find('canvas').exists()).toBe(false)
  })

  it('renders round trip itinerary without error', () => {
    const wrapper = mount(FareGraph, {
      props: {
        itinerary: {
          ...baseItinerary,
          tripType: 'ROUND_TRIP',
          statistics: { latestVal: 2500, allTimeHigh: 3000, allTimeLow: 2000 },
          flights: [
            {
              id: 'f1',
              sequence: 0,
              origin: 'HKG',
              destination: 'NRT',
              flightDate: '2025-12-01',
              fareSnapshots: [
                {
                  id: 's1',
                  fare: 1200,
                  currency: 'HKD',
                  scrapeStatus: 'success',
                  createdAt: '2024-06-15T10:00:00Z',
                },
              ],
            },
            {
              id: 'f2',
              sequence: 1,
              origin: 'NRT',
              destination: 'HKG',
              flightDate: '2025-12-08',
              fareSnapshots: [
                {
                  id: 's2',
                  fare: 1300,
                  currency: 'HKD',
                  scrapeStatus: 'success',
                  createdAt: '2024-06-15T10:00:00Z',
                },
              ],
            },
          ],
        },
      },
    })
    expect(wrapper.exists()).toBe(true)
  })

  it('renders with rule37Analysis cutoff date annotation without error', () => {
    const wrapper = mount(FareGraph, {
      props: {
        itinerary: {
          ...baseItinerary,
          rule37Analysis: {
            phase: 'OBSERVING',
            cutoffDate: '2024-09-01',
            historyBestVal: null,
          },
          flights: [
            {
              id: 'f1',
              sequence: 0,
              origin: 'HKG',
              destination: 'NRT',
              flightDate: '2025-12-01',
              fareSnapshots: [],
            },
          ],
        },
      },
    })
    expect(wrapper.exists()).toBe(true)
  })
})
