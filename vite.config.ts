import tailwindcss from '@tailwindcss/vite'
import vue from '@vitejs/plugin-vue'
import fs from 'node:fs'
import path from 'node:path'
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
    {
      name: 'flask-vite-hot-file',
      configureServer(server) {
        server.httpServer?.once('listening', () => {
          setTimeout(() => {
            const urls = server.resolvedUrls?.local;
            if (urls && urls.length > 0) {
              const hotFilePath = path.resolve('src/static/dist/hot');
              fs.mkdirSync(path.dirname(hotFilePath), { recursive: true });
              fs.writeFileSync(hotFilePath, urls[0].replace(/\/$/, ''));
            }
          }, 50); // wait a tick for resolvedUrls to populate
        });
      }
    }
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
})
