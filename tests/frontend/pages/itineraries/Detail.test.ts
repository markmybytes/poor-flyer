import DetailPage from '@/Pages/Itineraries/Detail.vue'
import { flushPromises, mount } from '@vue/test-utils'
import { router } from '@inertiajs/vue3'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useToast } from 'vue-toast-notification'
import { VueDatePicker } from '@vuepic/vue-datepicker'

const itinerary = {
  id: 'it-1',
  tripType: 'SINGLE',
  isActive: true,
  deadline: null,
  createdAt: '2026-01-01T00:00:00Z',
  flights: [{ id: 'f1', sequence: 0, origin: 'HKG', destination: 'NRT', flightDate: '2026-12-01' }],
}

const globalStubs = {
  AppLayout: { template: '<div><slot /></div>' },
  FareGraph: { template: '<div />' },
  FareList: { template: '<div />' },
}

function mountDetail(overrides: Record<string, unknown> = {}) {
  return mount(DetailPage, {
    props: {
      itinerary: { ...itinerary, ...overrides },
      baseCurrency: 'HKD',
    },
    global: { stubs: globalStubs },
  })
}

describe('Itineraries/Detail filters', () => {
  beforeEach(() => {
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: async () => ({ message: null, data: null }),
    } as Response)
  })

  it('renders read-only filter values from props', () => {
    const wrapper = mountDetail({
      cabinClass: 'BUSINESS',
      maxStops: 'NON_STOP',
      airlines: ['CX', 'JL'],
    })

    expect(wrapper.find('[data-tip="修改搜尋條件請刪除後重新建立"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('商務艙')
    expect(wrapper.text()).toContain('轉機 直飛')
    expect(wrapper.text()).toContain('CX')
    expect(wrapper.text()).toContain('JL')
    expect(wrapper.text()).not.toContain('未設定篩選')
  })

  it('shows 未設定篩選 when all filters unset', () => {
    const wrapper = mountDetail()

    expect(wrapper.text()).toContain('未設定篩選')
    expect(wrapper.text()).not.toContain('商務艙')
  })

  it('renders no filter editor form', () => {
    const wrapper = mountDetail()

    expect(wrapper.findAll('form')).toHaveLength(0)
    expect(wrapper.findAll('select')).toHaveLength(0)
    expect(wrapper.find('input[placeholder="搜尋航空公司名稱或代碼"]').exists()).toBe(false)
  })

  it('asks for confirmation in a modal before deleting', async () => {
    const wrapper = mountDetail({ isActive: true })
    // trash button only opens the modal — no fetch yet
    vi.mocked(fetch).mockClear()
    await wrapper.find('button[title="刪除此追蹤"]').trigger('click')
    expect(wrapper.text()).toContain('此操作無法復原')
    expect(fetch).not.toHaveBeenCalled()

    // confirm button inside the modal triggers the DELETE + visit
    const confirmBtn = wrapper.findAll('button').find((b) => b.text().trim() === '刪除')
    await confirmBtn?.trigger('click')
    await flushPromises()

    expect(fetch).toHaveBeenCalledWith(
      '/api/itineraries/it-1',
      expect.objectContaining({ method: 'DELETE' }),
    )
    expect(vi.mocked(router.visit)).toHaveBeenCalled()
  })
})

describe('Itineraries/Detail per-leg notifications', () => {
  beforeEach(() => {
    vi.mocked(fetch).mockResolvedValue({ ok: true, json: async () => ({}) } as Response)
  })

  it('shows the flag as 已開啟 when enabled', () => {
    const wrapper = mountDetail({ notifyPerLeg: true })

    expect(wrapper.text()).toContain('逐航段通知')
    expect(wrapper.text()).toContain('已開啟')
  })

  it('shows the flag as 未開啟 when disabled', () => {
    const wrapper = mountDetail({ notifyPerLeg: false })

    expect(wrapper.text()).toContain('逐航段通知')
    expect(wrapper.text()).toContain('未開啟')
    expect(wrapper.text()).not.toContain('已開啟')
  })
})

