<script setup lang="ts">
import AppLayout from '@/Layouts/AppLayout.vue'
import type { FareSnapshot, Itinerary } from '@/types'
import { fmtDate, fmtFare, fmtItineraryName, fmtTime, fmtTz } from '@/utils'
import { router } from '@inertiajs/vue3'
import Chart from 'chart.js/auto'
import { computed, nextTick, onMounted, onUnmounted, ref, useTemplateRef, watch } from 'vue'
import { useToast } from 'vue-toast-notification'

const props = defineProps<{ itinerary: Itinerary }>()
const toast = useToast()

const chartCanvas = useTemplateRef<HTMLCanvasElement>('chartCanvas')
const activeTab = ref('0')
const expandedGroups = ref(new Set<number>())
const loading = ref<string | null>(null)
const detailPanel = ref(props.itinerary.deadline ? 'analysis' : 'summary')

let chart: Chart | null = null
const today = new Date().toISOString().split('T')[0]

const ruleAnalysis = computed(() => props.itinerary.rule37Analysis)
const isSingleTrip = computed(() => props.itinerary.tripType === 'SINGLE')
const selectedFlight = computed(
  () => props.itinerary.flights[parseInt(activeTab.value, 10)] || props.itinerary.flights[0],
)

const legMinMax = computed(() => {
  const fares = (selectedFlight.value?.fareSnapshots || [])
    .filter((s) => s.scrapeStatus === 'success' && s.fare !== null)
    .map((s) => s.fare as number)

  if (!fares.length) return { min: null, max: null }
  const min = Math.min(...fares),
    max = Math.max(...fares)
  return min === max ? { min: null, max: null } : { min, max }
})

const dailyGroups = computed(() => {
  const byDate = (selectedFlight.value?.fareSnapshots || []).reduce(
    (acc, s) => {
      const d = s.createdAt.split('T')[0]
      ;(acc[d] ??= []).push(s)
      return acc
    },
    {} as Record<string, FareSnapshot[]>,
  )

  return Object.entries(byDate)
    .sort(([a], [b]) => b.localeCompare(a))
    .map(([date, snaps]) => {
      const low = snaps
        .filter((s) => s.scrapeStatus === 'success' && s.fare != null)
        .sort((a, b) => (a.fare as number) - (b.fare as number))[0]
      return {
        date,
        lowestFare: low?.fare ?? null,
        lowestSnapshot: low ? { flightNumber: low.flightNumber, fare: low.fare } : null,
        snapshots: snaps.sort((a, b) => b.createdAt.localeCompare(a.createdAt)),
      }
    })
})

const runAction = async (action: 'toggle' | 'scrape' | 'delete') => {
  if (action === 'delete' && !confirm('確認刪除此航班追蹤？')) return
  loading.value = action

  const opts: RequestInit = {
    method: action === 'toggle' ? 'PATCH' : action === 'scrape' ? 'POST' : 'DELETE',
  }
  if (action === 'toggle') {
    opts.headers = { 'Content-Type': 'application/json' }
    opts.body = JSON.stringify({ is_active: !props.itinerary.isActive })
  }

  try {
    const res = await fetch(
      `/api/flights/${props.itinerary.id}${action === 'scrape' ? '/scrape' : ''}`,
      opts,
    )
    if (!res.ok) throw new Error()
    if (action === 'delete') router.visit('/flights/')
    else router.reload()
  } catch {
    toast.error(
      `${action === 'scrape' ? '擷取' : action === 'delete' ? '刪除' : '操作'}失敗，請稍後再試`,
    )
  } finally {
    loading.value = null
  }
}

