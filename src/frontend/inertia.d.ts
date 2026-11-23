import '@inertiajs/core'

declare module '@inertiajs/core' {
  export interface InertiaConfig {
    sharedPageProps: {
      flash: Partial<Record<'success' | 'error' | 'info' | 'warning', string>>
    }
  }
}