describe('Itineraries/Detail settings modal', () => {
  beforeEach(() => {
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: async () => ({ message: null, data: null }),
    } as Response)
  })

  it('opens the settings modal from the gear button without fetching', async () => {
    const wrapper = mountDetail()
    vi.mocked(fetch).mockClear()

    await wrapper.find('button[title="設定通知與限期"]').trigger('click')

    expect(wrapper.text()).toContain('通知與限期設定')
    expect(wrapper.text()).toContain('逐航段通知')
    // daisyUI .label is nowrap inline-flex; flex-wrap keeps the toggle row from overflowing the box
    expect(wrapper.find('label').classes()).toContain('flex-wrap')
    expect(fetch).not.toHaveBeenCalled()
  })

  it('saves the deadline via PATCH and keeps the chip in sync', async () => {
    const wrapper = mountDetail({ deadline: '2026-06-01' })
    await wrapper.find('button[title="設定通知與限期"]').trigger('click')

    const saveBtn = wrapper.findAll('button').find((b) => b.text().trim() === '儲存')
    await saveBtn!.trigger('click')
    await flushPromises()

    expect(fetch).toHaveBeenCalledWith(
      '/api/itineraries/it-1',
      expect.objectContaining({
        method: 'PATCH',
        body: JSON.stringify({ deadline: '2026-06-01', notify_per_leg: false }),
      }),
    )
    expect(wrapper.text()).toContain('購票限期')
    expect(wrapper.text()).toContain('天後')
    expect(wrapper.findAll('dialog.modal-open')).toHaveLength(0)
  })

  it('keeps the in-field clear affordance disabled without a deadline and drops the footer button', async () => {
    const wrapper = mountDetail()
    await wrapper.find('button[title="設定通知與限期"]').trigger('click')

    const clearBtn = wrapper.find('button[aria-label="清除限期"]')
    expect(clearBtn.exists()).toBe(true)
    expect(clearBtn.attributes('disabled')).toBeDefined()
    expect(wrapper.findAll('button').some((b) => b.text().trim() === '移除限期')).toBe(false)
  })

  it('clears the draft in-field without PATCH; PATCH fires only on 儲存', async () => {
    const wrapper = mountDetail({ deadline: '2026-06-01' })
    await wrapper.find('button[title="設定通知與限期"]').trigger('click')
    vi.mocked(fetch).mockClear()

    const clearBtn = wrapper.find('button[aria-label="清除限期"]')
    expect(clearBtn.attributes('disabled')).toBeUndefined()

    await clearBtn.trigger('click')
    expect(fetch).not.toHaveBeenCalled()

    await wrapper
      .findAll('button')
      .find((b) => b.text().trim() === '儲存')!
      .trigger('click')
    await flushPromises()

    expect(fetch).toHaveBeenCalledWith(
      '/api/itineraries/it-1',
      expect.objectContaining({
        method: 'PATCH',
        body: JSON.stringify({ deadline: null, notify_per_leg: false }),
      }),
    )
    expect(wrapper.findAll('dialog.modal-open')).toHaveLength(0)
  })

  it('marks the departure date with a blue dot marker', async () => {
    const wrapper = mountDetail()
    const dp = wrapper.findComponent(VueDatePicker)
    expect(dp.exists()).toBe(true)
    // VTU's props() reads $props, which stays empty for this package's root; vnode props carry the bindings.
    const dpVNodeProps = dp.vm.$.vnode.props as Record<string, unknown> | null
    expect(dpVNodeProps?.markers).toEqual([{ date: '2026-12-01', type: 'dot', color: '#007af0' }])
    // presets are computed from the real clock, so only assert they reach the picker
    expect(Array.isArray(dpVNodeProps?.presetDates)).toBe(true)
  })

  it('toggles notify_per_leg via PATCH', async () => {
    const wrapper = mountDetail({ notifyPerLeg: false })
    await wrapper.find('button[title="設定通知與限期"]').trigger('click')

    await wrapper.find('input[type="checkbox"]').setValue(true)
    const saveBtn = wrapper.findAll('button').find((b) => b.text().trim() === '儲存')
    await saveBtn!.trigger('click')
    await flushPromises()

    expect(fetch).toHaveBeenCalledWith(
      '/api/itineraries/it-1',
      expect.objectContaining({
        method: 'PATCH',
        body: JSON.stringify({ deadline: null, notify_per_leg: true }),
      }),
    )
    expect(wrapper.text()).toContain('已開啟')
  })

  it('shows an inline error and keeps the modal open on failure', async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: false,
      json: async () => ({ message: 'Entry not found', data: null }),
    } as Response)
    const wrapper = mountDetail()
    await wrapper.find('button[title="設定通知與限期"]').trigger('click')

    const saveBtn = wrapper.findAll('button').find((b) => b.text().trim() === '儲存')
    await saveBtn!.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('更新失敗')
    expect(wrapper.find('dialog.modal.modal-open').exists()).toBe(true)
  })
})

