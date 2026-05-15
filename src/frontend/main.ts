import { createInertiaApp } from '@inertiajs/vue3'
import type { App, DefineComponent } from 'vue'
import { createApp, h } from 'vue'
import VueToast from 'vue-toast-notification'
import 'vue-toast-notification/dist/theme-bootstrap.css'

import './css/app.css'

type StrOrNum = string | number

declare global {
  interface Window {
    reverseUrl(urlName: string, args?: Record<string, unknown> | StrOrNum | StrOrNum[]): string
  }
}

// create a plugin to use window.reverseUrl in our Components
const routePlugin = {
  install: (app: App) => {
    app.config.globalProperties.$route = window.reverseUrl
  },
}

createInertiaApp({
  resolve: (name) => {
    const pages = import.meta.glob<DefineComponent>('./Pages/**/*.vue', { eager: true })
    return pages[`./Pages/${name}.vue`] as DefineComponent
  },
  setup({ el, App, props, plugin }) {
    const app = createApp({ render: () => h(App, props) })
    app.use(plugin)
    app.use(routePlugin)
    app.use(VueToast, { position: 'top-right' })
    app.mount(el)
  },
})
