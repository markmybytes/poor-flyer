import FieldError from '@/Components/FieldError.vue'
import { mount } from '@vue/test-utils'
import { usePage } from '@inertiajs/vue3'
import { beforeEach, describe, expect, it, vi } from 'vitest'

describe('FieldError', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(usePage).mockReturnValue({ props: {} } as never)
  })

  it('renders nothing when the field has no error', () => {
    const wrapper = mount(FieldError, { props: { field: 'origin' } })
    expect(wrapper.find('p').exists()).toBe(false)
  })

  it('renders the server message for its field', () => {
    vi.mocked(usePage).mockReturnValue({
      props: { errors: { origin: '出發地機場代碼無效' } },
    } as never)
    const wrapper = mount(FieldError, { props: { field: 'origin' } })
    expect(wrapper.text()).toBe('出發地機場代碼無效')
    expect(wrapper.find('p').classes()).toContain('text-error')
  })

  it('shows nothing when the errors bag carries only unrelated fields', () => {
    vi.mocked(usePage).mockReturnValue({
      props: { errors: { destination: '目的地機場代碼無效' } },
    } as never)
    const wrapper = mount(FieldError, { props: { field: 'origin' } })
    expect(wrapper.find('p').exists()).toBe(false)
  })

  it('takes the first message when the value is an array', () => {
    vi.mocked(usePage).mockReturnValue({
      props: { errors: { deadline: ['第一條訊息', '第二條訊息'] } },
    } as never)
    const wrapper = mount(FieldError, { props: { field: 'deadline' } })
    expect(wrapper.text()).toBe('第一條訊息')
  })
})
