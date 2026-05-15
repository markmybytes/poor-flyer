<script setup lang="ts">
import AppLayout from '@/Layouts/AppLayout.vue'
import type { Flight } from '@/types'
import { fmtDate, fmtFare, getFlightStats } from '@/utils'
import { Link } from '@inertiajs/vue3'
import { computed } from 'vue'

const props = defineProps<{ flights: Flight[] }>()

const summary = computed(() => {
  const active = props.flights.filter((flight) => flight.isActive).length
  const buySignals = props.flights.filter(
    (flight) => flight.rule37Analysis?.phase === 'BUY_SIGNAL',
  ).length
  const lowestFare = props.flights
    .flatMap((flight) => flight.fareSnapshots ?? [])
    .filter((snapshot) => snapshot.scrapeStatus === 'success' && snapshot.fare !== null)
    .reduce<number | null>((lowest, snapshot) => {
      if (snapshot.fare === null) return lowest
      if (lowest === null || snapshot.fare < lowest) return snapshot.fare
      return lowest
    }, null)

  return {
    total: props.flights.length,
    active,
    paused: props.flights.length - active,
    buySignals,
    lowestFare,
  }
})
</script>

<template>
  <AppLayout>
    <div class="mb-8">
      <h2 class="text-3xl font-extrabold tracking-tight text-base-content">追蹤清單</h2>

      <p class="mt-2 text-sm font-medium text-base-content/65">
        管理追蹤中的航線，掌握最佳購買時機，並在價格落入理想區間時快速採取行動。
      </p>
    </div>

    <div class="tracker-panel stats mb-8 w-full stats-horizontal gap-0 rounded-lg">
      <div class="stat px-4 py-3 sm:px-6 sm:py-4">
        <div class="stat-title text-xs sm:text-sm">航線總數</div>

        <div class="stat-value text-xl text-primary sm:text-3xl">{{ summary.total }}</div>

        <div class="stat-desc hidden sm:block">已建立的追蹤項目</div>
      </div>

      <div class="stat px-4 py-3 sm:px-6 sm:py-4">
        <div class="stat-title text-xs sm:text-sm">啟用中</div>

        <div class="stat-value text-xl text-secondary sm:text-3xl">{{ summary.active }}</div>

        <div class="stat-desc hidden sm:block">{{ summary.paused }} 個已暫停</div>
      </div>

      <div class="stat px-4 py-3 sm:px-6 sm:py-4">
        <div class="stat-title text-xs sm:text-sm">最佳買點</div>

        <div class="stat-value text-xl text-success sm:text-3xl">{{ summary.buySignals }}</div>

        <div class="stat-desc hidden sm:block">符合 BUY_SIGNAL 的航線</div>
      </div>
    </div>

    <div class="mb-8 flex items-center justify-between">
      <div class="flex-1"></div>

      <Link href="/flights/create" class="btn shadow-sm btn-primary">建立追蹤</Link>
    </div>

    <div v-if="flights?.length" class="grid gap-6 lg:grid-cols-2">
      <div
        v-for="flight in flights"
        :key="flight.id"
        class="tracker-panel group card rounded-lg transition-all hover:-translate-y-1 hover:shadow-xl"
      >
        <div class="card-body gap-5 p-6">
          <div class="flex items-start justify-between gap-4">
            <div>
              <div
                class="mb-2 flex items-center gap-3 text-2xl font-black tracking-tight text-base-content"
              >
                <span>{{ flight.origin }}</span>

                <span class="text-base-content/25">→</span>

                <span>{{ flight.destination }}</span>
              </div>

              <p class="text-sm font-medium text-base-content/65">
                出發日期：{{ fmtDate(flight.flightDate) }}
              </p>
            </div>

            <div class="shrink-0">
              <span v-if="!flight.isActive" class="badge gap-2 badge-soft px-3 py-3 badge-warning">
                已暫停
              </span>

              <span v-else class="badge gap-2 badge-soft px-3 py-3 badge-success">
                <span class="status status-success"></span>
                追蹤中
              </span>
            </div>
          </div>

          <div class="stats stats-vertical rounded-lg bg-base-200/70 lg:stats-horizontal">
            <div class="stat px-5 py-4">
              <div class="stat-title text-base-content/55">最新票價</div>

              <div class="stat-value text-3xl text-primary">
                {{ fmtFare(getFlightStats(flight.fareSnapshots || []).latest) }}
              </div>
            </div>

            <div class="stat px-5 py-4">
              <div class="stat-title text-base-content/55">歷史最低</div>

              <div class="stat-value text-2xl text-success">
                {{ fmtFare(getFlightStats(flight.fareSnapshots || []).lowest) }}
              </div>
            </div>

            <div class="stat px-5 py-4">
              <div class="stat-title text-base-content/55">歷史最高</div>

              <div class="stat-value text-2xl text-error">
                {{ fmtFare(getFlightStats(flight.fareSnapshots || []).highest) }}
              </div>
            </div>
          </div>

          <div class="mt-auto">
            <div
              v-if="flight.rule37Analysis && flight.rule37Analysis.latestVal !== null"
              class="tracker-panel rounded-lg border px-4 py-4"
              :class="{
                'bg-success/10': flight.rule37Analysis.phase === 'BUY_SIGNAL',
                'bg-info/10': flight.rule37Analysis.phase === 'WAITING',
                'bg-neutral/10': flight.rule37Analysis.phase === 'OBSERVING',
              }"
            >
              <div class="space-y-3">
                <p class="text-xs font-bold tracking-widest uppercase opacity-60">購買時機分析</p>

                <div class="flex items-center gap-2">
                  <template v-if="flight.rule37Analysis.phase === 'BUY_SIGNAL'">
                    <span class="status status-lg status-success"></span>

                    <span class="text-sm font-bold text-success">購買信號（最佳時機）</span>
                  </template>

                  <template v-else-if="flight.rule37Analysis.phase === 'OBSERVING'">
                    <span class="status status-lg status-neutral"></span>

                    <span class="text-sm font-bold text-neutral">觀察期</span>
                  </template>

                  <template v-else>
                    <span class="status status-lg status-info"></span>

                    <span class="text-sm font-bold text-info">
                      等待中（門檻: {{ fmtFare(flight.rule37Analysis.historyBestVal) }}）
                    </span>
                  </template>
                </div>

                <div class="text-xs text-base-content/60">
                  <span class="font-medium">限期：</span>

                  <span>{{ fmtDate(flight.deadline) }}</span>
                </div>
              </div>
            </div>

            <div
              v-else-if="flight.rule37Analysis"
              class="tracker-panel rounded-lg border border-dashed px-4 py-4 text-center"
            >
              <span class="text-sm font-medium text-base-content/60">收集數據中</span>
            </div>

            <div v-else class="tracker-panel rounded-lg border border-dashed px-4 py-4 text-center">
              <span class="text-sm font-medium text-base-content/60"
                >未設定購票限期，無法分析購買時機</span
              >
            </div>
          </div>

          <div class="card-actions justify-end border-t border-base-300/70 pt-5">
            <Link :href="`/flights/${flight.id}`" class="btn btn-neutral">查看詳情</Link>
          </div>
        </div>
      </div>
    </div>

    <div
      v-else
      class="tracker-panel hero rounded-lg border-2 border-dashed py-12 text-center sm:py-20"
    >
      <div class="hero-content flex-col">
        <div class="placeholder avatar mb-6">
          <div class="w-24 rounded-full bg-primary/10 text-5xl text-primary">✈️</div>
        </div>

        <h3 class="mb-2 text-2xl font-bold text-base-content">尚未追蹤任何航班</h3>

        <p class="mb-8 max-w-xl text-sm leading-relaxed text-base-content/65">
          加入您想關注的出發地與目的地，我們將為您不間斷追蹤價格，並在最佳時機提示您購買。
        </p>

        <Link href="/flights/create" class="btn shadow-sm btn-lg btn-primary">
          建立您的第一個追蹤
        </Link>
      </div>
    </div>
  </AppLayout>
</template>
