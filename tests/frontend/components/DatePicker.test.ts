import DatePicker from '@/Components/DatePicker.vue'
import { mount } from '@vue/test-utils'
import { VueDatePicker } from '@vuepic/vue-datepicker'
import { describe, expect, it } from 'vitest'

function mountPicker(props: Record<string, unknown> = {}) {
  return mount(DatePicker, { props: { modelValue: '', ...props } })
}

function dpProps(wrapper: ReturnType<typeof mountPicker>) {
  return wrapper.findComponent(VueDatePicker).vm.$.vnode.props as Record<string, unknown> | null
}

describe('DatePicker', () => {
  it('shows the string model value in a readonly trigger input', () => {
    const wrapper = mountPicker({ modelValue: '2026-12-01' })
    const input = wrapper.find('input')

    expect(input.attributes('readonly')).toBeDefined()
    expect((input.element as HTMLInputElement).value).toBe('2026-12-01')
    expect(input.attributes('placeholder')).toBe('選擇日期')
  })

  it('shows a two-date range as start 至 end', () => {
    const wrapper = mountPicker({ modelValue: ['2026-12-01', '2026-12-09'] })

    expect((wrapper.find('input').element as HTMLInputElement).value).toBe(
      '2026-12-01 至 2026-12-09',
    )
  })

  it('spreads caller options over the defaults', () => {
    const wrapper = mountPicker({ options: { enableTimePicker: true, range: true } })
    const props = dpProps(wrapper)

    expect(props?.enableTimePicker).toBe(true)
    expect(props?.range).toBe(true)
    expect(props?.autoApply).toBe(true)
    expect(props?.modelType).toBe('yyyy-MM-dd')
  })

  it('hides the clear button when clearable is false', () => {
    const wrapper = mountPicker({ modelValue: '2026-12-01', clearable: false })

    expect(wrapper.find('button').exists()).toBe(false)
  })

  it('disables the clear button while the value is empty', () => {
    const wrapper = mountPicker()

    expect(wrapper.find('button[aria-label="清除"]').attributes('disabled')).toBeDefined()
  })

  it('clears a string model to an empty string', async () => {
    const wrapper = mountPicker({ modelValue: '2026-12-01', clearLabel: '清除限期' })

    await wrapper.find('button[aria-label="清除限期"]').trigger('click')

    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([''])
  })

  it('clears an array model to an empty array', async () => {
    const wrapper = mountPicker({ modelValue: ['2026-12-01', '2026-12-09'] })

    await wrapper.find('button').trigger('click')

    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([[]])
  })

  it('passes required and disabled attrs to the input, disabling clearing', () => {
    const wrapper = mountPicker({ modelValue: '2026-12-01', required: true, disabled: true })
    const input = wrapper.find('input')

    expect(input.attributes('required')).toBeDefined()
    expect(input.attributes('disabled')).toBeDefined()
    expect(wrapper.find('button').attributes('disabled')).toBeDefined()
  })
})
