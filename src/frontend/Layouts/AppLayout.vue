<script setup lang="ts">
import { Link } from '@inertiajs/vue3'
</script>

<template>
  <div class="tracker-shell">
    <div class="mx-auto max-w-7xl px-4 py-2 sm:px-6 sm:py-4">
      <nav class="tracker-panel navbar z-30 mb-8 rounded-lg px-4 py-2 sm:px-6 sm:py-4">
        <div class="navbar-start gap-3">
          <Link href="/" class="btn h-auto min-h-0 gap-3 px-2 btn-ghost hover:bg-transparent">
            <div class="placeholder avatar">
              <div class="w-10 overflow-hidden rounded-lg sm:w-11">
                <img src="/static/favicon.svg" alt="PoorFlyer" />
              </div>
            </div>

            <div class="hidden text-left sm:block">
              <div class="text-lg font-black tracking-tight text-base-content">PoorFlyer</div>

              <div class="text-xs font-medium text-base-content/60">
                追蹤每日機票價格 選擇最佳時機購票
              </div>
            </div>
          </Link>
        </div>

        <div class="navbar-end gap-2 lg:gap-4">
          <div class="flex flex-wrap justify-end gap-2">
            <Link
              href="/itineraries/"
              class="btn btn-sm sm:btn-md"
              :class="
                $page.url.startsWith('/itineraries')
                  ? 'font-semibold btn-primary'
                  : 'font-semibold btn-ghost'
              "
            >
              <span class="hidden sm:inline">追蹤清單</span>

              <span class="sm:hidden">追蹤</span>
            </Link>

            <Link
              href="/settings/"
              class="btn btn-sm sm:btn-md"
              :class="
                $page.url.startsWith('/settings')
                  ? 'font-semibold btn-primary'
                  : 'font-semibold btn-ghost'
              "
            >
              <span class="hidden sm:inline">設定</span>

              <span class="sm:hidden">設定</span>
            </Link>

            <Link
              href="/logs/"
              class="btn btn-sm sm:btn-md"
              :class="
                $page.url.startsWith('/logs')
                  ? 'font-semibold btn-primary'
                  : 'font-semibold btn-ghost'
              "
            >
              <span class="hidden sm:inline">系統紀錄</span>

              <span class="sm:hidden">紀錄</span>
            </Link>
          </div>
        </div>
      </nav>

      <main class="mx-auto max-w-7xl pb-10">
        <slot />
      </main>
    </div>
  </div>
</template>
