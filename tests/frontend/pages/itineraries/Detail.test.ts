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

function lastRequestBody() {
  const call = vi.mocked(fetch).mock.calls.at(-1)
  return JSON.parse(String(call?.[1]?.body ?? '{}'))
}

describe('Itineraries/Detail filters', () => {
  beforeEach(() => {
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: async () => ({ success: true }),
    } as Response)
  })

  it('opens the inline filter editor', async () => {
    const wrapper = mountDetail()
    expect(wrapper.findAll('select')).toHaveLength(0)
    const toggle = wrapper.findAll('button').find((b) => b.text().includes('修改'))
    await toggle?.trigger('click')
    expect(wrapper.findAll('select')).toHaveLength(2)
    expect(wrapper.text()).toContain('票價搜尋條件')
  })

  it('prefills filters from the itinerary props', async () => {
    const wrapper = mountDetail({ cabinClass: 'BUSINESS', maxStops: 'NON_STOP' })
    await wrapper
      .findAll('button')
      .find((b) => b.text().includes('修改'))
      ?.trigger('click')
    const selects = wrapper.findAll('select')
    expect((selects[0].element as HTMLSelectElement).value).toBe('BUSINESS')
    expect((selects[1].element as HTMLSelectElement).value).toBe('NON_STOP')
  })

  it('PATCHes snake_case keys and omits untouched airlines', async () => {
    const wrapper = mountDetail()
    await wrapper
      .findAll('button')
      .find((b) => b.text().includes('修改'))
      ?.trigger('click')
    const selects = wrapper.findAll('select')
    await selects[0].setValue('FIRST')
    await selects[1].setValue('ONE_STOP')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(fetch).toHaveBeenCalledWith(
      '/api/itineraries/it-1',
      expect.objectContaining({ method: 'PATCH' }),
    )
    const body = lastRequestBody()
    expect(body.cabin_class).toBe('FIRST')
    expect(body.max_stops).toBe('ONE_STOP')
    expect(body).not.toHaveProperty('airlines')
    expect(vi.mocked(router.reload)).toHaveBeenCalled()
  })

  it('sends an airline include list', async () => {
    const wrapper = mountDetail()
    await wrapper
      .findAll('button')
      .find((b) => b.text().includes('修改'))
      ?.trigger('click')
    await wrapper.find('input[value="UO"]').setValue(true)
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(lastRequestBody().airlines).toEqual(['UO'])
  })

  it('sends an empty array when the airline filter is cleared', async () => {
    const wrapper = mountDetail({ airlines: ['CX'] })
    await wrapper
      .findAll('button')
      .find((b) => b.text().includes('修改'))
      ?.trigger('click')
    await wrapper.find('input[value="CX"]').setValue(false)
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(lastRequestBody().airlines).toEqual([])
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
