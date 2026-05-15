<script setup lang="ts">
import { Link } from '@inertiajs/vue3'
</script>

<template>
  <div class="min-h-screen bg-gray-50 font-sans text-gray-900 antialiased">
    <nav class="sticky top-0 z-30 border-b border-gray-200 bg-white/80 backdrop-blur-md">
      <div class="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
        <Link
          href="/"
          class="flex items-center gap-2 text-xl font-black tracking-tight text-gray-900 transition-opacity hover:opacity-80"
        >
          <span class="text-blue-600">✈</span>

          <span>價格追蹤器</span>
        </Link>

        <div class="flex items-center gap-1">
          <Link
            href="/flights/"
            class="rounded-lg px-4 py-2 text-sm font-semibold text-gray-700 transition-all hover:bg-gray-100"
          >
            追蹤清單
          </Link>

          <Link
            href="/settings/"
            class="flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold text-gray-700 transition-all hover:bg-gray-100"
          >
            <span>⚙️</span>

            <span>設定</span>
          </Link>
        </div>
      </div>
    </nav>

    <main class="mx-auto max-w-5xl px-6 py-10">
      <slot />
    </main>
  </div>
</template>
