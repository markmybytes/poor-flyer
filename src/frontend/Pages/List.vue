<script setup lang="ts">
import AppLayout from '@/Layouts/AppLayout.vue';
import { Link, router } from '@inertiajs/vue3';

defineProps<{
  entries: {
    entry: {
      id: string
      origin: string
      destination: string
      flightDate: string
      deadline: string | null
      isActive: boolean
      pastDeparture: boolean
    }
    rule37Status: {
      phase: string
      cutoffDate: string
      historyBestVal: number | null
      latestVal: number | null
      allTimeHigh: number | null
      allTimeLow: number | null
    } | null
    minFare: number | null
    maxFare: number | null
    latestFare: number | null
    lastScraped: string | null
  }[]
}>()
</script>

<template>
  <AppLayout>
    <div class="mb-8 flex items-center justify-between">
      <h2 class="text-3xl font-bold">追蹤的航班</h2>

      <Link href="/create" class="rounded-lg bg-blue-600 px-5 py-2 font-medium text-white">
        + 追蹤航班
      </Link>
    </div>

    <div v-if="entries.length" class="space-y-3">
      <div
        v-for="item in entries"
        :key="item.entry.id"
        class="rounded-lg border bg-white p-5 shadow-sm"
      >
        <div class="mb-3 flex items-start justify-between">
          <div class="flex-1">
            <h3 class="mb-1 text-lg font-bold text-gray-900">
              {{ item.entry.origin }} → {{ item.entry.destination }} |
              {{ item.entry.flightDate.replace(/-/g, '/') }}
            </h3>
          </div>

          <div class="shrink-0 text-right">
            <span
              v-if="item.entry.pastDeparture"
              class="rounded-full bg-gray-100 px-2 py-1 text-xs text-gray-500"
            >
              已過
            </span>

            <span
              v-else-if="!item.entry.isActive"
              class="rounded-full bg-amber-100 px-2 py-1 text-xs text-amber-700"
            >
              已暫停
            </span>

            <span v-else class="rounded-full bg-green-100 px-2 py-1 text-xs text-green-700">
              活躍
            </span>
          </div>
        </div>

        <div class="mb-3 grid grid-cols-4 gap-3 text-center">
          <div class="rounded-lg bg-green-50 py-2">
            <p class="mb-0.5 text-xs text-gray-400">最低</p>

            <p class="font-semibold text-green-700">
              {{ item.minFare !== null ? Math.round(item.minFare) : '—' }}
            </p>
          </div>

          <div class="rounded-lg bg-blue-50 py-2">
            <p class="mb-0.5 text-xs text-gray-400">最新</p>

            <p class="font-semibold text-blue-700">
              {{ item.latestFare !== null ? Math.round(item.latestFare) : '—' }}
            </p>
          </div>

          <div class="rounded-lg bg-red-50 py-2">
            <p class="mb-0.5 text-xs text-gray-400">最高</p>

            <p class="font-semibold text-red-700">
              {{ item.maxFare !== null ? Math.round(item.maxFare) : '—' }}
            </p>
          </div>

          <div>
            <p class="mb-0.5 text-xs text-gray-400">觀察期</p>

            <p class="font-semibold text-gray-900">
              {{ item.entry.deadline ? item.entry.deadline.slice(5).replace('-', '/') : '—' }}
            </p>
          </div>
        </div>

        <div class="flex items-center justify-between border-t pt-3">
          <div>
            <template v-if="item.rule37Status">
              <span
                v-if="item.rule37Status.phase === 'BUY_SIGNAL'"
                class="inline-flex items-center gap-1 text-sm font-medium text-green-700"
                ><span class="h-2 w-2 rounded-full bg-green-600"></span>購買信號</span
              >

              <span
                v-else-if="item.rule37Status.phase === 'OBSERVING'"
                class="inline-flex items-center gap-1 text-sm font-medium text-amber-700"
                ><span class="h-2 w-2 rounded-full bg-amber-600"></span>觀察中</span
              >

              <span v-else class="inline-flex items-center gap-1 text-sm font-medium text-gray-600"
                ><span class="h-2 w-2 rounded-full bg-gray-400"></span>等待中</span
              >
            </template>

            <span v-else class="text-xs text-gray-400">未設定期限</span>
          </div>

          <div class="flex items-center gap-2">
            <Link
              :href="`/detail/${item.entry.id}`"
              class="rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white"
            >
              查看
            </Link>

            <button
              type="button"
              class="rounded bg-gray-100 px-3 py-1.5 text-sm text-gray-600"
              @click="router.post(`/entries/${item.entry.id}/toggle`)"
            >
              {{ item.entry.isActive ? '禁用' : '啟用' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="rounded-lg border bg-white p-16 text-center shadow-sm">
      <p class="mb-5 text-lg text-gray-400">尚未追蹤任何航班。</p>

      <Link
        href="/create"
        class="inline-block rounded-lg bg-blue-600 px-8 py-2.5 font-medium text-white"
      >
        追蹤您的第一個航班
      </Link>
    </div>
  </AppLayout>
</template>