function initChart() {
  if (!chartCanvas.value || !props.itinerary.flights.length) return
  if (chart) chart.destroy()

  const labels = [
    ...new Set([
      ...props.itinerary.flights.flatMap((f) =>
        (f.fareSnapshots || []).map((s) => s.createdAt.split('T')[0]),
      ),
      ...(ruleAnalysis.value?.cutoffDate ? [ruleAnalysis.value.cutoffDate] : []),
    ]),
  ]
    .filter(Boolean)
    .sort()

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const datasets: any[] = []

  if (!isSingleTrip.value && props.itinerary.statistics) {
    datasets.push({
      label: '總價 (每日最低)',
      data: labels.map((date) => {
        const totals = props.itinerary.flights.map((f) => {
          const fares = (f.fareSnapshots || [])
            .filter(
              (s) =>
                s.createdAt.startsWith(date) && s.scrapeStatus === 'success' && s.fare !== null,
            )
            .map((s) => s.fare as number)
          return fares.length ? Math.min(...fares) : null
        })
        return totals.includes(null) ? null : totals.reduce((a, b) => a! + b!, 0)
      }),
      borderColor: '#ff9800',
      backgroundColor: 'rgba(255, 152, 0, 0.1)',
      borderWidth: 3,
      tension: 0.4,
      fill: false,
      spanGaps: true,
    })
  }

  props.itinerary.flights.forEach((f, idx) => {
    const dataObj = (f.fareSnapshots || [])
      .filter((s) => s.scrapeStatus === 'success' && s.fare !== null)
      .reduce(
        (acc, s) => {
          const d = s.createdAt.split('T')[0]
          if (!acc[d] || s.fare! < acc[d]) acc[d] = s.fare!
          return acc
        },
        {} as Record<string, number>,
      )

    datasets.push({
      label: isSingleTrip.value ? '最低票價' : `${f.origin} → ${f.destination}`,
      data: labels.map((l) => dataObj[l] ?? null),
      borderColor: isSingleTrip.value ? '#2563eb' : `hsl(${(idx * 137.5) % 360}, 70%, 50%)`,
      backgroundColor: isSingleTrip.value ? 'rgba(37, 99, 235, 0.1)' : 'transparent',
      borderWidth: 2.5,
      tension: 0.4,
      fill: isSingleTrip.value,
      spanGaps: true,
    })
  })

  if (ruleAnalysis.value?.historyBestVal) {
    datasets.push({
      label: 'Buying Threshold',
      data: labels.map(() => ruleAnalysis.value!.historyBestVal),
      borderColor: 'rgba(255, 99, 132, 0.8)',
      borderDash: [5, 5],
      borderWidth: 2,
      tension: 0,
      spanGaps: true,
      pointRadius: 0,
    })
  }

  chart = new Chart(chartCanvas.value, {
    type: 'line',
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: !isSingleTrip.value },
        tooltip: { padding: 12, cornerRadius: 8 },
      },
      scales: { y: { grid: { color: '#f3f4f6' } }, x: { grid: { display: false } } },
      interaction: { intersect: false, mode: 'index' },
    },
  })
}

function switchTab(t: string) {
  activeTab.value = t
  if (t === 'graph') nextTick(() => initChart())
}

