import DetailPage from '@/Pages/Itineraries/Detail.vue'
import { flushPromises, mount } from '@vue/test-utils'
import { router } from '@inertiajs/vue3'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const itinerary = {
  id: 'it-1',
  tripType: 'SINGLE',
  isActive: true,
  deadline: null,
  createdAt: '2026-01-01T00:00:00Z',
  flights: [
    { id: 'f1', sequence: 0, origin: 'HKG', destination: 'NRT', flightDate: '2026-12-01' },
  ],
}

const globalStubs = {
  AppLayout: { template: '<div><slot /></div>' },
  FareGraph: { template: '<div />' },
  FareList: { template: '<div />' },
}

function mountDetail(overrides: Record<string, unknown> = {}) {
  return mount(DetailPage, {
    props: {
      itinerary: { ...itinerary, ...overrides },
      baseCurrency: 'HKD',
    },
    global: { stubs: globalStubs },
  })
}

describe('Itineraries/Detail filters', () => {
  beforeEach(() => {
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: async () => ({ success: true }),
    } as Response)
  })

  it('renders read-only filter values from props', () => {
    const wrapper = mountDetail({
      cabinClass: 'BUSINESS',
      maxStops: 'NON_STOP',
      airlines: ['CX', 'JL'],
    })

    expect(wrapper.find('[data-tip="修改搜尋條件請刪除後重新建立"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('商務艙')
    expect(wrapper.text()).toContain('轉機 直飛')
    expect(wrapper.text()).toContain('CX')
    expect(wrapper.text()).toContain('JL')
    expect(wrapper.text()).not.toContain('未設定篩選')
  })

  it('shows 未設定篩選 when all filters unset', () => {
    const wrapper = mountDetail()

    expect(wrapper.text()).toContain('未設定篩選')
    expect(wrapper.text()).not.toContain('商務艙')
  })

  it('renders no filter editor form', () => {
    const wrapper = mountDetail()

    expect(wrapper.findAll('form')).toHaveLength(0)
    expect(wrapper.findAll('select')).toHaveLength(0)
    expect(wrapper.find('input[placeholder="搜尋航空公司名稱或代碼"]').exists()).toBe(false)
  })

  it('asks for confirmation in a modal before deleting', async () => {
    const wrapper = mountDetail({ isActive: true })
    // trash button only opens the modal — no fetch yet
    vi.mocked(fetch).mockClear()
    await wrapper.find('button[title="刪除此追蹤"]').trigger('click')
    expect(wrapper.text()).toContain('此操作無法復原')
    expect(fetch).not.toHaveBeenCalled()

    // confirm button inside the modal triggers the DELETE + visit
    const confirmBtn = wrapper
      .findAll('button')
      .find((b) => b.text().trim() === '刪除')
    await confirmBtn?.trigger('click')
    await flushPromises()

    expect(fetch).toHaveBeenCalledWith(
      '/api/itineraries/it-1',
      expect.objectContaining({ method: 'DELETE' }),
    )
    expect(vi.mocked(router.visit)).toHaveBeenCalled()
  })
})
