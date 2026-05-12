<script setup lang="ts">
import AppLayout from '@/Layouts/AppLayout.vue'
import type { FareSnapshot, Flight } from '@/types'
import { fmtDate, fmtFare, fmtTime, fmtTz, getFlightStats } from '@/utils'
import { Link, router } from '@inertiajs/vue3'
import Chart from 'chart.js/auto'
import { computed, nextTick, onMounted, onUnmounted, ref, useTemplateRef, watch } from 'vue'

const props = defineProps<{
  flight: Flight
}>()

const chartCanvas = useTemplateRef<HTMLCanvasElement>('chartCanvas')
const activeTab = ref<'table' | 'graph'>('table')
const expandedGroups = ref(new Set<number>())
const loading = ref({ loading: null as 'toggle' | 'scrape' | 'delete' | null })

let chart: Chart | null = null

const today = new Date().toISOString().split('T')[0]

const flightStats = computed(() => getFlightStats(props.flight.fareSnapshots))

const dailyGroups = computed(() => {
  const byDate = new Map<string, FareSnapshot[]>()
  for (const s of props.flight.fareSnapshots) {
    const d = s.createdAt.split('T')[0]
    if (!byDate.has(d)) byDate.set(d, [])
    byDate.get(d)!.push(s)
  }

  return [...byDate.entries()]
    .sort(([a], [b]) => b.localeCompare(a))
    .map(([date, snapshots]) => {
      const low =
        snapshots
          .filter((s) => s.scrapeStatus === 'success' && s.fare != null)
          .sort((a, b) => (a.fare as number) - (b.fare as number))[0] ?? null
      return {
        date,
        lowestFare: low?.fare ?? null,
        lowestSnapshot: low ? { flightNumber: low.flightNumber, fare: low.fare } : null,
        snapshots: [...snapshots].sort((a, b) => b.createdAt.localeCompare(a.createdAt)),
      }
    })
})

