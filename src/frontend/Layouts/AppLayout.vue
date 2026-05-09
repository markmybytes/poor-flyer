<script setup lang="ts">
import { Link } from '@inertiajs/vue3'
</script>

<template>
  <div class="min-h-screen bg-gray-50">
    <nav class="border-b bg-white">
      <div class="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        <Link href="/" class="text-xl font-bold text-gray-800">✈ 價格追蹤器</Link>

        <Link href="/create" class="rounded-lg bg-blue-600 px-4 py-1.5 text-white">+ 追蹤航班</Link>
      </div>
    </nav>

    <main class="mx-auto max-w-6xl px-4 py-8">
      <slot />
    </main>
  </div>
</template>
