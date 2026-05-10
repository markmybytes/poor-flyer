import tailwindcss from '@tailwindcss/vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue({
      template: {
        transformAssetUrls: {
          base: null,
          includeAbsolute: false,
        },
      },
    }),
    tailwindcss(),
  ],
  build: {
    outDir: 'src/static/dist/',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        app: 'src/frontend/main.ts',
      },
      output: {
        entryFileNames: '[name].js',
        assetFileNames: '[name].[ext]',
      },
    },
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('src/frontend', import.meta.url)),
    },
  },
  server: {
    // flask assume the vite dev server is running on port 5173`
    strictPort: true,
    port: 5173,
  },
})
