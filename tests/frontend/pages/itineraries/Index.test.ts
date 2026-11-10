import IndexPage from '@/Pages/Itineraries/Index.vue'
import type { Itinerary } from '@/types'
import { flushPromises, mount } from '@vue/test-utils'
import { router } from '@inertiajs/vue3'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useToast } from 'vue-toast-notification'

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

const archivedItinerary: Itinerary = {
  ...mockItinerary,
  archivedAt: '2026-10-01T04:05:06Z',
  rule37Analysis: undefined,
}

function mountIndex(props: Record<string, unknown> = {}) {
  return mount(IndexPage, {
    props: { itineraries: [mockItinerary], baseCurrency: 'HKD', ...props },
    global: { stubs: { AppLayout: { template: '<div><slot /></div>' } } },
  })
}

function mountArchivedView(props: Record<string, unknown> = {}) {
  window.history.replaceState({}, '', '/itineraries/?archived=1')
  return mountIndex({ itineraries: [archivedItinerary], ...props })
}

describe('Itineraries/Index', () => {
  beforeEach(() => {
    window.history.replaceState({}, '', '/itineraries/')
    vi.mocked(fetch).mockResolvedValue({ ok: true, json: async () => ({}) } as Response)
  })

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

  it('makes the whole archived card clickable with the restore button outside the anchor', () => {
    const wrapper = mountArchivedView()

    const card = wrapper.find('.card')
    const overlay = card.find('a.absolute.inset-0')
    expect(overlay.exists()).toBe(true)
    expect(overlay.attributes('href')).toBe('/itineraries/it1')

    const restoreBtn = card
      .findAll('button')
      .find((b) => b.text().trim() === '恢復追蹤')!
    expect(restoreBtn.exists()).toBe(true)
    expect(overlay.element.contains(restoreBtn.element)).toBe(false)
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

  it('switches to the archived view via router.get', async () => {
    const wrapper = mountIndex()
    await wrapper.findAll('button').find((b) => b.text() === '已封存')!.trigger('click')

    expect(router.get).toHaveBeenCalledWith(
      '/itineraries/',
      { archived: '1' },
      expect.objectContaining({ replace: true }),
    )
  })

  it('shows archived cards with 已封存 badge and no rule37 card in archived view', () => {
    const wrapper = mountArchivedView()

    expect(wrapper.text()).toContain('已封存')
    expect(wrapper.text()).toContain('封存於 2026/10/01')
    expect(wrapper.text()).not.toContain('購買時機分析')
    expect(wrapper.text()).not.toContain('可入手提示')
  })

  it('shows the archived empty state when no itineraries are archived', () => {
    const wrapper = mountArchivedView({ itineraries: [], baseCurrency: 'HKD' })

    expect(wrapper.text()).toContain('沒有已封存的旅程')
    expect(wrapper.findAll('.card').length).toBe(0)
  })

  it('asks for confirmation with re-archive notice before restoring', async () => {
    const wrapper = mountArchivedView()
    await wrapper.findAll('button').find((b) => b.text().trim() === '恢復追蹤')!.trigger('click')

    expect(wrapper.text()).toContain('恢復追蹤？')
    expect(wrapper.text()).toContain('重新封存')
  })

  it('restores via PATCH and reloads', async () => {
    const wrapper = mountArchivedView()
    await wrapper.findAll('button').find((b) => b.text().trim() === '恢復追蹤')!.trigger('click')

    const confirmBtn = wrapper.findAll('button').find((b) => b.text().trim() === '恢復追蹤' && b.attributes('type') === 'button')
    await confirmBtn!.trigger('click')
    await flushPromises()

    expect(fetch).toHaveBeenCalledWith(
      '/api/itineraries/it1',
      expect.objectContaining({
        method: 'PATCH',
        body: JSON.stringify({ archived: false }),
      }),
    )
    expect(vi.mocked(router.reload)).toHaveBeenCalled()
  })

  it('shows a toast on restore failure', async () => {
    vi.mocked(fetch).mockResolvedValue({ ok: false } as Response)
    const toast = useToast() as unknown as { error: ReturnType<typeof vi.fn> }
    const wrapper = mountArchivedView()
    await wrapper.findAll('button').find((b) => b.text().trim() === '恢復追蹤')!.trigger('click')

    const confirmBtn = wrapper
      .findAll('button')
      .find((b) => b.text().trim() === '恢復追蹤' && b.attributes('type') === 'button')
    await confirmBtn!.trigger('click')
    await flushPromises()

    expect(toast.error).toHaveBeenCalledWith('恢復追蹤失敗，請稍後再試')
  })

  it('keeps the summary stats panel rendered in the archived view, showing only the archived count', () => {
    const wrapper = mountArchivedView()

    const panel = wrapper.find('.stats-horizontal')
    expect(panel.exists()).toBe(true)
    expect(panel.findAll('.stat-title').map((el) => el.text())).toEqual(['已封存'])
  })

  it('renders the archived empty state with the same shape as the active one', () => {
    window.history.replaceState({}, '', '/itineraries/')
    const activeEmpty = mountIndex({ itineraries: [], baseCurrency: 'HKD' })
    window.history.replaceState({}, '', '/itineraries/?archived=1')
    const archivedEmpty = mountIndex({ itineraries: [], baseCurrency: 'HKD' })

    const activeHero = activeEmpty.find('.tracker-panel.hero')
    const archivedHero = archivedEmpty.find('.tracker-panel.hero')

    expect(activeHero.exists()).toBe(true)
    expect(activeHero.classes()).toEqual(archivedHero.classes())
    expect(archivedEmpty.find('.placeholder.avatar').exists()).toBe(true)
  })
})
