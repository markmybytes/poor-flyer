<script setup lang="ts">
import { ref, onMounted, onUnmounted, useTemplateRef } from 'vue'
import { router, Link } from '@inertiajs/vue3'
import {
  Chart,
  LineController,
  LineElement,
  PointElement,
  LinearScale,
  CategoryScale,
  Legend,
  Tooltip,
} from 'chart.js'

import AppLayout from '@/Layouts/AppLayout.vue'

Chart.register(LineController, LineElement, PointElement, LinearScale, CategoryScale, Legend, Tooltip)

interface Snapshot {
  id: string
  flight_number: string | null
  departure_at: string | null
  arrival_at: string | null
  fare: number | null
  scrape_status: string
  error_message: string | null
}

interface DailyGroup {
  date: string
  lowest_fare: number | null
  lowest_snapshot: { flight_number: string | null; fare: number | null } | null
  snapshots: Snapshot[]
}

interface Rule37Status {
  phase: string
  cutoff_date: string
  history_best_val: number | null
  latest_val: number | null
  all_time_high: number | null
  all_time_low: number | null
}

interface TrackingEntry {
  id: string
  origin: string
  destination: string
  flight_date: string
  deadline: string | null
  is_active: boolean
  past_departure: boolean
}

const props = defineProps<{
  entry: TrackingEntry
  daily_groups: DailyGroup[]
  today: string
  rule37_status: Rule37Status | null
  all_time_low: number | null
  all_time_high: number | null
}>()

const activeTab = ref<'table' | 'graph'>('table')
const expandedGroups = ref<Set<number>>(new Set())
const chartCanvas = useTemplateRef<HTMLCanvasElement>('chartCanvas')
let chart: Chart | null = null

function toggleGroup(index: number) {
  if (expandedGroups.value.has(index)) {
    expandedGroups.value.delete(index)
  } else {
    expandedGroups.value.add(index)
  }
}

function formatDate(iso: string): string {
  return iso.replace(/-/g, '/')
}

function formatDateWithWeekday(iso: string): string {
  const d = new Date(iso + 'T00:00:00')
  const days = ['日', '一', '二', '三', '四', '五', '六']
  return `${iso.replace(/-/g, '/')} (${days[d.getDay()]})`
}

function formatTime(iso: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleTimeString('zh-HK', { hour: '2-digit', minute: '2-digit', hour12: false })
}

function formatTz(iso: string | null): string {
  if (!iso) return ''
  const match = iso.match(/([+-]\d{2}:\d{2}|Z)$/)
  return match ? match[0] : ''
}

function formatFare(fare: number | null): string {
  return fare !== null ? `$${Math.round(fare)}` : '—'
}

function isAllTimeHigh(snap: Snapshot): boolean {
  return (
    snap.scrape_status === 'success' &&
    snap.fare !== null &&
    props.all_time_high !== null &&
    snap.fare === props.all_time_high
  )
}

function isAllTimeLow(snap: Snapshot): boolean {
  return (
    snap.scrape_status === 'success' &&
    snap.fare !== null &&
    props.all_time_low !== null &&
    snap.fare === props.all_time_low
  )
}

function isObservationBest(snap: Snapshot): boolean {
  if (
    !props.rule37_status ||
    snap.scrape_status !== 'success' ||
    snap.fare === null ||
    !snap.departure_at
  )
    return false
  const snapDate = snap.departure_at.slice(0, 10)
  return (
    snapDate >= props.rule37_status.cutoff_date &&
    snap.fare === props.rule37_status.history_best_val
  )
}

function snapRowClass(snap: Snapshot): string {
  if (snap.scrape_status === 'error') return 'bg-gray-50'
  if (isAllTimeHigh(snap)) return 'bg-red-50'
  if (isAllTimeLow(snap)) return 'bg-green-50'
  if (isObservationBest(snap)) return 'bg-blue-50'
  return ''
}

