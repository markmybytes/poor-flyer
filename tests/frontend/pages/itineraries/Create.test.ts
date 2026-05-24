import CreatePage from '@/Pages/Itineraries/Create.vue'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const globalStubs = {
  AppLayout: { template: '<div><slot /></div>' },
  VueDatePicker: { template: '<input />', props: ['modelValue'] },
}

describe('Itineraries/Create', () => {
  beforeEach(() => {
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, data: 'new-id' }),
    } as Response)
  })

  it('renders without crashing', () => {
    const wrapper = mount(CreatePage, { global: { stubs: globalStubs } })
    expect(wrapper.exists()).toBe(true)
  })

  it('defaults trip type to SINGLE', () => {
    const wrapper = mount(CreatePage, { global: { stubs: globalStubs } })
    const radios = wrapper.findAll('input[type="radio"]')
    const singleRadio = radios.find((r) => r.attributes('value') === 'SINGLE')
    expect((singleRadio?.element as HTMLInputElement).checked).toBe(true)
  })

  it('shows one flight leg for SINGLE by default', () => {
    const wrapper = mount(CreatePage, { global: { stubs: globalStubs } })
    expect(wrapper.findAll('input[placeholder="例如: HKG"]').length).toBeGreaterThanOrEqual(1)
  })

  it('switching to ROUND_TRIP adds second flight leg', async () => {
    const wrapper = mount(CreatePage, { global: { stubs: globalStubs } })
    const roundTripRadio = wrapper.find('input[value="ROUND_TRIP"]')
    await roundTripRadio.setValue(true)
    await roundTripRadio.trigger('change')
    await flushPromises()
    const allInputs = wrapper.findAll('input[type="text"]')
    expect(allInputs.length).toBeGreaterThanOrEqual(2)
  })

  it('submit button is present in the form', () => {
    const wrapper = mount(CreatePage, { global: { stubs: globalStubs } })
    const submitBtn = wrapper.find('button[type="submit"]')
    expect(submitBtn.exists()).toBe(true)
  })

  it('calls fetch with POST to /api/itineraries on submit', async () => {
    const wrapper = mount(CreatePage, { global: { stubs: globalStubs } })
    const form = wrapper.find('form')
    await form.trigger('submit')
    await flushPromises()
    expect(fetch).toHaveBeenCalledWith(
      '/api/itineraries',
      expect.objectContaining({ method: 'POST' }),
    )
  })

  it('shows toast success on successful submission', async () => {
    const wrapper = mount(CreatePage, { global: { stubs: globalStubs } })
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    const { useToast } = await import('vue-toast-notification')
    expect(vi.mocked(useToast)().success).toHaveBeenCalled()
  })

  it('shows toast error when fetch fails', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: false,
      json: async () => ({ success: false, message: 'Server error' }),
    } as Response)

    const wrapper = mount(CreatePage, { global: { stubs: globalStubs } })
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    const { useToast } = await import('vue-toast-notification')
    expect(vi.mocked(useToast)().error).toHaveBeenCalled()
  })
})
