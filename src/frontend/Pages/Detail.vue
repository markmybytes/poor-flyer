<script setup lang="ts">
import AppLayout from '@/Layouts/AppLayout.vue';
import { Link, router } from '@inertiajs/vue3';
import {
  CategoryScale,
  Chart,
  Legend,
  LinearScale,
  LineController,
  LineElement,
  PointElement,
  Tooltip,
} from 'chart.js';
import { onMounted, onUnmounted, ref, useTemplateRef } from 'vue';

const props = defineProps<{
  entry: {
    id: string
    origin: string
    destination: string
    flightDate: string
    deadline: string | null
    isActive: boolean
    pastDeparture: boolean
  }
  dailyGroups: {
    date: string
    lowestFare: number | null
    lowestSnapshot: { flightNumber: string | null; fare: number | null } | null
    snapshots: {
      id: string
      flightNumber: string | null
      departureAt: string | null
      arrivalAt: string | null
      fare: number | null
      scrapeStatus: string
      errorMessage: string | null
    }[]
  }[]
  today: string
  rule37Status: {
    phase: string
    cutoffDate: string
    historyBestVal: number | null
    latestVal: number | null
    allTimeHigh: number | null
    allTimeLow: number | null
  } | null
  allTimeLow: number | null
  allTimeHigh: number | null
}>()

Chart.register(
  LineController,
  LineElement,
  PointElement,
  LinearScale,
  CategoryScale,
  Legend,
  Tooltip,
)

const activeTab = ref<'table' | 'graph'>('table')
const expandedGroups = ref(new Set<number>())
const chartCanvas = useTemplateRef<HTMLCanvasElement>('chartCanvas')
let chart: Chart | null = null

const fmtFare = (f: number | null) => (f !== null ? `$${Math.round(f)}` : '—')
const fmtTime = (iso: string | null) =>
  iso
    ? new Date(iso).toLocaleTimeString('zh-HK', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
      })
    : '—'
const fmtTz = (iso: string | null) => (iso ? (iso.match(/([+-]\d{2}:\d{2}|Z)$/) || [''])[0] : '')

const toggleGroup = (i: number) =>
  expandedGroups.value.has(i) ? expandedGroups.value.delete(i) : expandedGroups.value.add(i)
const deleteEntry = () =>
  confirm('刪除此項和所有數據?') && router.post(`/entries/${props.entry.id}/delete`)

