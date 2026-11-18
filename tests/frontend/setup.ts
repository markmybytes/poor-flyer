import { vi } from 'vitest'

vi.mock('@inertiajs/vue3', async () => {
  const { reactive } = await import('vue')

  const router = {
    visit: vi.fn(),
    reload: vi.fn(),
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  }

  // enough of useForm for page tests: a reactive draft whose post() lands on the mocked router
  function useForm(initial: Record<string, unknown>) {
    let transform = (data: Record<string, unknown>) => data
    const form = reactive({ ...structuredClone(initial) }) as Record<string, unknown> & {
      transform(callback: (data: Record<string, unknown>) => Record<string, unknown>): unknown
      post(url: string, options?: Record<string, unknown>): void
    }

    form.transform = (callback) => {
      transform = callback
      return form
    }
    form.post = (url, options) => {
      const draft = Object.fromEntries(Object.keys(initial).map((key) => [key, form[key]]))
      router.post(url, transform(draft), options)
    }
    return form
  }

  return {
    Link: { template: '<a><slot /></a>' },
    router,
    useForm,
    usePage: vi.fn(() => ({ props: {} })),
  }
})

vi.mock('vue-toast-notification', () => {
  const sharedToast = {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
  }
  return { useToast: vi.fn(() => sharedToast) }
})

vi.mock('chart.js/auto', () => {
  const Chart = vi.fn().mockImplementation(() => ({
    destroy: vi.fn(),
    update: vi.fn(),
    data: { labels: [], datasets: [] },
  }))
  return { default: Chart }
})

vi.mock('@vuepic/vue-datepicker', () => ({
  // stub renders the trigger slot and keeps vnode props readable (Detail.test inspects them)
  VueDatePicker: { template: '<div><slot name="trigger" /><slot /></div>' },
}))

vi.mock('@iconify/vue', () => ({
  Icon: { template: '<span />' },
}))

Object.defineProperty(global, 'fetch', {
  writable: true,
  value: vi.fn(),
})
