<script setup lang="ts">
import AppLayout from '@/Layouts/AppLayout.vue'
import type { Itinerary } from '@/types'
import { fmtDate, fmtFare, fmtItineraryName } from '@/utils'
import { Link } from '@inertiajs/vue3'
import { computed } from 'vue'

const props = defineProps<{ itineraries: Itinerary[]; baseCurrency: string }>()

const summary = computed(() => {
  const its = props.itineraries || []
  const active = its.filter((it) => it.isActive).length
  const lows = its.map((it) => it.statistics?.allTimeLow).filter((v) => v != null) as number[]

  return {
    total: its.length,
    active,
    paused: its.length - active,
    buySignals: its.filter((it) => it.rule37Analysis?.phase === 'BUY_SIGNAL').length,
    lowestTotal: lows.length ? Math.min(...lows) : null,
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

    <div
      class="tracker-panel stats mb-8 w-full stats-horizontal gap-0 rounded-lg border border-base-200 shadow-sm"
    >
      <div class="stat px-4 py-3 sm:px-6 sm:py-4">
        <div class="stat-title text-xs sm:text-sm">行程總數</div>

        <div class="stat-value text-xl text-primary sm:text-3xl">{{ summary.total }}</div>

        <div class="stat-desc hidden sm:block">已建立的追蹤項目</div>
      </div>

      <div class="stat px-4 py-3 sm:px-6 sm:py-4">
        <div class="stat-title text-xs sm:text-sm">啟用中</div>

        <div class="stat-value text-xl text-secondary sm:text-3xl">{{ summary.active }}</div>

        <div class="stat-desc hidden sm:block">{{ summary.paused }} 個已暫停</div>
      </div>

      <div class="stat px-4 py-3 sm:px-6 sm:py-4">
        <div class="stat-title text-xs sm:text-sm">最佳時機</div>

        <div class="stat-value text-xl text-success sm:text-3xl">{{ summary.buySignals }}</div>

        <div class="stat-desc hidden sm:block">處於最佳購買時機的行程</div>
      </div>
    </div>

    <div class="mb-8 flex items-center justify-between">
      <div class="flex-1"></div>

      <Link href="/flights/create" class="btn shadow-sm btn-primary">建立追蹤</Link>
    </div>

    <div v-if="itineraries?.length" class="grid gap-6 lg:grid-cols-2">
      <Link
        v-for="itinerary in itineraries.toSorted((a, b) => a.createdAt.localeCompare(b.createdAt))"
        :key="itinerary.id"
        :href="`/flights/${itinerary.id}`"
        class="tracker-panel group card rounded-lg border bg-base-100 transition-all duration-300 hover:-translate-y-1 hover:shadow-xl"
        :class="{
          'border-success/40 hover:border-success/70':
            itinerary.rule37Analysis?.phase === 'BUY_SIGNAL',
          'border-base-200': itinerary.rule37Analysis?.phase !== 'BUY_SIGNAL',
        }"
      >
        <div class="card-body gap-5 p-6">
          <div class="flex items-start justify-between gap-4">
            <div>
              <div
                class="mb-2 flex flex-wrap items-center gap-3 text-xl font-black tracking-tight text-base-content transition-colors group-hover:text-primary"
              >
                <span>{{ fmtItineraryName(itinerary) }}</span>
              </div>

              <p class="text-sm font-medium text-base-content/65">
                出發日期：{{ fmtDate(itinerary.flights[0]?.flightDate) }}
              </p>
            </div>

            <div class="shrink-0">
              <span
                v-if="!itinerary.isActive"
                class="badge gap-2 badge-soft px-3 py-3 badge-warning"
              >
                已暫停
              </span>

              <span v-else class="badge gap-2 badge-soft px-3 py-3 badge-success">
                <span class="status status-success"></span> 追蹤中
              </span>
            </div>
          </div>

          <div
            class="stats stats-vertical rounded-lg border border-base-200 bg-base-200/50 lg:stats-horizontal"
          >
            <div class="stat px-5 py-4 transition-colors group-hover:bg-base-200/80">
              <div class="stat-title text-base-content/55">最新總價</div>

              <div
                class="stat-value text-3xl"
                :class="
                  itinerary.isActive && itinerary.rule37Analysis?.phase === 'BUY_SIGNAL'
                    ? 'text-success'
                    : 'text-primary'
                "
              >
                {{ fmtFare(itinerary.statistics?.latestVal ?? null, baseCurrency) }}
              </div>
            </div>

            <div class="stat px-5 py-4 transition-colors group-hover:bg-base-200/80">
              <div class="stat-title text-base-content/55">歷史最低</div>

              <div class="stat-value text-2xl text-success">
                {{ fmtFare(itinerary.statistics?.allTimeLow ?? null, baseCurrency) }}
              </div>
            </div>

            <div class="stat px-5 py-4 transition-colors group-hover:bg-base-200/80">
              <div class="stat-title text-base-content/55">歷史最高</div>

              <div class="stat-value text-2xl text-error">
                {{ fmtFare(itinerary.statistics?.allTimeHigh ?? null, baseCurrency) }}
              </div>
            </div>
          </div>

          <div class="mt-auto">
            <div
              v-if="itinerary.rule37Analysis && itinerary.statistics?.latestVal !== null"
              class="rounded-lg border px-4 py-4 transition-colors"
              :class="{
                'border-success/20 bg-success/10 group-hover:bg-success/15':
                  itinerary.rule37Analysis.phase === 'BUY_SIGNAL',
                'border-info/20 bg-info/10 group-hover:bg-info/15':
                  itinerary.rule37Analysis.phase === 'WAITING',
                'border-neutral/10 bg-neutral/5 group-hover:bg-neutral/10':
                  itinerary.rule37Analysis.phase === 'OBSERVING',
              }"
            >
              <div class="space-y-3">
                <p class="text-xs font-bold tracking-widest uppercase opacity-60">購買時機分析</p>

                <div class="flex items-center gap-2">
                  <template v-if="itinerary.rule37Analysis.phase === 'BUY_SIGNAL'">
                    <span class="status status-lg animate-pulse status-success"></span>

                    <span class="text-sm font-bold text-success">購買信號（最佳時機）</span>
                  </template>

                  <template v-else-if="itinerary.rule37Analysis.phase === 'OBSERVING'">
                    <span class="status status-lg status-neutral"></span>

                    <span class="text-sm font-bold text-neutral">觀察期</span>
                  </template>

                  <template v-else>
                    <span class="status status-lg status-info"></span>

                    <span class="text-sm font-bold text-info">
                      等待中（門檻:
                      {{ fmtFare(itinerary.rule37Analysis.historyBestVal ?? null, baseCurrency) }}）
                    </span>
                  </template>
                </div>

                <div class="text-xs text-base-content/60">
                  <span class="font-medium">限期：</span>

                  <span>{{ fmtDate(itinerary.deadline) }}</span>
                </div>
              </div>
            </div>

            <div
              v-else-if="itinerary.rule37Analysis"
              class="group-hover:border-base-400 rounded-lg border border-dashed border-base-300 px-4 py-4 text-center transition-colors group-hover:bg-base-200/30"
            >
              <span class="text-sm font-medium text-base-content/60">收集數據中</span>
            </div>

            <div
              v-else
              class="group-hover:border-base-400 rounded-lg border border-dashed border-base-300 px-4 py-4 text-center transition-colors group-hover:bg-base-200/30"
            >
              <span class="text-sm font-medium text-base-content/60">
                未設定購票限期，無法分析購買時機
              </span>
            </div>
          </div>
        </div>
      </Link>
    </div>

    <div
      v-else
      class="tracker-panel hero rounded-lg border-2 border-dashed border-base-300 py-12 text-center sm:py-20"
    >
      <div class="hero-content flex-col">
        <div class="placeholder avatar mb-6 flex justify-center">
          <div
            class="flex h-24 w-24 items-center justify-center rounded-full bg-primary/10 text-5xl text-primary"
          >
            ✈️
          </div>
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
