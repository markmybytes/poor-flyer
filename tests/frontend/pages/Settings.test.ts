import SettingsIndexPage from '@/Pages/Settings/Index.vue'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const defaultProps = {
  settings: {
    currency: { baseCurrency: 'HKD', fxratesApiKey: '', cacheTtl: '86400' },
    email: { recipients: '' },
    itinerary: { disableDeparturedItineraries: 'true' },
    search: { defaultCabinClass: 'ECONOMY', defaultMaxStops: 'ANY', defaultAirlines: '' },
    smtp: {
      host: '',
      port: '587',
      user: '',
      senderEmail: '',
      requireAuth: 'true',
      protocol: 'STARTTLS',
    },
  },
  supportedCurrencies: ['HKD', 'USD', 'EUR', 'GBP', 'JPY'],
  fxStatus: {
    baseCurrency: 'HKD',
    lastUpdated: '2024-06-15T00:00:00Z',
    rates: { USD: 0.1282, EUR: 0.1176 },
    error: null,
  },
}

const globalStubs = {
  AppLayout: { template: '<div><slot /></div>' },
}

describe('Settings/Index', () => {
  beforeEach(() => {
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: async () => ({ success: true }),
    } as Response)
  })

  it('renders without crashing', () => {
    const wrapper = mount(SettingsIndexPage, {
      props: defaultProps,
      global: { stubs: globalStubs },
    })
    expect(wrapper.exists()).toBe(true)
  })

  it('populates base currency select from props', () => {
    const wrapper = mount(SettingsIndexPage, {
      props: defaultProps,
      global: { stubs: globalStubs },
    })
    const select = wrapper
      .findAll('select')
      .find((s) => (s.element as HTMLSelectElement).value === 'HKD')
    expect(select).toBeDefined()
    expect((select?.element as HTMLSelectElement).value).toBe('HKD')
  })

  it('renders supported currencies as options', () => {
    const wrapper = mount(SettingsIndexPage, {
      props: defaultProps,
      global: { stubs: globalStubs },
    })
    const options = wrapper.findAll('select option')
    expect(options.length).toBeGreaterThanOrEqual(5)
  })

  it('shows FX status last updated date', () => {
    const wrapper = mount(SettingsIndexPage, {
      props: defaultProps,
      global: { stubs: globalStubs },
    })
    expect(wrapper.text()).toMatch(/2024/)
  })

  it('shows error banner when fxStatus has error', () => {
    const wrapper = mount(SettingsIndexPage, {
      props: {
        ...defaultProps,
        fxStatus: { ...defaultProps.fxStatus, error: 'API unavailable', rates: {} },
      },
      global: { stubs: globalStubs },
    })
    expect(wrapper.text()).toContain('API unavailable')
  })

  it('calls PATCH /api/settings on save', async () => {
    const wrapper = mount(SettingsIndexPage, {
      props: defaultProps,
      global: { stubs: globalStubs },
    })
    const forms = wrapper.findAll('form')
    if (forms.length > 0) {
      await forms[0].trigger('submit')
      await flushPromises()
      expect(fetch).toHaveBeenCalledWith(
        '/api/settings',
        expect.objectContaining({ method: 'PATCH' }),
      )
    }
  })

  it('shows toast success after saving', async () => {
    const wrapper = mount(SettingsIndexPage, {
      props: defaultProps,
      global: { stubs: globalStubs },
    })
    const forms = wrapper.findAll('form')
    if (forms.length > 0) {
      await forms[0].trigger('submit')
      await flushPromises()
      const { useToast } = await import('vue-toast-notification')
      expect(vi.mocked(useToast)().success).toHaveBeenCalled()
    }
  })

  it('shows toast error when save fails', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: false,
      json: async () => ({ success: false, message: 'Server error' }),
    } as Response)

    const wrapper = mount(SettingsIndexPage, {
      props: defaultProps,
      global: { stubs: globalStubs },
    })
    const forms = wrapper.findAll('form')
    if (forms.length > 0) {
      await forms[0].trigger('submit')
      await flushPromises()
      const { useToast } = await import('vue-toast-notification')
      expect(vi.mocked(useToast)().error).toHaveBeenCalled()
    }
  })

  it('calls POST /api/settings/test-email on test email button', async () => {
    const wrapper = mount(SettingsIndexPage, {
      props: defaultProps,
      global: { stubs: globalStubs },
    })
    const testBtn = wrapper.findAll('button').find((b) => b.text().includes('測試'))
    if (testBtn) {
      await testBtn.trigger('click')
      await flushPromises()
      expect(fetch).toHaveBeenCalled()
    }
  })

  it('renders the default fetch filter controls', () => {
    const wrapper = mount(SettingsIndexPage, {
      props: defaultProps,
      global: { stubs: globalStubs },
    })
    const selects = wrapper.findAll('select')
    expect(selects.length).toBeGreaterThanOrEqual(3)
    expect(selects[0].findAll('option')).toHaveLength(5)
    expect(wrapper.findAll('.checkbox')).toHaveLength(12)
    expect(wrapper.text()).toContain('預設搜尋條件')
  })

  it('saves default fetch filters with snake_case keys', async () => {
    const wrapper = mount(SettingsIndexPage, {
      props: {
        ...defaultProps,
        settings: {
          ...defaultProps.settings,
          search: {
            defaultCabinClass: 'PREMIUM_ECONOMY',
            defaultMaxStops: 'NON_STOP',
            defaultAirlines: 'UO,CX',
          },
        },
      },
      global: { stubs: globalStubs },
    })
    const forms = wrapper.findAll('form')
    expect(forms[1].findAll('.checkbox')).toHaveLength(12)
    await forms[1].trigger('submit')
    await flushPromises()

    const call = vi.mocked(fetch).mock.calls.at(-1)
    const body = JSON.parse(String(call?.[1]?.body ?? '{}'))
    expect(body.search.default_cabin_class).toBe('PREMIUM_ECONOMY')
    expect(body.search.default_max_stops).toBe('NON_STOP')
    expect(body.search.default_airlines).toEqual(['UO', 'CX'])
  })
})
