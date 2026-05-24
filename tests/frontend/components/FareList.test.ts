import FareList from '@/Components/FareList.vue'
import type { Flight } from '@/types'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

const baseFlight: Flight = {
  id: 'f1',
  sequence: 0,
  origin: 'HKG',
  destination: 'NRT',
  flightDate: '2025-12-01',
  fareSnapshots: [],
}

describe('FareList', () => {
  it('renders without crashing with empty snapshots', () => {
    const wrapper = mount(FareList, {
      props: { flight: baseFlight },
    })
    expect(wrapper.exists()).toBe(true)
  })

  it('renders without crashing with successful snapshots', () => {
    const wrapper = mount(FareList, {
      props: {
        flight: {
          ...baseFlight,
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
        displayCurrency: 'HKD',
      },
    })
    expect(wrapper.exists()).toBe(true)
  })

  it('groups snapshots by date', () => {
    const wrapper = mount(FareList, {
      props: {
        flight: {
          ...baseFlight,
          fareSnapshots: [
            {
              id: 's1',
              fare: 1200,
              currency: 'HKD',
              scrapeStatus: 'success',
              createdAt: '2024-06-15T10:00:00Z',
            },
            {
              id: 's2',
              fare: 1100,
              currency: 'HKD',
              scrapeStatus: 'success',
              createdAt: '2024-06-16T10:00:00Z',
            },
          ],
        },
      },
    })
    expect(wrapper.findAll('.collapse').length).toBe(2)
  })

  it('shows failed snapshot with no valid fare message', () => {
    const wrapper = mount(FareList, {
      props: {
        flight: {
          ...baseFlight,
          fareSnapshots: [
            {
              id: 's1',
              fare: null,
              currency: 'HKD',
              scrapeStatus: 'error',
              createdAt: '2024-06-15T10:00:00Z',
            },
          ],
        },
      },
    })
    expect(wrapper.text()).toContain('無有效價格數據')
  })

  it('expand-all button appears when there are snapshots', () => {
    const wrapper = mount(FareList, {
      props: {
        flight: {
          ...baseFlight,
          fareSnapshots: [
            {
              id: 's1',
              fare: 900,
              currency: 'HKD',
              scrapeStatus: 'success',
              createdAt: '2024-06-15T10:00:00Z',
            },
          ],
        },
      },
    })
    expect(wrapper.find('button').exists()).toBe(true)
  })

  it('clicking expand-all toggles groups open', async () => {
    const wrapper = mount(FareList, {
      props: {
        flight: {
          ...baseFlight,
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
      },
    })
    const btn = wrapper.find('button')
    await btn.trigger('click')
    expect(wrapper.find('.collapse-open').exists()).toBe(true)
  })

  it('renders rule37Analysis cutoff date indicator when date matches', () => {
    const wrapper = mount(FareList, {
      props: {
        flight: {
          ...baseFlight,
          fareSnapshots: [
            {
              id: 's1',
              fare: 800,
              currency: 'HKD',
              scrapeStatus: 'success',
              createdAt: '2024-06-15T10:00:00Z',
            },
          ],
        },
        rule37Analysis: {
          phase: 'BUY_SIGNAL',
          cutoffDate: '2024-06-15',
          historyBestVal: 900,
        },
      },
    })
    expect(wrapper.text()).toContain('購買時機分析')
  })
})