function snapFareClass(snap: Snapshot): string {
  if (snap.scrape_status === 'error') return 'text-gray-600'
  if (isAllTimeHigh(snap)) return 'text-red-700'
  if (isAllTimeLow(snap)) return 'text-green-700'
  if (isObservationBest(snap)) return 'text-blue-700'
  return 'text-gray-900'
}

function groupBgClass(group: DailyGroup, index: number): string {
  if (
    group.lowest_snapshot &&
    group.lowest_snapshot.fare !== null &&
    group.lowest_snapshot.fare === props.all_time_low
  ) {
    return 'bg-green-50'
  }
  if (
    props.rule37_status &&
    group.lowest_snapshot &&
    group.date >= props.rule37_status.cutoff_date &&
    group.lowest_snapshot.fare === props.rule37_status.history_best_val
  ) {
    return 'bg-blue-50'
  }
  return ''
}

function scrape() {
  router.post(`/entries/${props.entry.id}/scrape`)
}

function toggleEntry() {
  router.post(`/entries/${props.entry.id}/toggle`)
}

function deleteEntry() {
  if (confirm('刪除此項和所有數據?')) {
    router.post(`/entries/${props.entry.id}/delete`)
  }
}

function initChart() {
  if (!chartCanvas.value || !props.daily_groups.length) return
  const chartData = props.daily_groups
    .filter((g) => g.lowest_fare !== null)
    .map((g) => ({ date: g.date, fare: g.lowest_fare as number }))
    .reverse()

  chart = new Chart(chartCanvas.value, {
    type: 'line',
    data: {
      labels: chartData.map((d) => d.date),
      datasets: [
        {
          label: '票價 (港幣)',
          data: chartData.map((d) => d.fare),
          borderColor: '#2563eb',
          backgroundColor: 'rgba(37, 99, 235, 0.05)',
          tension: 0.3,
          pointBackgroundColor: '#2563eb',
          pointRadius: 4,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: true } },
      scales: { y: { beginAtZero: false } },
    },
  })
}

onMounted(() => {
  if (activeTab.value === 'graph') initChart()
})

onUnmounted(() => {
  chart?.destroy()
})

function switchTab(tab: 'table' | 'graph') {
  activeTab.value = tab
  if (tab === 'graph' && !chart) {
    setTimeout(initChart, 0)
  }
}
</script>