// Explicit fetch functions for JSON API
function toggleEntry() {
  loading.value.loading = 'toggle'
  fetch(`/api/entries/${props.flight.id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ is_active: !props.flight.isActive }),
  })
    .then((res) => {
      if (res.ok) router.reload()
    })
    .finally(() => {
      loading.value.loading = null
    })
}

function scrapeEntry() {
  loading.value.loading = 'scrape'
  fetch(`/api/entries/${props.flight.id}/scrape`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  })
    .then((res) => {
      if (res.ok) router.reload()
    })
    .finally(() => {
      loading.value.loading = null
    })
}

function deleteEntry() {
  if (!confirm('確認刪除此航班追蹤？')) return
  loading.value.loading = 'delete'
  fetch(`/api/entries/${props.flight.id}`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
  })
    .then((res) => {
      if (res.ok) router.visit('/')
    })
    .finally(() => {
      loading.value.loading = null
    })
}

function initChart() {
  if (!chartCanvas.value || !dailyGroups.value?.length) return
  if (chart) chart.destroy()

  const dateMap = new Map(dailyGroups.value.map((g) => [g.date, g.lowestFare]))
  const dates = dailyGroups.value.map((g) => g.date).sort()
  const start = new Date(dates[0]).getTime()
  const end = new Date(dates[dates.length - 1]).getTime()

  const labels: string[] = []
  const fareData: (number | null)[] = []

  for (let t = start; t <= end; t += 86400000) {
    const iso = new Date(t).toISOString().split('T')[0]
    labels.push(iso)
    fareData.push(dateMap.get(iso) ?? null)
  }

  chart = new Chart(chartCanvas.value, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: '最低票價',
          data: fareData,
          borderColor: '#2563eb',
          backgroundColor: 'rgba(37, 99, 235, 0.1)',
          borderWidth: 2.5,
          tension: 0.4,
          pointBackgroundColor: '#2563eb',
          pointBorderColor: '#fff',
          pointBorderWidth: 1,
          pointRadius: 3.5,
          pointHoverRadius: 7,
          fill: true,
          spanGaps: false,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false }, tooltip: { padding: 12, cornerRadius: 8 } },
      scales: {
        y: { beginAtZero: false, grid: { color: '#f3f4f6' } },
        x: { grid: { display: false } },
      },
      interaction: { intersect: false, mode: 'index' },
    },
  })
}

function switchTab(t: 'table' | 'graph') {
  activeTab.value = t
  if (t === 'graph') {
    nextTick(() => initChart())
  }
}

watch(dailyGroups, () => {
  if (activeTab.value === 'graph') initChart()
})

onMounted(() => activeTab.value === 'graph' && initChart())
onUnmounted(() => chart?.destroy())
</script>

<template>
  <AppLayout>
    <div class="mb-6">
      <Link
        href="/"
        class="text-sm font-medium text-gray-500 transition-colors hover:text-gray-900"
      >
        ← 返回列表
      </Link>
    </div>

    <div
      class="mb-6 flex flex-col items-start justify-between gap-5 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm md:flex-row md:items-center"
    >
      <div>
        <div
          class="mb-1.5 flex items-center gap-3 text-3xl font-black tracking-tight text-gray-900"
        >
          <span>{{ flight.origin }}</span>

          <span class="text-gray-300">→</span>

          <span>{{ flight.destination }}</span>

          <span
            v-if="props.flight.flightDate < today"
            class="ml-2 rounded-full bg-gray-100 px-3 py-1 align-middle text-xs font-semibold tracking-normal text-gray-500"
          >
            已過期
          </span>
        </div>

        <p class="text-sm font-medium text-gray-600">
          航班日期：<strong class="text-gray-900">{{ fmtDate(flight.flightDate) }}</strong>

          <span v-if="flight.deadline" class="ml-4 text-gray-400">|</span>

          <span v-if="flight.deadline" class="ml-4"
            >限期：<strong class="text-gray-900">{{ fmtDate(flight.deadline) }}</strong></span
          >
        </p>
      </div>

      <div class="flex shrink-0 gap-3">
        <button
          class="rounded-xl bg-gray-100 px-4 py-2.5 text-sm font-semibold text-gray-700 transition-colors hover:bg-gray-200 disabled:opacity-50"
          :disabled="loading.loading === 'toggle'"
          @click="toggleEntry"
        >
          {{ flight.isActive ? '停止追蹤' : '開啟追蹤' }}
        </button>

        <button
          class="rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-all hover:bg-blue-500 hover:shadow disabled:opacity-50"
          :disabled="loading.loading === 'scrape'"
          @click="scrapeEntry"
        >
          {{ loading.loading === 'scrape' ? '擷取中...' : '擷取最新價格' }}
        </button>

        <button
          class="rounded-xl bg-red-50 px-4 py-2.5 text-sm font-semibold text-red-600 transition-colors hover:bg-red-100 disabled:opacity-50"
          :disabled="loading.loading === 'delete'"
          @click="deleteEntry"
        >
          刪除
        </button>
      </div>
    </div>

    <div
      v-if="flight.rule37Analysis"
      class="mb-8 flex flex-col items-center justify-between gap-6 rounded-2xl border p-6 shadow-sm md:flex-row"
      :class="{
        'border-green-200 bg-green-50': flight.rule37Analysis.phase === 'BUY_SIGNAL',
        'border-amber-200 bg-amber-50': flight.rule37Analysis.phase === 'OBSERVING',
        'border-gray-200 bg-white': flight.rule37Analysis.phase === 'WAITING',
      }"
    >
      <div class="flex-1">
        <p class="mb-1 text-xs font-bold tracking-widest text-gray-400 uppercase">37% 法則指標</p>

        <div class="flex items-center gap-3">
          <template v-if="flight.rule37Analysis.phase === 'BUY_SIGNAL'">
            <span class="relative flex h-3 w-3">
              <span
                class="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75"
              ></span>

              <span class="relative inline-flex h-3 w-3 rounded-full bg-green-500"></span>
            </span>

            <span class="text-2xl font-black text-green-700">購買信號 (最佳時機)</span>
          </template>

          <template v-else-if="flight.rule37Analysis.phase === 'OBSERVING'">
            <span class="h-3 w-3 rounded-full bg-amber-500"></span>

            <span class="text-2xl font-black text-amber-700">觀察期</span>

            <span
              class="ml-2 rounded-full bg-amber-200/50 px-2.5 py-0.5 text-sm font-medium text-amber-800"
            >
              {{
                Math.ceil(
                  (new Date(flight.rule37Analysis.cutoffDate).getTime() -
                    new Date(today).getTime()) /
                    86400000,
                )
              }}
              天後結束
            </span>
          </template>

          <template v-else>
            <span class="h-3 w-3 rounded-full bg-gray-400"></span>

            <span class="text-2xl font-black text-gray-700">等待中</span>
          </template>
        </div>

        <p class="mt-1.5 text-sm font-medium text-gray-600">
          決策轉換期：<strong class="text-gray-900">{{
            fmtDate(flight.rule37Analysis.cutoffDate)
          }}</strong>

          <span class="mx-2 text-gray-300">|</span>

          門檻價格：<strong class="text-gray-900">{{
            fmtFare(flight.rule37Analysis.historyBestVal)
          }}</strong>
        </p>
      </div>

      <div
        class="grid grid-cols-2 gap-x-8 gap-y-2 border-t border-gray-200/60 pt-4 pl-0 text-right md:border-t-0 md:border-l md:pt-0 md:pl-6"
      >
        <div>
          <p class="text-xs font-bold tracking-widest text-gray-400 uppercase">最新價格</p>

          <p class="text-xl font-bold text-gray-900">
            {{ fmtFare(flight.rule37Analysis.latestVal) }}
          </p>
        </div>

        <div>
          <p class="text-xs font-bold tracking-widest text-gray-400 uppercase">歷史最低</p>

          <p class="text-xl font-bold text-green-600">
            {{ fmtFare(flight.rule37Analysis.allTimeLow) }}
          </p>
        </div>
      </div>
    </div>

    <div
      v-else
      class="mb-8 rounded-2xl border border-dashed border-gray-300 bg-gray-50 p-6 text-center"
    >
      <p class="text-sm font-medium text-gray-500">
        未設定購買限期，無法計算 37% 最佳購買法則指標。
      </p>
    </div>

    <div class="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
      <div class="flex border-b border-gray-100 bg-gray-50/50 p-2">
        <button
          class="flex-1 rounded-lg py-2.5 text-sm font-bold transition-all"
          :class="
            activeTab === 'table'
              ? 'bg-white text-gray-900 shadow-sm ring-1 ring-gray-200'
              : 'text-gray-500 hover:text-gray-700'
          "
          @click="switchTab('table')"
        >
          詳細數據列表
        </button>

        <button
          class="flex-1 rounded-lg py-2.5 text-sm font-bold transition-all"
          :class="
            activeTab === 'graph'
              ? 'bg-white text-gray-900 shadow-sm ring-1 ring-gray-200'
              : 'text-gray-500 hover:text-gray-700'
          "
          @click="switchTab('graph')"
        >
          價格趨勢圖表
        </button>
      </div>

      <div v-show="activeTab === 'table'" class="p-0">
        <template v-if="dailyGroups.length">
          <div
            v-for="(group, index) in dailyGroups"
            :key="group.date"
            class="border-b border-gray-100 last:border-b-0"
          >
            <button
              class="flex w-full items-center justify-between px-5 py-3 transition-colors hover:bg-gray-50/80"
              :class="{
                'bg-green-100/30': group.lowestSnapshot?.fare === flightStats.lowest,
                'bg-blue-100/30':
                  flight.rule37Analysis &&
                  group.date >= flight.rule37Analysis.cutoffDate &&
                  group.lowestSnapshot?.fare === flight.rule37Analysis.historyBestVal,
              }"
              @click="
                expandedGroups.has(index) ? expandedGroups.delete(index) : expandedGroups.add(index)
              "
            >
              <div class="flex flex-1 items-center gap-4 text-left">
                <div
                  class="flex w-6 items-center justify-center text-gray-300 transition-transform"
                  :class="{ 'rotate-90': expandedGroups.has(index) }"
                >
                  ▶
                </div>

                <div>
                  <p class="leading-tight font-bold text-gray-900">
                    {{ fmtDate(group.date) }}
                    <span class="ml-1 text-xs font-medium text-gray-500"
                      >({{
                        ['日', '一', '二', '三', '四', '五', '六'][new Date(group.date).getDay()]
                      }})</span
                    >
                  </p>

                  <p class="text-xs font-medium text-gray-500">
                    <template v-if="group.lowestSnapshot">
                      當日最低：<span class="font-bold text-gray-700"
                        >{{ fmtFare(group.lowestFare) }}
                      </span>

                      <template v-if="group.lowestSnapshot.flightNumber"
                        >· {{ group.lowestSnapshot.flightNumber }}</template
                      >
                    </template>

                    <span v-else class="text-red-500">無有效價格數據</span>
                  </p>
                </div>
              </div>

              <div
                class="shrink-0 rounded-full bg-gray-100 px-3 py-1 text-xs font-semibold text-gray-500"
              >
                {{ group.snapshots.length }} 筆紀錄
              </div>
            </button>

            <div
              v-if="flight.rule37Analysis && group.date === flight.rule37Analysis.cutoffDate"
              class="border-y border-amber-100 bg-amber-50 px-5 py-1.5 text-center"
            >
              <p class="text-[11px] font-bold tracking-widest text-amber-700">
                ◆ 37% 法則決策期開始 ◆
              </p>
            </div>

            <div
              v-show="expandedGroups.has(index)"
              class="border-t border-gray-100 bg-gray-50/50 px-5 py-3"
            >
              <div class="overflow-x-auto rounded-xl border border-gray-200 bg-white">
                <table class="w-full text-sm">
                  <thead class="border-b border-gray-200 bg-gray-50">
                    <tr>
                      <th
                        class="px-4 py-2 text-left text-xs font-bold tracking-wider text-gray-500 uppercase"
                      >
                        航班編號
                      </th>

                      <th
                        class="px-4 py-2 text-left text-xs font-bold tracking-wider text-gray-500 uppercase"
                      >
                        起飛時間
                      </th>

                      <th
                        class="px-4 py-2 text-left text-xs font-bold tracking-wider text-gray-500 uppercase"
                      >
                        降落時間
                      </th>

                      <th
                        class="px-4 py-2 text-right text-xs font-bold tracking-wider text-gray-500 uppercase"
                      >
                        票價
                      </th>
                    </tr>
                  </thead>

                  <tbody class="divide-y divide-gray-100">
                    <tr
                      v-for="snap in group.snapshots.toSorted(
                        (a, b) => a.flightNumber?.localeCompare(b.flightNumber ?? '') ?? 0,
                      )"
                      :key="snap.id"
                      class="transition-colors hover:bg-gray-50"
                      :class="{ 'bg-red-50/50': snap.scrapeStatus === 'error' }"
                    >
                      <td class="px-4 py-2 font-semibold text-gray-900">
                        {{ snap.flightNumber ?? '—' }}
                      </td>

                      <td class="px-4 py-2 text-gray-600">
                        {{ fmtTime(snap.departureAt) }}
                        <span class="text-[10px] text-gray-400">{{ fmtTz(snap.departureAt) }}</span>
                      </td>

                      <td class="px-4 py-2 text-gray-600">
                        {{ fmtTime(snap.arrivalAt) }}
                        <span class="text-[10px] text-gray-400">{{ fmtTz(snap.arrivalAt) }}</span>
                      </td>

                      <td class="px-4 py-2 text-right font-bold text-gray-900">
                        <template v-if="snap.scrapeStatus === 'success' && snap.fare !== null">
                          <div class="flex items-center justify-end gap-2">
                            <div class="flex gap-1">
                              <span
                                v-if="snap.fare === flightStats.lowest"
                                class="rounded bg-green-100 px-1.5 py-0.5 text-[10px] leading-none font-bold text-green-700"
                                >歷史低位</span
                              >

                              <span
                                v-if="
                                  flight.rule37Analysis &&
                                  snap.fare === flight.rule37Analysis.historyBestVal &&
                                  (snap.departureAt?.slice(0, 10) ?? '') >=
                                    flight.rule37Analysis.cutoffDate
                                "
                                class="rounded bg-blue-100 px-1.5 py-0.5 text-[10px] leading-none font-bold text-blue-700"
                                >最佳選擇</span
                              >
                            </div>

                            <span>{{ fmtFare(snap.fare) }}</span>
                          </div>
                        </template>

                        <span v-else class="text-xs text-red-500">擷取失敗</span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </template>

        <div v-else class="py-20 text-center">
          <p class="font-medium text-gray-400">暫無價格快照數據。</p>
        </div>
      </div>

      <div v-show="activeTab === 'graph'" class="p-8">
        <template v-if="dailyGroups.length">
          <canvas ref="chartCanvas" height="100"></canvas>
        </template>

        <div v-else class="py-20 text-center">
          <p class="font-medium text-gray-400">暫無趨勢數據。</p>
        </div>
      </div>
    </div>
  </AppLayout>
</template>
