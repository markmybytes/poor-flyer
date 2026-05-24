import { vi } from 'vitest'

vi.mock('@inertiajs/vue3', () => ({
  Link: { template: '<a><slot /></a>' },
  router: {
    visit: vi.fn(),
    reload: vi.fn(),
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
  usePage: vi.fn(() => ({ props: {} })),
}))

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
  VueDatePicker: { template: '<input />' },
}))

vi.mock('@iconify/vue', () => ({
  Icon: { template: '<span />' },
}))

Object.defineProperty(global, 'fetch', {
  writable: true,
  value: vi.fn(),
})
