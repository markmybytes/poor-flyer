import ItineraryCard from '@/Components/ItineraryCard.vue'
import type { Itinerary } from '@/types'
import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

const baseItinerary: Itinerary = {
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

const archivedItinerary: Itinerary = {
  ...baseItinerary,
  archivedAt: '2026-10-01T04:05:06Z',
  rule37Analysis: undefined,
}

function mountCard(props: Record<string, unknown> = {}) {
  return mount(ItineraryCard, {
    props: { itinerary: baseItinerary, baseCurrency: 'HKD', ...props },
  })
}

describe('ItineraryCard', () => {
  it('renders a whole-card link overlay regardless of archived state', () => {
    const active = mountCard()
    const archived = mountCard({ itinerary: archivedItinerary, archived: true })

    expect(active.find('a.absolute.inset-0').exists()).toBe(true)
    expect(archived.find('a.absolute.inset-0').exists()).toBe(true)
    expect(active.find('a.absolute.inset-0').attributes('aria-label')).toBe('查看 HKG → NRT 詳情')
  })

  it('emits restore with the itinerary when the restore button is pressed', async () => {
    const wrapper = mountCard({ itinerary: archivedItinerary, archived: true })

    await wrapper.findAll('button').find((b) => b.text().trim() === '恢復追蹤')!.trigger('click')

    expect(wrapper.emitted('restore')).toEqual([[archivedItinerary]])
  })

  it('hides the rule37 panel and shows the archive footer when archived', () => {
    const archived = mountCard({ itinerary: archivedItinerary, archived: true })

    expect(archived.text()).toContain('封存於')
    expect(archived.text()).not.toContain('購買時機分析')
  })

  it('mutes the archived card variant and keeps groups hover on the active one', () => {
    const archived = mountCard({ itinerary: archivedItinerary, archived: true })
    const active = mountCard()

    expect(archived.find('.card').classes()).toContain('bg-base-200/40')
    expect(archived.find('.card').classes()).not.toContain('hover:-translate-y-1')
    expect(active.find('.card').classes()).toContain('hover:-translate-y-1')
  })

  it('shows the paused badge for inactive itineraries', () => {
    const wrapper = mountCard({ itinerary: { ...baseItinerary, isActive: false } })

    expect(wrapper.text()).toContain('已暫停')
  })
})
