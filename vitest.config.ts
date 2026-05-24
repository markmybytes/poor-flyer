import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [
    vue(),
    {
      name: 'static-asset-stub',
      resolveId(id) {
        if (id.startsWith('/static/')) return `\0virtual:${id}`
      },
      load(id) {
        if (id.startsWith('\0virtual:/static/')) return 'export default ""'
      },
    },
  ],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./tests/frontend/setup.ts'],
    include: ['tests/frontend/**/*.test.ts'],
    server: {
      deps: {
        inline: ['chart.js'],
      },
    },
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('src/frontend', import.meta.url)),
    },
  },
})
