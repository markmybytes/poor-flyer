<script setup lang="ts">
import AppLayout from '@/Layouts/AppLayout.vue'
import type { FareSnapshot, Flight } from '@/types'
import { fmtDate, fmtFare, fmtTime, fmtTz, getFlightStats } from '@/utils'
import { router } from '@inertiajs/vue3'
import Chart from 'chart.js/auto'
import { computed, nextTick, onMounted, onUnmounted, ref, useTemplateRef, watch } from 'vue'
import { useToast } from 'vue-toast-notification'

const props = defineProps<{ flight: Flight }>()

const toast = useToast()

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
  fetch(`/api/flights/${props.flight.id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ is_active: !props.flight.isActive }),
  })
    .then((res) => {
      if (res.ok) {
        router.reload()
      } else {
        toast.error('操作失敗，請稍後再試')
      }
    })
    .catch(() => toast.error('操作失敗，請稍後再試'))
    .finally(() => {
      loading.value.loading = null
    })
}

function scrapeEntry() {
  loading.value.loading = 'scrape'
  fetch(`/api/flights/${props.flight.id}/scrape`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  })
    .then((res) => {
      if (res.ok) {
        router.reload()
      } else {
        toast.error('擷取失敗，請稍後再試')
      }
    })
    .catch(() => toast.error('擷取失敗，請稍後再試'))
    .finally(() => {
      loading.value.loading = null
    })
}

function deleteEntry() {
  if (!confirm('確認刪除此航班追蹤？')) return
  loading.value.loading = 'delete'
  fetch(`/api/flights/${props.flight.id}`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
  })
    .then((res) => {
      if (res.ok) {
        router.visit('/flights/')
      } else {
        toast.error('刪除失敗，請稍後再試')
      }
    })
    .catch(() => toast.error('刪除失敗，請稍後再試'))
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
    <div class="tracker-panel card mb-6 rounded-lg">
      <div class="card-body p-0">
        <div class="border-b border-base-300/70 px-6 py-5">
          <div class="flex items-start justify-between gap-4">
            <div>
              <h3 class="text-base font-bold text-base-content">
                {{ flight.origin }} → {{ flight.destination }}
              </h3>

              <p class="mt-0.5 text-sm font-medium text-base-content/60">
                出發日期：{{ fmtDate(flight.flightDate) }}
                <span v-if="flight.deadline" class="mx-2 text-base-content/30">|</span>

                <span v-if="flight.deadline">限期：{{ fmtDate(flight.deadline) }}</span>
              </p>
            </div>

            <div class="flex shrink-0 flex-wrap gap-2">
              <span v-if="flight.isActive" class="badge badge-soft px-3 py-3 badge-success">
                <span class="status status-success"></span>
                追蹤中
              </span>

              <span v-else class="badge badge-soft px-3 py-3 badge-warning">已暫停</span>
            </div>
          </div>
        </div>

        <div class="flex justify-end px-6 py-5">
          <div class="join gap-2">
            <button
              class="btn join-item btn-sm"
              :disabled="loading.loading === 'toggle'"
              @click="toggleEntry"
            >
              <span
                v-if="loading.loading === 'toggle'"
                class="loading loading-xs loading-spinner"
              ></span>
              {{ flight.isActive ? '停止追蹤' : '開啟追蹤' }}
            </button>

            <button
              class="btn join-item btn-sm btn-primary"
              :disabled="loading.loading === 'scrape'"
              @click="scrapeEntry"
            >
              <span
                v-if="loading.loading === 'scrape'"
                class="loading loading-xs loading-spinner"
              ></span>
              {{ loading.loading === 'scrape' ? '擷取中...' : '擷取最新價格' }}
            </button>

            <button
              class="btn join-item btn-soft btn-sm btn-error"
              :disabled="loading.loading === 'delete'"
              @click="deleteEntry"
            >
              <span
                v-if="loading.loading === 'delete'"
                class="loading loading-xs loading-spinner"
              ></span>
              刪除
            </button>
          </div>
        </div>
      </div>
    </div>

    <div
      class="tracker-panel mb-8 rounded-lg border px-6 py-6"
      :class="{
        'bg-success/10': flight.rule37Analysis?.phase === 'BUY_SIGNAL',
        'bg-info/10': flight.rule37Analysis?.phase === 'WAITING',
        'bg-neutral/10': flight.rule37Analysis?.phase === 'OBSERVING',
        'border-dashed bg-neutral/5': !flight.rule37Analysis?.latestVal,
      }"
    >
      <div
        v-if="flight.rule37Analysis && flight.rule37Analysis.latestVal !== null"
        class="space-y-4"
      >
        <p class="text-xs font-bold tracking-widest uppercase opacity-60">37% 法則指標</p>

        <div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div class="flex items-center gap-3">
            <template v-if="flight.rule37Analysis.phase === 'BUY_SIGNAL'">
              <span class="status status-lg status-success"></span>

              <span class="text-lg font-bold text-success">購買信號 (最佳時機)</span>
            </template>

            <template v-else-if="flight.rule37Analysis.phase === 'OBSERVING'">
              <span class="status status-lg status-neutral"></span>

              <span class="text-lg font-bold text-neutral">觀察期</span>

              <span class="badge px-2 py-1 text-xs font-medium badge-warning">
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
              <span class="status status-lg status-info"></span>

              <span class="text-lg font-bold text-info">等待中</span>
            </template>
          </div>

          <div class="space-y-1 text-xs text-base-content/70">
            <p>
              <span class="font-medium">決策期開始：</span>
              {{ fmtDate(flight.rule37Analysis.cutoffDate) }}
            </p>

            <p>
              <span class="font-medium">門檻：</span>
              {{ fmtFare(flight.rule37Analysis.historyBestVal) }}
            </p>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div class="rounded-lg bg-base-100/60 px-4 py-3">
            <p class="text-xs font-bold tracking-widest uppercase opacity-55">最新票價</p>

            <p class="mt-1 text-base font-bold">{{ fmtFare(flight.rule37Analysis.latestVal) }}</p>
          </div>

          <div class="rounded-lg bg-base-100/60 px-4 py-3">
            <p class="text-xs font-bold tracking-widest uppercase opacity-55">歷史最低</p>

            <p class="mt-1 text-base font-bold text-success">
              {{ fmtFare(flight.rule37Analysis.allTimeLow) }}
            </p>
          </div>
        </div>
      </div>

      <div v-else-if="flight.rule37Analysis" class="text-center">
        <p class="text-sm font-medium text-base-content/60">未有數據，未能計算 37% 法則指標。</p>
      </div>

      <div v-else class="text-center">
        <p class="text-sm font-medium text-base-content/60">
          未設定購買限期，無法計算 37% 最佳則指標。
        </p>
      </div>
    </div>

    <div class="tracker-panel card rounded-lg">
      <div class="card-body p-4 md:p-6">
        <div class="tabs-box tabs bg-base-200/70 p-1">
          <button
            class="tab h-12 flex-1 text-sm font-bold"
            :class="activeTab === 'table' ? 'tab-active' : ''"
            @click="switchTab('table')"
          >
            詳細數據列表
          </button>

          <button
            class="tab h-12 flex-1 text-sm font-bold"
            :class="activeTab === 'graph' ? 'tab-active' : ''"
            @click="switchTab('graph')"
          >
            價格趨勢圖表
          </button>
        </div>

        <div v-show="activeTab === 'table'" class="pt-5">
          <template v-if="dailyGroups.length">
            <div
              v-for="(group, index) in dailyGroups"
              :key="group.date"
              class="collapse-plus collapse mb-3 border border-base-300/70 bg-base-100 last:mb-0"
              :class="expandedGroups.has(index) ? 'collapse-open' : 'collapse-close'"
            >
              <button
                class="collapse-title flex w-full items-center justify-between pr-14 pl-5 text-left transition-colors hover:bg-base-200/40"
                :class="{
                  'bg-success/10': group.lowestSnapshot?.fare === flightStats.lowest,
                  'bg-primary/10':
                    flight.rule37Analysis?.phase &&
                    group.date >= flight.rule37Analysis.cutoffDate &&
                    group.lowestSnapshot?.fare === flight.rule37Analysis.historyBestVal,
                }"
                @click="
                  expandedGroups.has(index)
                    ? expandedGroups.delete(index)
                    : expandedGroups.add(index)
                "
              >
                <div class="flex flex-1 items-center gap-4">
                  <div>
                    <p class="leading-tight font-bold text-base-content">
                      {{ fmtDate(group.date) }}
                      <span class="ml-1 text-xs font-medium text-base-content/55">
                        （{{
                          ['日', '一', '二', '三', '四', '五', '六'][new Date(group.date).getDay()]
                        }}）
                      </span>
                    </p>

                    <p class="text-xs font-medium text-base-content/60">
                      <template v-if="group.lowestSnapshot">
                        當日最低：<span class="font-bold text-base-content">{{
                          fmtFare(group.lowestFare)
                        }}</span>

                        <template v-if="group.lowestSnapshot.flightNumber">
                          · {{ group.lowestSnapshot.flightNumber }}
                        </template>
                      </template>

                      <span v-else class="text-error">無有效價格數據</span>
                    </p>
                  </div>
                </div>

                <div
                  class="badge shrink-0 badge-outline px-3 py-3 text-xs font-semibold badge-primary"
                >
                  {{ group.snapshots.length }} 筆紀錄
                </div>
              </button>

              <div
                v-if="
                  flight.rule37Analysis?.phase && group.date === flight.rule37Analysis.cutoffDate
                "
                class="border-y border-warning/20 bg-warning/15 px-5 py-1.5 text-center"
              >
                <p class="text-[11px] font-bold tracking-widest text-warning-content">
                  ▴ 37% 法則決策期 ▴
                </p>
              </div>

              <div
                v-show="expandedGroups.has(index)"
                class="collapse-content border-t border-base-300/70 bg-base-200/40 px-5 py-4"
              >
                <div
                  class="overflow-x-auto rounded-[1.25rem] border border-base-300/70 bg-base-100"
                >
                  <table class="table table-zebra text-sm">
                    <thead>
                      <tr>
                        <th class="text-xs font-bold tracking-wider text-base-content/55 uppercase">
                          航班編號
                        </th>

                        <th class="text-xs font-bold tracking-wider text-base-content/55 uppercase">
                          起飛時間
                        </th>

                        <th class="text-xs font-bold tracking-wider text-base-content/55 uppercase">
                          降落時間
                        </th>

                        <th
                          class="text-right text-xs font-bold tracking-wider text-base-content/55 uppercase"
                        >
                          票價
                        </th>
                      </tr>
                    </thead>

                    <tbody>
                      <tr
                        v-for="snap in group.snapshots.toSorted(
                          (a, b) => a.flightNumber?.localeCompare(b.flightNumber ?? '') ?? 0,
                        )"
                        :key="snap.id"
                        :class="{ 'bg-error/10': snap.scrapeStatus === 'error' }"
                      >
                        <td class="font-semibold text-base-content">
                          {{ snap.flightNumber ?? '—' }}
                        </td>

                        <td class="text-base-content/70">
                          {{ fmtTime(snap.departureAt) }}
                          <span class="text-[10px] text-base-content/40">{{
                            fmtTz(snap.departureAt)
                          }}</span>
                        </td>

                        <td class="text-base-content/70">
                          {{ fmtTime(snap.arrivalAt) }}
                          <span class="text-[10px] text-base-content/40">{{
                            fmtTz(snap.arrivalAt)
                          }}</span>
                        </td>

                        <td class="text-right font-bold text-base-content">
                          <template v-if="snap.scrapeStatus === 'success' && snap.fare !== null">
                            <div class="flex items-center justify-end gap-2">
                              <div class="flex gap-1">
                                <span
                                  v-if="snap.fare === flightStats.lowest"
                                  class="badge badge-soft badge-xs badge-success"
                                >
                                  歷史低位
                                </span>

                                <span
                                  v-if="
                                    flight.rule37Analysis?.phase &&
                                    snap.fare === flight.rule37Analysis.historyBestVal &&
                                    (snap.departureAt?.slice(0, 10) ?? '') >=
                                      flight.rule37Analysis.cutoffDate
                                  "
                                  class="badge badge-soft badge-xs badge-primary"
                                >
                                  最佳選擇
                                </span>
                              </div>

                              <span>{{ fmtFare(snap.fare) }}</span>
                            </div>
                          </template>

                          <span v-else class="text-xs text-error">擷取失敗</span>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </template>

          <div v-else class="hero py-16 text-center">
            <div class="hero-content">
              <p class="font-medium text-base-content/50">暫無價格數據。</p>
            </div>
          </div>
        </div>

        <div v-show="activeTab === 'graph'" class="pt-5">
          <template v-if="dailyGroups.length">
            <div class="rounded-3xl bg-base-100 p-4 md:p-6">
              <canvas ref="chartCanvas" height="100"></canvas>
            </div>
          </template>

          <div v-else class="hero py-16 text-center">
            <div class="hero-content">
              <p class="font-medium text-base-content/50">暫無趨勢數據。</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>