describe('Itineraries/Detail archived state', () => {
  beforeEach(() => {
    vi.mocked(fetch).mockResolvedValue({ ok: true, json: async () => ({}) } as Response)
  })

  it('shows 已封存 badge and hides tracking actions when archived', () => {
    const wrapper = mountDetail({ archivedAt: '2026-11-01T00:00:00Z' })

    expect(wrapper.text()).toContain('已封存')
    expect(wrapper.text()).not.toContain('下載最新票價')
    expect(
      wrapper.findAll('button').some((b) => ['暫停追蹤', '開始追蹤'].includes(b.text().trim())),
    ).toBe(false)
    expect(wrapper.find('button[title="設定通知與限期"]').exists()).toBe(true)
  })

  it('keeps 已封存 badge precedence when itinerary is also inactive', () => {
    const wrapper = mountDetail({ archivedAt: '2026-11-01T00:00:00Z', isActive: false })

    expect(wrapper.text()).toContain('已封存')
    expect(wrapper.text()).not.toContain('已暫停')
  })

  it('keeps the active/unarchived actions when not archived', () => {
    const wrapper = mountDetail({ archivedAt: null })

    // archived badge (badge-neutral) is not rendered, active actions intact
    expect(wrapper.findAll('.badge.badge-neutral').length).toBe(0)
    expect(wrapper.text()).toContain('下載最新票價')
  })

  it('confirms before restoring and PATCHes archived:false', async () => {
    const wrapper = mountDetail({ archivedAt: '2026-11-01T00:00:00Z' })
    vi.mocked(fetch).mockClear()

    // open the confirm modal from the join button group
    await wrapper
      .findAll('button')
      .find((b) => b.text().trim() === '恢復追蹤')!
      .trigger('click')
    expect(wrapper.text()).toContain('重新封存')
    expect(fetch).not.toHaveBeenCalled()

    const confirmBtn = wrapper
      .findAll('button')
      .find((b) => b.text().trim() === '恢復追蹤' && b.attributes('type') === 'button')
    await confirmBtn!.trigger('click')
    await flushPromises()

    expect(fetch).toHaveBeenCalledWith(
      '/api/itineraries/it-1',
      expect.objectContaining({
        method: 'PATCH',
        body: JSON.stringify({ archived: false }),
      }),
    )
    expect(vi.mocked(router.reload)).toHaveBeenCalled()
  })

  it('offers archive in the header join for non-archived itineraries', () => {
    const wrapper = mountDetail()

    expect(wrapper.find('button[title="封存此追蹤"]').exists()).toBe(true)
  })

  it('asks for confirmation with 停止追蹤 copy before archiving, without fetching', async () => {
    const wrapper = mountDetail()
    vi.mocked(fetch).mockClear()

    await wrapper.find('button[title="封存此追蹤"]').trigger('click')

    expect(wrapper.text()).toContain('封存？')
    expect(wrapper.text()).toContain('追蹤將停止，並移至已封存列表')
    expect(fetch).not.toHaveBeenCalled()
  })

  it('archives via PATCH and reloads', async () => {
    const toast = useToast() as unknown as { success: ReturnType<typeof vi.fn> }
    const wrapper = mountDetail()
    vi.mocked(fetch).mockClear()

    await wrapper.find('button[title="封存此追蹤"]').trigger('click')

    const confirmBtn = wrapper.findAll('button').find((b) => b.text().trim() === '確認封存')
    await confirmBtn!.trigger('click')
    await flushPromises()

    expect(fetch).toHaveBeenCalledWith(
      '/api/itineraries/it-1',
      expect.objectContaining({
        method: 'PATCH',
        body: JSON.stringify({ archived: true }),
      }),
    )
    expect(toast.success).toHaveBeenCalledWith('已封存')
    expect(vi.mocked(router.reload)).toHaveBeenCalled()
  })

  it('hides the archive action when already archived', () => {
    const wrapper = mountDetail({ archivedAt: '2026-11-01T00:00:00Z' })

    expect(wrapper.find('button[title="封存此追蹤"]').exists()).toBe(false)
  })
})