watch(activeTab, (val) => {
  expandedGroups.value.clear()
  if (val === 'graph') initChart()
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
              <h3 class="flex items-center gap-2 text-base font-bold text-base-content">
                {{ fmtItineraryName(itinerary) }}
              </h3>

              <p class="mt-0.5 text-sm font-medium text-base-content/60">
                出發日期：{{ fmtDate(itinerary.flights[0].flightDate) }}
                <span v-if="itinerary.deadline" class="mx-2 text-base-content/30">|</span>

                <span v-if="itinerary.deadline">限期：{{ fmtDate(itinerary.deadline) }}</span>
              </p>
            </div>

            <div class="flex shrink-0 flex-wrap gap-2">
              <span v-if="itinerary.isActive" class="badge badge-soft px-3 py-3 badge-success">
                <span class="status status-success"></span> 追蹤中
              </span>

              <span v-else class="badge badge-soft px-3 py-3 badge-warning">已暫停</span>
            </div>
          </div>
        </div>

        <div class="flex justify-end px-6 py-5">
          <div class="join gap-2">
            <button
              class="btn join-item btn-sm"
              :disabled="loading === 'toggle'"
              @click="runAction('toggle')"
            >
              <span v-if="loading === 'toggle'" class="loading loading-xs loading-spinner"></span>
              {{ itinerary.isActive ? '停止追蹤' : '開啟追蹤' }}
            </button>

            <button
              class="btn join-item btn-sm btn-primary"
              :disabled="loading === 'scrape'"
              @click="runAction('scrape')"
            >
              <span v-if="loading === 'scrape'" class="loading loading-xs loading-spinner"></span>
              {{ loading === 'scrape' ? '擷取中...' : '擷取最新價格' }}
            </button>

            <button
              class="btn join-item btn-soft btn-sm btn-error"
              :disabled="loading === 'delete'"
              @click="runAction('delete')"
            >
              <span v-if="loading === 'delete'" class="loading loading-xs loading-spinner"></span>
              刪除
            </button>
          </div>
        </div>
      </div>
    </div>

    <div
      class="tracker-panel mb-8 rounded-lg border px-6 py-6"
      :class="{
        'bg-success/10': detailPanel === 'analysis' && ruleAnalysis?.phase === 'BUY_SIGNAL',
        'bg-info/10': detailPanel === 'analysis' && ruleAnalysis?.phase === 'WAITING',
        'bg-neutral/10': detailPanel === 'analysis' && ruleAnalysis?.phase === 'OBSERVING',
      }"
    >
      <div class="join mb-5">
        <button
          class="btn join-item btn-xs"
          :class="detailPanel === 'analysis' ? 'btn-neutral' : 'opacity-50 btn-ghost'"
          @click="detailPanel = 'analysis'"
        >
          購買時機分析
        </button>

        <button
          class="btn join-item btn-xs"
          :class="detailPanel === 'summary' ? 'btn-neutral' : 'opacity-50 btn-ghost'"
          @click="detailPanel = 'summary'"
        >
          價格摘要
        </button>
      </div>

      <div class="grid">
        <div
          class="col-start-1 row-start-1 transition-opacity duration-150"
          :class="detailPanel !== 'analysis' ? 'pointer-events-none invisible' : ''"
        >
          <div v-if="itinerary.deadline && ruleAnalysis?.phase" class="space-y-4">
            <div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div class="flex items-center gap-3">
                <template v-if="ruleAnalysis.phase === 'BUY_SIGNAL'">
                  <span class="status status-lg status-success"></span>

                  <span class="text-lg font-bold text-success">購買信號 (最佳時機)</span>
                </template>

                <template v-else-if="ruleAnalysis.phase === 'OBSERVING'">
                  <span class="status status-lg status-neutral"></span>

                  <span class="text-lg font-bold text-neutral">觀察期</span>

                  <span class="badge px-2 py-1 text-xs font-medium badge-warning">
                    {{
                      Math.ceil(
                        (new Date(ruleAnalysis.cutoffDate).getTime() - new Date(today).getTime()) /
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
                  {{ fmtDate(ruleAnalysis.cutoffDate) }}
                </p>

                <p>
                  <span class="font-medium">門檻：</span> {{ fmtFare(ruleAnalysis.historyBestVal) }}
                </p>
              </div>
            </div>

            <div class="grid grid-cols-2 gap-3">
              <div class="rounded-lg bg-base-100/60 px-4 py-3">
                <p class="text-xs font-bold tracking-widest uppercase opacity-55">總價 (最新)</p>

                <p class="mt-1 text-base font-bold">
                  {{ fmtFare(itinerary.statistics?.latestVal ?? null) }}
                </p>
              </div>

              <div class="rounded-lg bg-base-100/60 px-4 py-3">
                <p class="text-xs font-bold tracking-widest uppercase opacity-55">歷史總價最低</p>

                <p class="mt-1 text-base font-bold text-success">
                  {{ fmtFare(itinerary.statistics?.allTimeLow ?? null) }}
                </p>
              </div>
            </div>
          </div>

          <div v-else-if="itinerary.deadline" class="py-4 text-center">
            <p class="text-sm font-medium text-base-content/60">
              數據不足，尚無法分析最佳購買時機。
            </p>
          </div>

          <div v-else class="py-4 text-center">
            <p class="text-sm font-medium text-base-content/60">
              未設定購票限期，無法分析購買時機。
            </p>
          </div>
        </div>

        <div
          class="col-start-1 row-start-1 transition-opacity duration-150"
          :class="detailPanel !== 'summary' ? 'pointer-events-none invisible' : ''"
        >
          <div class="stats w-full stats-vertical rounded-lg bg-base-200/60 lg:stats-horizontal">
            <div class="stat px-5 py-4">
              <div class="stat-title text-base-content/55">最新票價</div>

              <div class="stat-value text-2xl text-primary">
                {{ fmtFare(itinerary.statistics?.latestVal ?? null) }}
              </div>
            </div>

            <div class="stat px-5 py-4">
              <div class="stat-title text-base-content/55">歷史最低</div>

              <div class="stat-value text-2xl text-success">
                {{ fmtFare(itinerary.statistics?.allTimeLow ?? null) }}
              </div>
            </div>

            <div class="stat px-5 py-4">
              <div class="stat-title text-base-content/55">歷史最高</div>

              <div class="stat-value text-2xl text-error">
                {{ fmtFare(itinerary.statistics?.allTimeHigh ?? null) }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="tracker-panel card rounded-lg">
      <div class="card-body p-4 md:p-6">
        <div class="tabs-box tabs flex-nowrap overflow-x-auto bg-base-200/70 p-1 whitespace-nowrap">
          <button
            v-if="isSingleTrip"
            class="tab h-12 shrink-0 px-6 text-sm font-bold"
            :class="activeTab === '0' ? 'tab-active' : ''"
            @click="switchTab('0')"
          >
            詳細數據列表
          </button>

          <template v-else>
            <button
              v-for="(f, i) in itinerary.flights"
              :key="f.id"
              class="tab h-12 shrink-0 px-6 text-sm font-bold"
              :class="activeTab === String(i) ? 'tab-active' : ''"
              @click="switchTab(String(i))"
            >
              {{ f.origin }} → {{ f.destination }}
            </button>
          </template>

          <button
            class="tab h-12 shrink-0 px-6 text-sm font-bold"
            :class="activeTab === 'graph' ? 'tab-active' : ''"
            @click="switchTab('graph')"
          >
            價格趨勢圖表
          </button>
        </div>

        <div v-show="activeTab !== 'graph'" class="pt-5">
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
                  'bg-success/10':
                    legMinMax.min !== null &&
                    group.snapshots.some((s) => s.fare === legMinMax.min) &&
                    !group.snapshots.some((s) => s.fare === legMinMax.max),
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

                        <template v-if="group.lowestSnapshot.flightNumber"
                          >· {{ group.lowestSnapshot.flightNumber }}</template
                        >
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
                v-if="ruleAnalysis?.phase && group.date === ruleAnalysis.cutoffDate"
                class="border-y border-warning/20 bg-warning/15 px-5 py-1.5 text-center"
              >
                <p class="text-[11px] font-bold tracking-widest text-warning-content">
                  ▴ 購買時機分析 · 決策期 ▴
                </p>
              </div>

              <div
                v-show="expandedGroups.has(index)"
                class="collapse-content border-t border-base-300/70 bg-base-200/40 px-5 py-4"
              >
                <div
                  class="overflow-x-auto rounded-[1.25rem] border border-base-300/70 bg-base-100"
                >
                  <table class="table w-full table-zebra text-sm">
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
                        v-for="snap in group.snapshots"
                        :key="snap.id"
                        :class="[snap.scrapeStatus === 'error' ? 'bg-error/10' : '']"
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
                            <div
                              class="flex flex-col items-end justify-end gap-2 sm:flex-row sm:items-center"
                            >
                              <div class="flex flex-wrap justify-end gap-1">
                                <span
                                  v-if="snap.fare === legMinMax.min"
                                  class="badge badge-soft badge-xs badge-success"
                                  >[歷史低位]</span
                                >

                                <span
                                  v-if="snap.fare === legMinMax.max"
                                  class="badge badge-soft badge-xs badge-error"
                                  >[歷史高位]</span
                                >
                              </div>

                              <span>{{ fmtFare(snap.fare, snap.currency) }}</span>
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
          <template v-if="itinerary.flights.length">
            <div
              class="rounded-3xl bg-base-100 p-4 md:p-6"
              style="height: 400px; position: relative"
            >
              <canvas ref="chartCanvas"></canvas>
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
