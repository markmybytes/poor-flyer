import IndexPage from '@/Pages/Itineraries/Index.vue'
import type { Itinerary } from '@/types'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

const mockItinerary: Itinerary = {
  id: 'it1',
  tripType: 'SINGLE',
  isActive: true,
  deadline: null,
  createdAt: '2024-01-01T00:00:00Z',
  flights: [
    {
      id: 'f1',
      sequence: 0,
      origin: 'HKG',
      destination: 'NRT',
      flightDate: '2025-12-01',
    },
  ],
  statistics: { latestVal: 1200, allTimeHigh: 1500, allTimeLow: 1000 },
  rule37Analysis: null,
}

describe('Itineraries/Index', () => {
  it('renders without crashing with empty list', () => {
    const wrapper = mount(IndexPage, {
      props: { itineraries: [], baseCurrency: 'HKD' },
      global: { stubs: { AppLayout: { template: '<div><slot /></div>' } } },
    })
    expect(wrapper.exists()).toBe(true)
  })

  it('shows the correct total count in summary', () => {
    const wrapper = mount(IndexPage, {
      props: { itineraries: [mockItinerary], baseCurrency: 'HKD' },
      global: { stubs: { AppLayout: { template: '<div><slot /></div>' } } },
    })
    expect(wrapper.text()).toContain('1')
  })

  it('computes zero buy signals when none exist', () => {
    const wrapper = mount(IndexPage, {
      props: { itineraries: [mockItinerary], baseCurrency: 'HKD' },
      global: { stubs: { AppLayout: { template: '<div><slot /></div>' } } },
    })
    const statValues = wrapper.findAll('.stat-value')
    const buySignalStat = statValues.find((el) => el.text() === '0')
    expect(buySignalStat).toBeTruthy()
  })

  it('computes one buy signal when phase is BUY_SIGNAL', () => {
    const wrapper = mount(IndexPage, {
      props: {
        itineraries: [
          {
            ...mockItinerary,
            rule37Analysis: { phase: 'BUY_SIGNAL', cutoffDate: '2024-09-01', historyBestVal: 900 },
          },
        ],
        baseCurrency: 'HKD',
      },
      global: { stubs: { AppLayout: { template: '<div><slot /></div>' } } },
    })
    const statValues = wrapper.findAll('.stat-value')
    const buySignalStat = statValues.find((el) => el.text() === '1')
    expect(buySignalStat).toBeTruthy()
  })

  it('renders a card link for each itinerary', () => {
    const wrapper = mount(IndexPage, {
      props: { itineraries: [mockItinerary, { ...mockItinerary, id: 'it2' }], baseCurrency: 'HKD' },
      global: { stubs: { AppLayout: { template: '<div><slot /></div>' } } },
    })
    expect(wrapper.findAll('.card').length).toBe(2)
  })

  it('shows paused badge when itinerary is inactive', () => {
    const wrapper = mount(IndexPage, {
      props: {
        itineraries: [{ ...mockItinerary, isActive: false }],
        baseCurrency: 'HKD',
      },
      global: { stubs: { AppLayout: { template: '<div><slot /></div>' } } },
    })
    expect(wrapper.text()).toContain('已暫停')
  })

  it('shows create link button', () => {
    const wrapper = mount(IndexPage, {
      props: { itineraries: [], baseCurrency: 'HKD' },
      global: { stubs: { AppLayout: { template: '<div><slot /></div>' } } },
    })
    expect(wrapper.text()).toContain('新增監察項目')
  })
})
