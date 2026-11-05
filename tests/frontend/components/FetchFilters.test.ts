import FetchFilters from '@/Components/FetchFilters.vue'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { reactive } from 'vue'

function mountFilters() {
  const value = reactive({
    cabinClass: '',
    maxStops: '',
    airlines: null as string[] | null,
  })
  const wrapper = mount(FetchFilters, { props: { modelValue: value } })
  return { wrapper, value }
}

describe('Components/FetchFilters', () => {
  it('renders cabin and stops option lists', () => {
    const { wrapper } = mountFilters()
    const selects = wrapper.findAll('select')
    expect(selects).toHaveLength(2)
    expect(selects[0].findAll('option')).toHaveLength(5)
    expect(selects[1].findAll('option')).toHaveLength(5)
    expect(selects[0].text()).toContain('經濟艙')
    expect(selects[1].text()).toContain('直飛')
  })

  it('renders the common carrier list', () => {
    const { wrapper } = mountFilters()
    expect(wrapper.findAll('.checkbox')).toHaveLength(12)
    expect(wrapper.text()).toContain('UO · 香港快運')
    expect(wrapper.text()).toContain('HX · 香港航空')
  })

  it('adds a valid free-text IATA code uppercased', async () => {
    const { wrapper, value } = mountFilters()
    const input = wrapper.find('input[placeholder="其他 IATA 代碼"]')
    await input.setValue('cx')
    await input.trigger('keydown.enter')
    expect(value.airlines).toEqual(['CX'])
    expect(wrapper.text()).toContain('CX')
  })

  it('ignores invalid free-text codes', async () => {
    const { wrapper, value } = mountFilters()
    const input = wrapper.find('input[placeholder="其他 IATA 代碼"]')
    await input.setValue('TOOLONG')
    await input.trigger('keydown.enter')
    expect(value.airlines).toBeNull()
    await input.setValue('1')
    await input.trigger('keydown.enter')
    expect(value.airlines).toBeNull()
  })

  it('toggles a common carrier checkbox', async () => {
    const { wrapper, value } = mountFilters()
    const checkbox = wrapper.find('input[value="UO"]')
    await checkbox.setValue(true)
    expect(value.airlines).toEqual(['UO'])
    await checkbox.setValue(false)
    expect(value.airlines).toEqual([])
  })
})
