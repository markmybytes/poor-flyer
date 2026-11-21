import { usePage } from '@inertiajs/vue3'
import { onMounted, watch } from 'vue'
import { useToast } from 'vue-toast-notification'

const NOTICE_LEVELS = ['success', 'error', 'info', 'warning'] as const

// Renders the server flash as toasts. Mount once, at the app root: the flash prop arrives
// with the redirect's render, and the server pops it on read, so the next render is empty.
export function useFlashToasts(): void {
  const toast = useToast()

  onMounted(() => {
    watch(
      () => usePage().props.flash,
      (flash) => {
        for (const level of NOTICE_LEVELS) {
          if (flash[level]) toast[level](flash[level])
        }
      },
      { immediate: true },
    )
  })
}
