import SettingsIndexPage from '@/Pages/Settings/Index.vue'
import { flushPromises, mount } from '@vue/test-utils'
import { router, usePage } from '@inertiajs/vue3'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const defaultProps = {
  settings: {
    currency: { baseCurrency: 'HKD', fxratesApiKey: '', cacheTtl: 86400 },
    email: { recipients: '' },
    itinerary: { disableDeparturedItineraries: true },
    search: {},
    smtp: {
      host: '',
      port: 587,
      user: '',
      senderEmail: '',
      requireAuth: true,
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
    vi.clearAllMocks()
    vi.mocked(usePage).mockReturnValue({ props: {} } as never)
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: async () => ({ message: 'ok', data: {} }),
    } as Response)
  })

  function lastSaveOptions() {
    return vi.mocked(router.post).mock.calls.at(-1)?.[2] as {
      onSuccess?: () => void
      onError?: (errors: Record<string, string>) => void
    }
  }

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

  it('refreshes fx rates through the API, then reloads the page props', async () => {
    const wrapper = mount(SettingsIndexPage, {
      props: defaultProps,
      global: { stubs: globalStubs },
    })
    const refreshBtn = wrapper.findAll('button').find((b) => b.text().includes('更新匯率'))!

    await refreshBtn.trigger('click')
    await flushPromises()

    expect(fetch).toHaveBeenCalledWith(
      '/api/settings/fx-rates/refresh',
      expect.objectContaining({ method: 'POST' }),
    )
    expect(router.reload).toHaveBeenCalled()
    // the reloaded props are the feedback: same shape as the Detail scrape, no local success toast
    const { useToast } = await import('vue-toast-notification')
    expect(vi.mocked(useToast)().success).not.toHaveBeenCalled()
  })

  it('toasts and skips the reload when the refresh request fails', async () => {
    vi.mocked(fetch).mockResolvedValue({ ok: false } as Response)
    const wrapper = mount(SettingsIndexPage, {
      props: defaultProps,
      global: { stubs: globalStubs },
    })
    const refreshBtn = wrapper.findAll('button').find((b) => b.text().includes('更新匯率'))!

    await refreshBtn.trigger('click')
    await flushPromises()

    expect(router.reload).not.toHaveBeenCalled()
    const { useToast } = await import('vue-toast-notification')
    expect(vi.mocked(useToast)().error).toHaveBeenCalledWith('更新匯率失敗，請稍後再試')
  })

  it('posts to /settings through the Inertia router on save', async () => {
    const wrapper = mount(SettingsIndexPage, {
      props: defaultProps,
      global: { stubs: globalStubs },
    })
    await wrapper.findAll('form')[0].trigger('submit')
    await flushPromises()
    expect(router.post).toHaveBeenCalledWith(
      '/settings',
      expect.objectContaining({ itinerary: expect.any(Object) }),
      expect.any(Object),
    )
  })

  it('submits snake_case payloads even though the draft is camelCase', async () => {
    const wrapper = mount(SettingsIndexPage, {
      props: defaultProps,
      global: { stubs: globalStubs },
    })

    await wrapper.findAll('form')[1].trigger('submit')
    await flushPromises()
    expect(vi.mocked(router.post).mock.calls.at(-1)?.[1]).toEqual({
      currency: { base_currency: 'HKD', fxrates_api_key: '', cache_ttl: 86400 },
    })

    await wrapper.findAll('form')[2].trigger('submit')
    await flushPromises()
    expect(vi.mocked(router.post).mock.calls.at(-1)?.[1]).toEqual({
      smtp: {
        host: '',
        port: 587,
        user: '',
        sender_email: '',
        require_auth: true,
        protocol: 'STARTTLS',
      },
    })
  })

  it('leaves the success toast to the server flash router', async () => {
    const wrapper = mount(SettingsIndexPage, {
      props: defaultProps,
      global: { stubs: globalStubs },
    })
    await wrapper.findAll('form')[0].trigger('submit')
    await flushPromises()
    lastSaveOptions().onSuccess?.()
    const { useToast } = await import('vue-toast-notification')
    expect(vi.mocked(useToast)().success).not.toHaveBeenCalled()
  })

  it('toasts the error bag copy when save fails', async () => {
    vi.mocked(usePage).mockReturnValue({
      props: { errors: { settings: 'Unsupported base currency' } },
    } as never)
    const wrapper = mount(SettingsIndexPage, {
      props: defaultProps,
      global: { stubs: globalStubs },
    })
    await wrapper.findAll('form')[0].trigger('submit')
    await flushPromises()
    lastSaveOptions().onError?.({})
    const { useToast } = await import('vue-toast-notification')
    expect(vi.mocked(useToast)().error).toHaveBeenCalledWith('Unsupported base currency')
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
})