<template>
  <AppLayout>
    <div class="mb-5">
      <Link href="/" class="text-sm text-blue-600">← 返回列表</Link>
    </div>

    <div class="mb-5 rounded-lg border bg-white p-6 shadow-sm">
      <div class="flex items-start justify-between">
        <div>
          <h2 class="mb-1 text-3xl font-bold">{{ entry.origin }} → {{ entry.destination }}</h2>

          <p class="text-sm text-gray-600">
            航班 <strong>{{ formatDate(entry.flight_date) }}</strong>
            <span
              v-if="entry.past_departure"
              class="ml-2 rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500"
            >
              已過期
            </span>
          </p>

          <p v-if="entry.deadline" class="mt-1 text-sm text-gray-600">
            限期：<strong>{{ formatDate(entry.deadline) }}</strong>
          </p>
        </div>

        <div class="flex gap-2">
          <button
            type="button"
            class="rounded-lg bg-gray-100 px-3 py-1.5 text-sm text-gray-600"
            @click="toggleEntry"
          >
            {{ entry.is_active ? '停用' : '啟用' }}
          </button>

          <button
            v-if="entry.flight_date >= today"
            type="button"
            class="rounded-lg bg-blue-600 px-3 py-1.5 text-sm text-white"
            @click="scrape"
          >
            擷取最新價格
          </button>

          <button
            type="button"
            class="rounded-lg bg-red-50 px-3 py-1.5 text-sm text-red-600"
            @click="deleteEntry"
          >
            刪除
          </button>
        </div>
      </div>
    </div>

    <div v-if="rule37_status" class="mb-5 rounded-lg border bg-white p-6 shadow-sm">
      <p class="mb-3 text-xs font-semibold tracking-widest text-gray-400 uppercase">
        37% 法則 | 最低：<span class="text-green-700">{{ formatFare(rule37_status.all_time_low) }}</span> | 最高：<span
          class="text-red-700"
          >{{ formatFare(rule37_status.all_time_high) }}</span
        >
      </p>

      <p class="mb-3 text-sm text-gray-600">
        決策期：<strong
          :class="{
            'text-green-700': rule37_status.phase === 'BUY_SIGNAL',
            'text-amber-700': rule37_status.phase === 'OBSERVING',
            'text-gray-700': rule37_status.phase === 'WAITING',
          }"
          >{{ formatDate(rule37_status.cutoff_date) }}</strong
        >
        <span v-if="rule37_status.phase === 'OBSERVING'" class="ml-1 text-xs text-gray-400">
          ({{
            Math.ceil(
              (new Date(rule37_status.cutoff_date).getTime() - new Date(today).getTime()) /
                86400000,
            )
          }}天後)
        </span>
      </p>

      <div class="mb-2 flex items-center gap-2">
        <template v-if="rule37_status.phase === 'BUY_SIGNAL'">
          <span class="text-2xl">🟢</span>

          <span class="text-xl font-bold text-green-600">購買信號</span>
        </template>

        <template v-else-if="rule37_status.phase === 'OBSERVING'">
          <span class="text-2xl">🟡</span>

          <span class="text-xl font-bold text-amber-600">觀察中</span>
        </template>

        <template v-else>
          <span class="text-2xl">⚪</span>

          <span class="text-xl font-bold text-gray-600">等待中</span>
        </template>
      </div>

      <p v-if="rule37_status.phase !== 'OBSERVING'" class="text-sm text-gray-600">
        最新：<strong>{{ formatFare(rule37_status.latest_val) }}</strong>
      </p>

      <p class="text-sm text-gray-600">
        門檻：<strong>{{ formatFare(rule37_status.history_best_val) }}</strong>
      </p>
    </div>

    <div v-else class="mb-5 rounded-lg border border-amber-200 bg-amber-50 p-6 shadow-sm">
      <p class="text-sm text-amber-800">未設定期限。設定購買期限以啟用37%規則。</p>
    </div>

    <div class="rounded-lg border bg-white shadow-sm">
      <div class="flex border-b">
        <button
          class="flex-1 py-3.5 text-center text-sm font-medium"
          :class="
            activeTab === 'table'
              ? 'border-b-2 border-blue-600 text-blue-600'
              : 'text-gray-500'
          "
          @click="switchTab('table')"
        >
          列表
        </button>

        <button
          class="flex-1 py-3.5 text-center text-sm font-medium"
          :class="
            activeTab === 'graph'
              ? 'border-b-2 border-blue-600 text-blue-600'
              : 'text-gray-500'
          "
          @click="switchTab('graph')"
        >
          圖表
        </button>
      </div>

      <!-- Table Tab -->
      <div v-show="activeTab === 'table'" class="p-5">
        <template v-if="daily_groups.length">
          <div v-for="(group, index) in daily_groups" :key="group.date" class="border-b last:border-b-0">
            <button
              class="flex w-full items-center justify-between px-5 py-3 hover:bg-gray-50"
              :class="groupBgClass(group, index)"
              @click="toggleGroup(index)"
            >
              <div class="flex flex-1 items-center gap-4 text-left">
                <div class="flex w-6 items-center justify-center">
                  <span class="text-gray-400">{{ expandedGroups.has(index) ? '▼' : '▶' }}</span>
                </div>

                <div>
                  <p class="font-semibold text-gray-900">{{ formatDateWithWeekday(group.date) }}</p>

                  <p class="text-xs text-gray-500">
                    <template v-if="group.lowest_snapshot">
                      最低：<span class="font-semibold">{{ formatFare(group.lowest_fare) }}</span>
                      <template v-if="group.lowest_snapshot.flight_number">
                        · {{ group.lowest_snapshot.flight_number }}
                      </template>
                    </template>

                    <span v-else class="text-red-500">無價格數據（僅錯誤）</span>
                  </p>
                </div>
              </div>

              <div class="shrink-0 text-right text-xs text-gray-400">
                {{ group.snapshots.length }} 班航班
              </div>
            </button>

            <div
              v-if="
                rule37_status &&
                group.date === rule37_status.cutoff_date
              "
              class="border-y border-blue-200 bg-blue-50 px-5 py-2"
            >
              <p class="text-xs font-semibold text-blue-700">
                ◆ {{ formatDate(rule37_status.cutoff_date) }} - 37%觀察期 ◆
              </p>
            </div>

            <div v-show="expandedGroups.has(index)" class="border-t">
              <table class="w-full text-sm">
                <thead class="bg-gray-50">
                  <tr>
                    <th class="px-5 py-2 text-left text-xs font-semibold text-gray-500 uppercase">航班</th>

                    <th class="px-5 py-2 text-left text-xs font-semibold text-gray-500 uppercase">起飛時間</th>

                    <th class="px-5 py-2 text-left text-xs font-semibold text-gray-500 uppercase">降落時間</th>

                    <th class="px-5 py-2 text-right text-xs font-semibold text-gray-500 uppercase">票價</th>
                  </tr>
                </thead>

                <tbody class="divide-y">
                  <tr
                    v-for="snap in group.snapshots"
                    :key="snap.id"
                    :class="snapRowClass(snap)"
                  >
                    <td class="px-5 py-2.5 font-medium">{{ snap.flight_number ?? '—' }}</td>

                    <td class="px-5 py-2.5">
                      <template v-if="snap.departure_at">
                        {{ formatTime(snap.departure_at) }}
                        <span class="text-xs text-gray-400">{{ formatTz(snap.departure_at) }}</span>
                      </template>

                      <template v-else>—</template>
                    </td>

                    <td class="px-5 py-2.5">
                      <template v-if="snap.arrival_at">
                        {{ formatTime(snap.arrival_at) }}
                        <span class="text-xs text-gray-400">{{ formatTz(snap.arrival_at) }}</span>
                      </template>

                      <template v-else>—</template>
                    </td>

                    <td class="px-5 py-2.5 text-right font-semibold" :class="snapFareClass(snap)">
                      <template v-if="snap.scrape_status === 'success' && snap.fare !== null">
                        {{ formatFare(snap.fare) }}
                        <span v-if="isAllTimeHigh(snap)" class="ml-1 text-xs">[歷史高位]</span>

                        <span v-if="isAllTimeLow(snap)" class="ml-1 text-xs">[歷史低位]</span>

                        <span v-if="isObservationBest(snap)" class="ml-1 text-xs">[37%最佳]</span>
                      </template>

                      <span v-else class="text-red-500">錯誤</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <p class="mt-4 px-1 text-xs text-gray-300">
            <span class="mr-2 inline-block h-3 w-3 rounded border border-red-300 bg-red-100"></span>歷史高位
            &ensp;
            <span
              class="mr-2 inline-block h-3 w-3 rounded border border-green-300 bg-green-100"
            ></span>歷史低位
            &ensp;
            <span
              class="mr-2 inline-block h-3 w-3 rounded border border-blue-300 bg-blue-100"
            ></span>37% 最佳選擇
          </p>
        </template>

        <div v-else class="p-12 text-center">
          <p class="text-gray-400">還沒有數據。</p>
        </div>
      </div>

      <!-- Graph Tab -->
      <div v-show="activeTab === 'graph'" class="p-5">
        <template v-if="daily_groups.length">
          <canvas ref="chartCanvas" height="80"></canvas>

          <p class="mt-3 text-xs text-gray-300">每日最低價格</p>
        </template>

        <div v-else class="p-12 text-center">
          <p class="text-gray-400">還沒有圖表數據。</p>
        </div>
      </div>
    </div>
  </AppLayout>
</template>
