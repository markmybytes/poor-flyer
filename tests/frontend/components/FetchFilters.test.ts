import FetchFilters from '@/Components/FetchFilters.vue'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { reactive } from 'vue'

const AIRLINES = [
  { code: 'CX', name: 'Cathay Pacific' },
  { code: '7C', name: 'Jeju Air' },
  { code: 'UO', name: 'Hong Kong Express' },
  { code: 'GK', name: 'Jetstar Japan' },
]

function mountFilters(airlines: string[] | null = null) {
  const value = reactive({
    cabinClass: '',
    maxStops: '',
    airlines,
  })
  const wrapper = mount(FetchFilters, { props: { modelValue: value } })
  return { wrapper, value }
}

function airlineInput(wrapper: ReturnType<typeof mountFilters>['wrapper']) {
  return wrapper.find('input[placeholder="搜尋航空公司名稱或代碼"]')
}

describe('Components/FetchFilters', () => {
  beforeEach(() => {
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: async () => ({ message: null, data: AIRLINES }),
    } as Response)
  })

  it('renders cabin and stops option lists', () => {
    const { wrapper } = mountFilters()
    const selects = wrapper.findAll('select')
    expect(selects).toHaveLength(2)
    expect(selects[0].findAll('option')).toHaveLength(5)
    expect(selects[1].findAll('option')).toHaveLength(5)
    expect(selects[0].text()).toContain('經濟艙')
    expect(selects[1].text()).toContain('直飛')
  })

  it('loads airline options on mount without dumping the catalog', async () => {
    const { wrapper } = mountFilters()
    await flushPromises()

    expect(fetch).toHaveBeenCalledWith('/api/airlines')
    await airlineInput(wrapper).trigger('focus')
    expect(wrapper.findAll('.airline-suggestion')).toHaveLength(0)
  })

  it('filters suggestions by code or name on input', async () => {
    const { wrapper } = mountFilters()
    await flushPromises()

    await airlineInput(wrapper).setValue('je')

    const labels = wrapper.findAll('.airline-suggestion').map((row) => row.text())
    expect(labels).toContain('GK · Jetstar Japan')
    expect(labels).toContain('7C · Jeju Air')
    expect(labels).not.toContain('CX · Cathay Pacific')
  })

  it('caps suggestions at 20 rows', async () => {
    const many = Array.from({ length: 25 }, (_, index) => ({
      code: `Z${index}`,
      name: `Airline ${index}`,
    }))
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: async () => ({ message: null, data: many }),
    } as Response)

    const { wrapper } = mountFilters()
    await flushPromises()
    await airlineInput(wrapper).setValue('air')

    expect(wrapper.findAll('.airline-suggestion')).toHaveLength(20)
  })

  it('adds a chip when a suggestion row is clicked', async () => {
    const { wrapper, value } = mountFilters()
    await flushPromises()

    const input = airlineInput(wrapper)
    await input.setValue('je')
    await wrapper
      .findAll('.airline-suggestion')
      .find((row) => row.text().includes('Jetstar Japan'))
      ?.trigger('mousedown')

    expect(value.airlines).toEqual(['GK'])
    expect(wrapper.text()).toContain('GK · Jetstar Japan')
    expect((input.element as HTMLInputElement).value).toBe('')
  })

  it('adds a valid IATA code uppercased and renders a chip', async () => {
    const { wrapper, value } = mountFilters()
    await flushPromises()

    const input = airlineInput(wrapper)
    await input.setValue('cx')
    await input.trigger('keydown.enter')

    expect(value.airlines).toEqual(['CX'])
    expect(wrapper.text()).toContain('CX · Cathay Pacific')
  })

  it('adds by airline name', async () => {
    const { wrapper, value } = mountFilters()
    await flushPromises()

    const input = airlineInput(wrapper)
    await input.setValue('Jeju Air')
    await input.trigger('keydown.enter')

    expect(value.airlines).toEqual(['7C'])
  })

  it('ignores invalid input', async () => {
    const { wrapper, value } = mountFilters()
    await flushPromises()

    const input = airlineInput(wrapper)
    await input.setValue('TOOLONG')
    await input.trigger('keydown.enter')
    expect(value.airlines).toBeNull()

    await input.setValue('1')
    await input.trigger('keydown.enter')
    expect(value.airlines).toBeNull()
  })

  it('deduplicates an already selected airline', async () => {
    const { wrapper, value } = mountFilters()
    await flushPromises()

    const input = airlineInput(wrapper)
    await input.setValue('CX')
    await input.trigger('keydown.enter')
    await input.setValue('cx')
    await input.trigger('keydown.enter')

    expect(value.airlines).toEqual(['CX'])
  })

  it('hides suggestions on Escape', async () => {
    const { wrapper } = mountFilters()
    await flushPromises()

    const input = airlineInput(wrapper)
    await input.setValue('je')
    expect(wrapper.findAll('.airline-suggestion').length).toBeGreaterThan(0)

    await input.trigger('keydown.esc')
    expect(wrapper.findAll('.airline-suggestion')).toHaveLength(0)
  })

  it('removes a chip with its × button', async () => {
    const { wrapper, value } = mountFilters(['CX', 'UO'])
    await flushPromises()

    await wrapper.find('button[aria-label="移除 CX"]').trigger('click')

    expect(value.airlines).toEqual(['UO'])
    expect(wrapper.findAll('.airline-chip')).toHaveLength(1)
    expect(wrapper.find('.airline-chip').text()).toContain('UO · Hong Kong Express')
  })
})
