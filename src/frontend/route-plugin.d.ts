import type { Page, PageProps, SharedPageProps } from '@inertiajs/core'
import { router } from '@inertiajs/vue3'

type StrOrNum = string | number

declare module '@vue/runtime-core' {
  export interface ComponentCustomProperties {
    $route: (urlName: string, args?: Record<string, unknown> | StrOrNum | StrOrNum[]) => string
    $inertia: typeof router
    // vue-tsc 3.3 misses Inertia's 'vue'-module $page augmentation in templates; mirror it here.
    $page: Page<PageProps & SharedPageProps>
  }
}
