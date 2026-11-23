import CreatePage from '@/Pages/Itineraries/Create.vue'
import { flushPromises, mount } from '@vue/test-utils'
import { router, usePage } from '@inertiajs/vue3'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const globalStubs = {
  AppLayout: { template: '<div><slot /></div>' },
  VueDatePicker: { template: '<input />', props: ['modelValue'] },
}

describe('Itineraries/Create', () => {
  function lastRequestBody() {
    return vi.mocked(router.post).mock.calls.at(-1)?.[1] as Record<string, unknown>
  }

  function lastRequestOptions() {
    return vi.mocked(router.post).mock.calls.at(-1)?.[2] as {
      onSuccess?: () => void
      onError?: (errors: Record<string, string>) => void
    }
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(usePage).mockReturnValue({ props: {} } as never)
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: async () => ({ data: [] }),
    } as Response)
  })

  it('renders without crashing', () => {
    const wrapper = mount(CreatePage, {
      props: { airlines: [{ code: 'CX', name: 'Cathay Pacific' }] },
      global: { stubs: globalStubs },
    })
    expect(wrapper.exists()).toBe(true)
  })

  it('defaults trip type to SINGLE', () => {
    const wrapper = mount(CreatePage, {
      props: { airlines: [{ code: 'CX', name: 'Cathay Pacific' }] },
      global: { stubs: globalStubs },
    })
    const radios = wrapper.findAll('input[type="radio"]')
    const singleRadio = radios.find((r) => r.attributes('value') === 'SINGLE')
    expect((singleRadio?.element as HTMLInputElement).checked).toBe(true)
  })

  it('shows one flight leg for SINGLE by default', () => {
    const wrapper = mount(CreatePage, {
      props: { airlines: [{ code: 'CX', name: 'Cathay Pacific' }] },
      global: { stubs: globalStubs },
    })
    expect(wrapper.findAll('input[placeholder="例如: HKG"]').length).toBeGreaterThanOrEqual(1)
  })

  it('switching to ROUND_TRIP adds second flight leg', async () => {
    const wrapper = mount(CreatePage, {
      props: { airlines: [{ code: 'CX', name: 'Cathay Pacific' }] },
      global: { stubs: globalStubs },
    })
    const roundTripRadio = wrapper.find('input[value="ROUND_TRIP"]')
    await roundTripRadio.setValue(true)
    await roundTripRadio.trigger('change')
    await flushPromises()
    const allInputs = wrapper.findAll('input[type="text"]')
    expect(allInputs.length).toBeGreaterThanOrEqual(2)
  })

  it('submit button is present in the form', () => {
    const wrapper = mount(CreatePage, {
      props: { airlines: [{ code: 'CX', name: 'Cathay Pacific' }] },
      global: { stubs: globalStubs },
    })
    const submitBtn = wrapper.find('button[type="submit"]')
    expect(submitBtn.exists()).toBe(true)
  })

  it('posts to /itineraries through the Inertia router on submit', async () => {
    const wrapper = mount(CreatePage, {
      props: { airlines: [{ code: 'CX', name: 'Cathay Pacific' }] },
      global: { stubs: globalStubs },
    })
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(router.post).toHaveBeenCalledWith(
      '/itineraries',
      expect.objectContaining({ trip_type: 'SINGLE' }),
      expect.any(Object),
    )
  })

  it('leaves the success toast to the server flash router', async () => {
    const wrapper = mount(CreatePage, {
      props: { airlines: [{ code: 'CX', name: 'Cathay Pacific' }] },
      global: { stubs: globalStubs },
    })
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    lastRequestOptions().onSuccess?.()
    const { useToast } = await import('vue-toast-notification')
    expect(vi.mocked(useToast)().success).not.toHaveBeenCalled()
  })

  it('shows toast error with the Inertia error bag message', async () => {
    const wrapper = mount(CreatePage, {
      props: { airlines: [{ code: 'CX', name: 'Cathay Pacific' }] },
      global: { stubs: globalStubs },
    })
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    lastRequestOptions().onError?.({ itinerary: '請檢查輸入內容' })
    const { useToast } = await import('vue-toast-notification')
    expect(vi.mocked(useToast)().error).toHaveBeenCalledWith('請檢查輸入內容')
  })

  it('renders the fetch filter controls', () => {
    const wrapper = mount(CreatePage, {
      props: { airlines: [{ code: 'CX', name: 'Cathay Pacific' }] },
      global: { stubs: globalStubs },
    })
    const selects = wrapper.findAll('select')
    expect(selects).toHaveLength(2)
    expect(selects[0].findAll('option')).toHaveLength(5)
    expect(selects[1].findAll('option')).toHaveLength(5)
    expect(wrapper.find('input[placeholder="搜尋航空公司名稱或代碼"]').exists()).toBe(true)
  })

  it('sends snake_case filter keys and omits untouched airlines', async () => {
    const wrapper = mount(CreatePage, {
      props: { airlines: [{ code: 'CX', name: 'Cathay Pacific' }] },
      global: { stubs: globalStubs },
    })
    const selects = wrapper.findAll('select')
    await selects[0].setValue('BUSINESS')
    await selects[1].setValue('NON_STOP')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    const body = lastRequestBody()
    expect(body.cabin_class).toBe('BUSINESS')
    expect(body.max_stops).toBe('NON_STOP')
    expect(body).not.toHaveProperty('airlines')
  })

  it('sends airlines as an include list', async () => {
    const wrapper = mount(CreatePage, {
      props: { airlines: [{ code: 'CX', name: 'Cathay Pacific' }] },
      global: { stubs: globalStubs },
    })
    const input = wrapper.find('input[placeholder="搜尋航空公司名稱或代碼"]')
    await input.setValue('uo')
    await input.trigger('keydown.enter')
    await input.setValue('vn')
    await input.trigger('keydown.enter')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(lastRequestBody().airlines).toEqual(['UO', 'VN'])
  })

  it('sends an empty airline array when a selected carrier is cleared', async () => {
    const wrapper = mount(CreatePage, {
      props: { airlines: [{ code: 'CX', name: 'Cathay Pacific' }] },
      global: { stubs: globalStubs },
    })
    const input = wrapper.find('input[placeholder="搜尋航空公司名稱或代碼"]')
    await input.setValue('UO')
    await input.trigger('keydown.enter')
    await wrapper.find('button[aria-label="移除 UO"]').trigger('click')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(lastRequestBody().airlines).toEqual([])
  })

  function notifyToggle(wrapper: ReturnType<typeof mount>) {
    const label = wrapper.findAll('label').find((l) => l.text().includes('逐航段通知'))
    return label!.find('input[type="checkbox"]')
  }

  it('renders the per-leg notification checkbox, off by default', () => {
    const wrapper = mount(CreatePage, {
      props: { airlines: [{ code: 'CX', name: 'Cathay Pacific' }] },
      global: { stubs: globalStubs },
    })
    const toggle = notifyToggle(wrapper)
    expect(toggle.exists()).toBe(true)
    expect((toggle.element as HTMLInputElement).checked).toBe(false)
  })

  it('sends notify_per_leg as false by default', async () => {
    const wrapper = mount(CreatePage, {
      props: { airlines: [{ code: 'CX', name: 'Cathay Pacific' }] },
      global: { stubs: globalStubs },
    })
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(lastRequestBody().notify_per_leg).toBe(false)
  })

  it('sends notify_per_leg as true once the checkbox is toggled', async () => {
    const wrapper = mount(CreatePage, {
      props: { airlines: [{ code: 'CX', name: 'Cathay Pacific' }] },
      global: { stubs: globalStubs },
    })
    await notifyToggle(wrapper).setValue(true)
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(lastRequestBody().notify_per_leg).toBe(true)
  })

  it.each([
    ['tripType', '請選擇旅程類型'],
    ['flights.0.origin', '出發地機場代碼無效'],
    ['flights.0.destination', '目的地機場代碼無效'],
    ['flights.0.flightDate', '出發日期無效'],
  ])('renders the server message for %s inline and only once', (key, message) => {
    vi.mocked(usePage).mockReturnValue({
      props: { errors: { [key]: message } },
    } as never)
    const wrapper = mount(CreatePage, {
      props: { airlines: [{ code: 'CX', name: 'Cathay Pacific' }] },
      global: { stubs: globalStubs },
    })
    expect(wrapper.text()).toContain(message)
    // unrelated fields share the same errors bag: exactly one field renders the message
    expect(wrapper.text().split(message).length - 1).toBe(1)
  })
})
