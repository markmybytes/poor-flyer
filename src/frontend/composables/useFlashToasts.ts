import { usePage } from '@inertiajs/vue3'
import { watch } from 'vue'
import { useToast } from 'vue-toast-notification'

const NOTICE_LEVELS = ['success', 'error', 'info', 'warning']

// Renders the server flash as toasts. Mount once, at the app root: the flash prop arrives
// with the redirect's render, and the server pops it on read, so the next render is empty.
export function useFlashToasts(): void {
  const toast = useToast()

  watch(
    () => usePage().props.flash as Partial<Record<keyof typeof NOTICE_LEVELS, string>> | undefined,
    (flash) => {
      for (const level of NOTICE_LEVELS) {
        if (flash?.[level]) toast[level](flash[level])
      }
    },
    { immediate: true },
  )
}