const initChart = () => {
  if (!chartCanvas.value || !props.dailyGroups.length) return
  const data = props.dailyGroups
    .filter((g) => g.lowestFare !== null)
    .map((g) => ({ date: g.date, fare: g.lowestFare! }))
    .reverse()
  chart = new Chart(chartCanvas.value, {
    type: 'line',
    data: {
      labels: data.map((d) => d.date),
      datasets: [
        {
          label: '票價 (港幣)',
          data: data.map((d) => d.fare),
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

onMounted(() => activeTab.value === 'graph' && initChart())
onUnmounted(() => chart?.destroy())

const switchTab = (t: 'table' | 'graph') => {
  activeTab.value = t
  if (t === 'graph' && !chart) setTimeout(initChart, 0)
}
</script>

<template>
  <AppLayout>
    <div class="mb-5"><Link href="/" class="text-sm text-blue-600">← 返回列表</Link></div>

    <div class="mb-5 rounded-lg border bg-white p-6 shadow-sm">
      <div class="flex items-start justify-between">
        <div>
          <h2 class="mb-1 text-3xl font-bold">{{ entry.origin }} → {{ entry.destination }}</h2>

          <p class="text-sm text-gray-600">
            航班 <strong>{{ entry.flightDate.replace(/-/g, '/') }}</strong>

            <span
              v-if="entry.pastDeparture"
              class="ml-2 rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500"
              >已過期</span
            >
          </p>

          <p v-if="entry.deadline" class="mt-1 text-sm text-gray-600">
            限期：<strong>{{ entry.deadline.replace(/-/g, '/') }}</strong>
          </p>
        </div>

        <div class="flex gap-2">
          <button
            class="rounded-lg bg-gray-100 px-3 py-1.5 text-sm text-gray-600"
            @click="router.post(`/entries/${entry.id}/toggle`)"
          >
            {{ entry.isActive ? '停用' : '啟用' }}
          </button>

          <button
            v-if="entry.flightDate >= today"
            class="rounded-lg bg-blue-600 px-3 py-1.5 text-sm text-white"
            @click="router.post(`/entries/${entry.id}/scrape`)"
          >
            擷取最新價格
          </button>

          <button
            class="rounded-lg bg-red-50 px-3 py-1.5 text-sm text-red-600"
            @click="deleteEntry"
          >
            刪除
          </button>
        </div>
      </div>
    </div>

    <div v-if="rule37Status" class="mb-5 rounded-lg border bg-white p-6 shadow-sm">
      <p class="mb-3 text-xs font-semibold tracking-widest text-gray-400 uppercase">
        37% 法則 | 最低：<span class="text-green-700">{{ fmtFare(rule37Status.allTimeLow) }}</span>

        | 最高：<span class="text-red-700">{{ fmtFare(rule37Status.allTimeHigh) }}</span>
      </p>

      <p class="mb-3 text-sm text-gray-600">
        決策期：<strong
          :class="{
            'text-green-700': rule37Status.phase === 'BUY_SIGNAL',
            'text-amber-700': rule37Status.phase === 'OBSERVING',
            'text-gray-700': rule37Status.phase === 'WAITING',
          }"
          >{{ rule37Status.cutoffDate.replace(/-/g, '/') }}</strong
        >

        <span v-if="rule37Status.phase === 'OBSERVING'" class="ml-1 text-xs text-gray-400"
          >({{
            Math.ceil(
              (new Date(rule37Status.cutoffDate).getTime() - new Date(today).getTime()) / 86400000,
            )
          }}天後)</span
        >
      </p>

      <div class="mb-2 flex items-center gap-2">
        <template v-if="rule37Status.phase === 'BUY_SIGNAL'"
          ><span class="text-2xl">🟢</span
          >

          <span class="text-xl font-bold text-green-600">購買信號</span></template
        >

        <template v-else-if="rule37Status.phase === 'OBSERVING'"
          ><span class="text-2xl">🟡</span
          >

          <span class="text-xl font-bold text-amber-600">觀察中</span></template
        >

        <template v-else
          ><span class="text-2xl">⚪</span
          >

          <span class="text-xl font-bold text-gray-600">等待中</span></template
        >
      </div>

      <p v-if="rule37Status.phase !== 'OBSERVING'" class="text-sm text-gray-600">
        最新：<strong>{{ fmtFare(rule37Status.latestVal) }}</strong>
      </p>

      <p class="text-sm text-gray-600">
        門檻：<strong>{{ fmtFare(rule37Status.historyBestVal) }}</strong>
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
            activeTab === 'table' ? 'border-b-2 border-blue-600 text-blue-600' : 'text-gray-500'
          "
          @click="switchTab('table')"
        >
          列表
        </button>

        <button
          class="flex-1 py-3.5 text-center text-sm font-medium"
          :class="
            activeTab === 'graph' ? 'border-b-2 border-blue-600 text-blue-600' : 'text-gray-500'
          "
          @click="switchTab('graph')"
        >
          圖表
        </button>
      </div>

      <div v-show="activeTab === 'table'" class="p-5">
        <template v-if="dailyGroups.length">
          <div
            v-for="(group, index) in dailyGroups"
            :key="group.date"
            class="border-b last:border-b-0"
          >
            <button
              class="flex w-full items-center justify-between px-5 py-3 hover:bg-gray-50"
              :class="{
                'bg-green-50': group.lowestSnapshot?.fare === allTimeLow,
                'bg-blue-50':
                  rule37Status &&
                  group.date >= rule37Status.cutoffDate &&
                  group.lowestSnapshot?.fare === rule37Status.historyBestVal,
              }"
              @click="toggleGroup(index)"
            >
              <div class="flex flex-1 items-center gap-4 text-left">
                <div class="flex w-6 items-center justify-center">
                  <span class="text-gray-400">{{ expandedGroups.has(index) ? '▼' : '▶' }}</span>
                </div>

                <div>
                  <p class="font-semibold text-gray-900">
                    {{ group.date.replace(/-/g, '/') }} ({{
                      ['日', '一', '二', '三', '四', '五', '六'][new Date(group.date).getDay()]
                    }})
                  </p>

                  <p class="text-xs text-gray-500">
                    <template v-if="group.lowestSnapshot"
                      >最低：<span class="font-semibold">{{ fmtFare(group.lowestFare) }}</span
                      >

                      <template v-if="group.lowestSnapshot.flightNumber">
                        · {{ group.lowestSnapshot.flightNumber }}</template
                      ></template
                    >

                    <span v-else class="text-red-500">無價格數據（僅錯誤）</span>
                  </p>
                </div>
              </div>

              <div class="shrink-0 text-right text-xs text-gray-400">
                {{ group.snapshots.length }} 班航班
              </div>
            </button>

            <div
              v-if="rule37Status && group.date === rule37Status.cutoffDate"
              class="border-y border-blue-200 bg-blue-50 px-5 py-2"
            >
              <p class="text-xs font-semibold text-blue-700">
                ◆ {{ rule37Status.cutoffDate.replace(/-/g, '/') }} - 37%觀察期 ◆
              </p>
            </div>

            <div v-show="expandedGroups.has(index)" class="border-t">
              <table class="w-full text-sm">
                <thead class="bg-gray-50">
                  <tr>
                    <th class="px-5 py-2 text-left text-xs font-semibold text-gray-500 uppercase">
                      航班
                    </th>

                    <th class="px-5 py-2 text-left text-xs font-semibold text-gray-500 uppercase">
                      起飛時間
                    </th>

                    <th class="px-5 py-2 text-left text-xs font-semibold text-gray-500 uppercase">
                      降落時間
                    </th>

                    <th class="px-5 py-2 text-right text-xs font-semibold text-gray-500 uppercase">
                      票價
                    </th>
                  </tr>
                </thead>

                <tbody class="divide-y">
                  <tr
                    v-for="snap in group.snapshots"
                    :key="snap.id"
                    :class="{
                      'bg-gray-50 text-gray-600': snap.scrapeStatus === 'error',
                      'bg-red-50 text-red-700':
                        snap.scrapeStatus === 'success' && snap.fare === allTimeHigh,
                      'bg-green-50 text-green-700':
                        snap.scrapeStatus === 'success' && snap.fare === allTimeLow,
                      'bg-blue-50 text-blue-700':
                        rule37Status &&
                        snap.scrapeStatus === 'success' &&
                        snap.fare === rule37Status.historyBestVal &&
                        snap.departureAt?.slice(0, 10) >= rule37Status.cutoffDate,
                    }"
                  >
                    <td class="px-5 py-2.5 font-medium">{{ snap.flightNumber ?? '—' }}</td>

                    <td class="px-5 py-2.5">
                      {{ fmtTime(snap.departureAt) }}
                      <span class="text-xs text-gray-400">{{ fmtTz(snap.departureAt) }}</span>
                    </td>

                    <td class="px-5 py-2.5">
                      {{ fmtTime(snap.arrivalAt) }}
                      <span class="text-xs text-gray-400">{{ fmtTz(snap.arrivalAt) }}</span>
                    </td>

                    <td class="px-5 py-2.5 text-right font-semibold">
                      <template v-if="snap.scrapeStatus === 'success' && snap.fare !== null">
                        {{ fmtFare(snap.fare) }}
                        <span v-if="snap.fare === allTimeHigh" class="ml-1 text-xs"
                          >[歷史高位]</span
                        >

                        <span v-if="snap.fare === allTimeLow" class="ml-1 text-xs">[歷史低位]</span>

                        <span
                          v-if="
                            rule37Status &&
                            snap.fare === rule37Status.historyBestVal &&
                            snap.departureAt?.slice(0, 10) >= rule37Status.cutoffDate
                          "
                          class="ml-1 text-xs"
                          >[37%最佳]</span
                        >
                      </template>

                      <span v-else class="text-red-500">錯誤</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <p class="mt-4 px-1 text-xs text-gray-300">
            <span class="mr-2 inline-block h-3 w-3 rounded border border-red-300 bg-red-100"></span
            >
歷史高位 &ensp;
            <span
              class="mr-2 inline-block h-3 w-3 rounded border border-green-300 bg-green-100"
            ></span
            >
歷史低位 &ensp;
            <span
              class="mr-2 inline-block h-3 w-3 rounded border border-blue-300 bg-blue-100"
            ></span
            >37% 最佳選擇
          </p>
        </template>

        <div v-else class="p-12 text-center"><p class="text-gray-400">還沒有數據。</p></div>
      </div>

      <div v-show="activeTab === 'graph'" class="p-5">
        <template v-if="dailyGroups.length">
          <canvas ref="chartCanvas" height="80"></canvas>

          <p class="mt-3 text-xs text-gray-300">每日最低價格</p>
        </template>

        <div v-else class="p-12 text-center"><p class="text-gray-400">還沒有圖表數據。</p></div>
      </div>
    </div>
  </AppLayout>
</template>
