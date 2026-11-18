import { useFlashToasts } from '@/composables/useFlashToasts'
import { usePage } from '@inertiajs/vue3'
import { mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, nextTick, reactive } from 'vue'
import { useToast } from 'vue-toast-notification'

const toast = useToast()

const page = reactive<{ props: { flash?: Record<string, string> } }>({ props: {} })

let harness: ReturnType<typeof mount> | null = null

function mountHarness() {
  harness = mount(
    defineComponent({
      setup() {
        useFlashToasts()
        return () => null
      },
    }),
  )
  return harness
}

describe('useFlashToasts', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    page.props = {}
    vi.mocked(usePage).mockImplementation(() => page as never)
  })

  afterEach(() => {
    // an unmounted watcher would keep firing on this shared reactive page
    harness?.unmount()
    harness = null
  })

  it('toasts a server flash at its own level', async () => {
    mountHarness()

    page.props.flash = { success: '已更新設定' }
    await nextTick()

    expect(toast.success).toHaveBeenCalledTimes(1)
    expect(toast.success).toHaveBeenCalledWith('已更新設定')
    expect(toast.error).not.toHaveBeenCalled()
  })

  it('routes each notice level to its matching toast method', async () => {
    mountHarness()

    page.props.flash = { success: 'a', error: 'b', info: 'c', warning: 'd' }
    await nextTick()

    expect(toast.success).toHaveBeenCalledWith('a')
    expect(toast.error).toHaveBeenCalledWith('b')
    expect(toast.info).toHaveBeenCalledWith('c')
    expect(toast.warning).toHaveBeenCalledWith('d')
  })

  it('stays quiet when the popped flash arrives empty', async () => {
    mountHarness()

    page.props.flash = { success: '已更新設定' }
    await nextTick()
    page.props.flash = {}
    await nextTick()

    expect(toast.success).toHaveBeenCalledTimes(1)
  })
})
