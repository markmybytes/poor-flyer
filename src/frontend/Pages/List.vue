<script setup lang="ts">
import AppLayout from '@/Layouts/AppLayout.vue'
import type { Flight } from '@/types'
import { fmtDate, fmtFare, getFlightStats } from '@/utils'
import { Link } from '@inertiajs/vue3'

defineProps<{ flights: Flight[] }>()
</script>

<template>
  <AppLayout>
    <div class="mb-8 flex items-end justify-between">
      <div>
        <h2 class="text-3xl font-extrabold tracking-tight text-gray-900">追蹤清單</h2>

        <p class="mt-2 text-sm font-medium text-gray-500">管理並追蹤您的航班價格變化</p>
      </div>

      <Link
        href="/create"
        class="rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition-all hover:bg-blue-500 hover:shadow-md"
      >
        + 建立追蹤
      </Link>
    </div>

    <div v-if="flights?.length" class="grid gap-6 lg:grid-cols-2">
      <div
        v-for="flight in flights"
        :key="flight.id"
        class="group relative flex flex-col rounded-2xl border border-gray-200 bg-white p-6 shadow-sm transition-all hover:border-blue-200 hover:shadow-md"
      >
        <div class="mb-5 flex items-start justify-between">
          <div>
            <div class="flex items-center gap-3 text-2xl font-black tracking-tight text-gray-900">
              <span>{{ flight.origin }}</span>

              <span class="text-gray-300">→</span>

              <span>{{ flight.destination }}</span>
            </div>

            <p class="mt-1.5 text-sm font-medium text-gray-600">
              出發日期：{{ fmtDate(flight.flightDate) }}
            </p>
          </div>

          <div class="shrink-0">
            <span
              v-if="!flight.isActive"
              class="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-700"
            >
              已暫停
            </span>

            <span
              v-else
              class="rounded-full bg-green-50 px-2.5 py-1 text-xs font-semibold text-green-700 ring-1 ring-green-600/20 ring-inset"
            >
              追蹤中
            </span>
          </div>
        </div>

        <div
          class="mb-6 flex items-end gap-6 rounded-xl border border-gray-100/50 bg-gray-50/80 p-4"
        >
          <div class="flex-1">
            <p class="mb-1 text-xs font-bold tracking-widest text-gray-400 uppercase">最新票價</p>

            <p class="text-3xl font-black">
              {{ fmtFare(getFlightStats(flight.fareSnapshots || []).latest) }}
            </p>
          </div>

          <div>
            <p class="mb-1 text-xs font-bold tracking-widest text-gray-400 uppercase">歷史最低</p>

            <p class="text-lg font-bold text-green-600">
              {{ fmtFare(getFlightStats(flight.fareSnapshots || []).lowest) }}
            </p>
          </div>

          <div>
            <p class="mb-1 text-xs font-bold tracking-widest text-gray-400 uppercase">歷史最高</p>

            <p class="text-lg font-bold text-red-500">
              {{ fmtFare(getFlightStats(flight.fareSnapshots || []).highest) }}
            </p>
          </div>
        </div>

        <div class="mt-auto h-18">
          <div
            v-if="flight.rule37Analysis && flight.rule37Analysis.latestVal !== null"
            class="flex h-full items-center justify-between rounded-xl border p-3.5"
            :class="{
              'border-green-200 bg-green-50': flight.rule37Analysis.phase === 'BUY_SIGNAL',
              'border-gray-200 bg-gray-50': flight.rule37Analysis.phase === 'OBSERVING',
              'border-sky-200 bg-sky-50': flight.rule37Analysis.phase === 'WAITING',
            }"
          >
            <div>
              <p class="mb-1 text-xs font-bold tracking-widest text-gray-400 uppercase">
                37% 法則指標
              </p>

              <div class="flex items-center gap-2">
                <template v-if="flight.rule37Analysis.phase === 'BUY_SIGNAL'">
                  <span class="relative flex h-2.5 w-2.5">
                    <span
                      class="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75"
                    ></span>

                    <span class="relative inline-flex h-2.5 w-2.5 rounded-full bg-green-500"></span>
                  </span>

                  <span class="text-sm font-bold text-green-700">購買信號（最佳時機）</span>
                </template>

                <template v-else-if="flight.rule37Analysis.phase === 'OBSERVING'">
                  <span class="h-2.5 w-2.5 rounded-full bg-gray-400"></span>

                  <span class="text-sm font-bold text-gray-700">觀察期</span>
                </template>

                <template v-else>
                  <span class="h-2.5 w-2.5 rounded-full bg-sky-500"></span>

                  <span class="text-sm font-bold text-sky-600">
                    等待中（門檻: {{ fmtFare(flight.rule37Analysis.historyBestVal) }}）
                  </span>
                </template>
              </div>
            </div>

            <div class="border-l border-gray-200/60 pl-3 text-right">
              <p class="mb-0.5 text-xs font-medium text-gray-500">限期</p>

              <p class="text-sm font-bold text-gray-700">{{ fmtDate(flight.deadline) }}</p>
            </div>
          </div>

          <div
            v-else-if="flight.rule37Analysis"
            class="flex h-full items-center justify-center rounded-xl border border-dashed border-gray-300 bg-gray-50 p-3.5"
          >
            <span class="text-sm font-medium text-gray-500">收集數據中</span>
          </div>

          <div
            v-else
            class="flex h-full items-center justify-center rounded-xl border border-dashed border-gray-300 bg-gray-50 p-3.5"
          >
            <span class="text-sm font-medium text-gray-500">未設定購買限期，無法計算 37% 法則</span>
          </div>
        </div>

        <div class="mt-6 flex items-center justify-end gap-3 border-t border-gray-100 pt-5">
          <Link
            :href="`/detail/${flight.id}`"
            class="rounded-xl bg-gray-900 px-5 py-2 text-sm font-semibold text-white shadow-sm transition-all hover:bg-gray-800 hover:shadow"
          >
            查看詳情
          </Link>
        </div>
      </div>
    </div>

    <div
      v-else
      class="flex flex-col items-center justify-center rounded-3xl border-2 border-dashed border-gray-200 bg-white py-28 text-center shadow-sm"
    >
      <div
        class="mb-5 flex h-20 w-20 items-center justify-center rounded-full bg-blue-50 text-4xl shadow-inner"
      >
        ✈️
      </div>

      <h3 class="mb-2 text-xl font-bold text-gray-900">尚未追蹤任何航班</h3>

      <p class="mb-8 max-w-sm text-sm leading-relaxed text-gray-500">
        加入您想關注的出發地與目的地，我們將為您不間斷追蹤價格，並在最佳時機提示您購買。
      </p>

      <Link
        href="/create"
        class="rounded-xl bg-blue-600 px-8 py-3 font-semibold text-white shadow-sm transition-all hover:-translate-y-0.5 hover:bg-blue-500 hover:shadow-md"
      >
        建立您的第一個追蹤
      </Link>
    </div>
  </AppLayout>
</template>
