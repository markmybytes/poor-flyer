import DeadlineDatePicker from '@/Components/DeadlineDatePicker.vue'
import { mount } from '@vue/test-utils'
import { VueDatePicker } from '@vuepic/vue-datepicker'
import { describe, expect, it } from 'vitest'

function mountPicker(props: Record<string, unknown> = {}) {
  return mount(DeadlineDatePicker, { props: { modelValue: '', ...props } })
}

function dpProps(wrapper: ReturnType<typeof mountPicker>) {
  return wrapper.findComponent(VueDatePicker).vm.$.vnode.props as Record<string, unknown> | null
}

describe('DeadlineDatePicker', () => {
  it('bounds a future departure and dots it in blue', () => {
    const wrapper = mountPicker({ departure: '2030-01-01' })
    const props = dpProps(wrapper)

    expect(props?.maxDate).toBe('2030-01-01')
    expect(props?.minDate).toBe(new Date().toLocaleDateString('en-CA'))
    expect(props?.startDate).toBe('2030-01-01')
    expect(props?.markers).toEqual([{ date: '2030-01-01', type: 'dot', color: '#007af0' }])
    expect(props?.presetDates).toHaveLength(5)
  })

  it('drops the upper bound for a departed trip but still dots the date', () => {
    const wrapper = mountPicker({ departure: '2020-01-01' })
    const props = dpProps(wrapper)

    expect(props?.maxDate).toBeUndefined()
    expect(props?.startDate).toBe(new Date().toLocaleDateString('en-CA'))
    expect(props?.markers).toEqual([{ date: '2020-01-01', type: 'dot', color: '#007af0' }])
  })

  it('renders no markers or presets without a departure', () => {
    const props = dpProps(mountPicker())

    expect(props?.maxDate).toBeUndefined()
    expect(props?.markers).toBeUndefined()
    expect(props?.presetDates).toEqual([])
  })

  it('passes a markers override through instead of the default dot', () => {
    const override = [{ date: '2030-02-02', type: 'dot', color: '#10b981' }]
    const props = dpProps(mountPicker({ departure: '2030-01-01', markers: override }))

    expect(props?.markers).toEqual(override)
  })

  it('forwards disabled to the trigger input', () => {
    const wrapper = mountPicker({ departure: '2030-01-01', disabled: true })

    expect(wrapper.find('input').attributes('disabled')).toBeDefined()
    expect(wrapper.find('button[aria-label="清除限期"]').attributes('disabled')).toBeDefined()
  })

  it('emits an empty string when the clear affordance is clicked', async () => {
    const wrapper = mountPicker({ modelValue: '2030-01-01', departure: '2030-01-01' })

    await wrapper.find('button[aria-label="清除限期"]').trigger('click')

    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([''])
  })
})
