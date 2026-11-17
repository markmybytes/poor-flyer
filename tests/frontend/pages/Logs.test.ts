import LogsIndexPage from '@/Pages/Logs/Index.vue'
import { router, usePage } from '@inertiajs/vue3'
import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useToast } from 'vue-toast-notification'

const toast = useToast()

const defaultProps = {
  logs: [],
  pagination: { total: 0, page: 1, perPage: 50 },
  filters: {
    levels: ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
    startDate: '',
    endDate: '',
  },
}

const globalStubs = {
  AppLayout: { template: '<div><slot /></div>' },
  VueDatePicker: { template: '<input />', props: ['modelValue'] },
}

describe('Logs/Index', () => {
  beforeEach(() => {
    vi.mocked(router.delete).mockClear()
    vi.mocked(toast.success).mockClear()
    vi.mocked(usePage).mockReturnValue({ props: {} } as never)
  })

  it('renders without crashing with empty logs', () => {
    const wrapper = mount(LogsIndexPage, {
      props: defaultProps,
      global: { stubs: globalStubs },
    })
    expect(wrapper.exists()).toBe(true)
  })

  it('renders a row for each log entry', () => {
    const wrapper = mount(LogsIndexPage, {
      props: {
        ...defaultProps,
        logs: [
          {
            timestamp: '2024-06-15 10:00:00,000',
            level: 'INFO',
            logger: 'src.routes',
            message: 'Request received',
            traceback: null,
            correlation: null,
          },
          {
            timestamp: '2024-06-15 10:01:00,000',
            level: 'ERROR',
            logger: 'src.services',
            message: 'Something failed',
            traceback: null,
            correlation: null,
          },
        ],
        pagination: { total: 2, page: 1, perPage: 50 },
      },
      global: { stubs: globalStubs },
    })
    expect(wrapper.findAll('tbody tr').length).toBe(2)
  })

  it('displays log level badge for each entry', () => {
    const wrapper = mount(LogsIndexPage, {
      props: {
        ...defaultProps,
        logs: [
          {
            timestamp: '2024-06-15 10:00:00,000',
            level: 'ERROR',
            logger: 'src',
            message: 'err',
            traceback: null,
            correlation: null,
          },
        ],
        pagination: { total: 1, page: 1, perPage: 50 },
      },
      global: { stubs: globalStubs },
    })
    expect(wrapper.text()).toContain('ERROR')
  })

  it('shows confirm modal trigger button', () => {
    const wrapper = mount(LogsIndexPage, {
      props: defaultProps,
      global: { stubs: globalStubs },
    })
    expect(wrapper.text()).toContain('清理紀錄')
  })

  it('clears logs through the page route, never the JSON API', async () => {
    const wrapper = mount(LogsIndexPage, {
      props: defaultProps,
      global: { stubs: globalStubs },
    })
    const modal = wrapper.find('dialog').element as HTMLDialogElement
    modal.close = vi.fn()
    const confirmButton = wrapper.findAll('button').find((b) => b.text().trim() === '確認清除')!

    await confirmButton.trigger('click')

    expect(router.delete).toHaveBeenCalledWith(
      '/logs',
      expect.objectContaining({
        onSuccess: expect.any(Function),
        onError: expect.any(Function),
        onFinish: expect.any(Function),
      }),
    )
    expect(fetch).not.toHaveBeenCalled()
    expect(confirmButton.attributes('disabled')).toBeDefined()

    const options = vi.mocked(router.delete).mock.calls[0][1]
    options.onSuccess?.({} as never)
    expect(modal.close).toHaveBeenCalled()
    // success copy comes from the server flash router, not this page
    expect(toast.success).not.toHaveBeenCalled()

    options.onFinish?.({} as never)
    await wrapper.vm.$nextTick()
    expect(confirmButton.attributes('disabled')).toBeUndefined()
  })

  it('toasts the failure copy when the server rejects the clear', async () => {
    vi.mocked(usePage).mockReturnValue({ props: { errors: { logs: '清除紀錄失敗' } } } as never)
    const wrapper = mount(LogsIndexPage, {
      props: defaultProps,
      global: { stubs: globalStubs },
    })

    const confirmButton = wrapper.findAll('button').find((b) => b.text().trim() === '確認清除')!
    await confirmButton.trigger('click')
    vi.mocked(router.delete).mock.calls[0][1].onError?.({} as never)

    expect(fetch).not.toHaveBeenCalled()
    expect(toast.error).toHaveBeenCalledWith('清除失敗，請稍後再試')
  })

  it('shows pagination total', () => {
    const wrapper = mount(LogsIndexPage, {
      props: {
        ...defaultProps,
        pagination: { total: 142, page: 1, perPage: 50 },
      },
      global: { stubs: globalStubs },
    })
    expect(wrapper.text()).toContain('142')
  })

  it('renders correlation chip only when present', () => {
    const base = {
      timestamp: '2024-06-15 10:00:00,000',
      level: 'INFO',
      logger: 'src.routes',
      traceback: null,
    }
    const wrapper = mount(LogsIndexPage, {
      props: {
        ...defaultProps,
        logs: [
          { ...base, message: 'with cid', correlation: '1a2b3c4d' },
          { ...base, message: 'without cid', correlation: null },
        ],
        pagination: { total: 2, page: 1, perPage: 50 },
      },
      global: { stubs: globalStubs },
    })
    expect(wrapper.findAll('span.badge.font-mono').length).toBe(1)
    expect(wrapper.text()).toContain('1a2b3c4d')
  })

  it('expands traceback row on click', async () => {
    const wrapper = mount(LogsIndexPage, {
      props: {
        ...defaultProps,
        logs: [
          {
            timestamp: '2024-06-15 10:00:00,000',
            level: 'ERROR',
            logger: 'src',
            message: 'err',
            traceback: 'Traceback (most recent call last):\n  ...',
            correlation: null,
          },
        ],
        pagination: { total: 1, page: 1, perPage: 50 },
      },
      global: { stubs: globalStubs },
    })
    const row = wrapper.find('tbody tr')
    await row.trigger('click')
    expect(wrapper.text()).toContain('Traceback')
  })
})
