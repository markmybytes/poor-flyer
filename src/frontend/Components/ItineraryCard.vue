<script setup lang="ts">
import type { Itinerary } from '@/types'
import { fmtDate, fmtFare, fmtItineraryName } from '@/utils'
import { formatLocalDate } from '@/utils/timezone'
import { Link } from '@inertiajs/vue3'

defineProps<{
  itinerary: Itinerary
  baseCurrency: string
  archived?: boolean
}>()

const emit = defineEmits<{ restore: [itinerary: Itinerary] }>()
</script>

<template>
  <div
    class="tracker-panel card relative rounded-lg border"
    :class="
      archived
        ? 'border-base-200 bg-base-200/40'
        : [
            'bg-base-100 transition-all duration-300 hover:-translate-y-1 hover:shadow-xl',
            itinerary.rule37Analysis?.phase === 'BUY_SIGNAL'
              ? 'border-success/40 hover:border-success/70'
              : 'border-base-200',
          ]
    "
  >
    <Link
      :href="`/itineraries/${itinerary.id}`"
      class="absolute inset-0 z-10"
      :aria-label="`查看 ${fmtItineraryName(itinerary)} 詳情`"
    ></Link>

    <div class="card-body gap-5 p-6">
      <div class="flex flex-col gap-2" :class="archived ? 'opacity-70' : ''">
        <div class="flex justify-between gap-2">
          <span
            class="text-xl font-black tracking-tight"
            :class="archived ? 'text-base-content/80' : 'text-base-content'"
          >
            {{ fmtItineraryName(itinerary) }}
          </span>

          <span v-if="archived" class="badge shrink-0 badge-soft badge-neutral max-sm:p-1">
            已封存
          </span>

          <span
            v-else-if="!itinerary.isActive"
            class="badge shrink-0 badge-soft badge-warning max-sm:p-1"
          >
            已暫停
          </span>
        </div>

        <p class="text-sm font-medium" :class="archived ? 'text-base-content/55' : ''">
          日期：{{
            itinerary.flights.length == 1
              ? fmtDate(itinerary.flights.at(0).flightDate)
              : `${fmtDate(itinerary.flights.at(0).flightDate)} - ${fmtDate(itinerary.flights.at(-1).flightDate)}`
          }}
        </p>
      </div>

      <div
        class="stats stats-vertical rounded-lg border border-base-200 lg:stats-horizontal"
        :class="archived ? 'bg-base-100/60' : 'bg-base-200/50'"
      >
        <div
          class="stat px-5 py-4"
          :class="archived ? '' : 'transition-colors group-hover:bg-base-200/80'"
        >
          <div
            class="stat-title"
            :class="archived ? 'text-base-content/50' : 'text-base-content/55'"
          >
            最新總計
          </div>

          <div
            class="stat-value text-3xl"
            :class="archived ? 'text-base-content/70' : 'text-primary'"
          >
            {{ fmtFare(itinerary.statistics?.latestVal ?? null, baseCurrency) }}
          </div>
        </div>

        <div
          class="stat px-5 py-4"
          :class="archived ? '' : 'transition-colors group-hover:bg-base-200/80'"
        >
          <div
            class="stat-title"
            :class="archived ? 'text-base-content/50' : 'text-base-content/55'"
          >
            歷史最低
          </div>

          <div
            class="stat-value text-2xl"
            :class="archived ? 'text-base-content/60' : 'text-success'"
          >
            {{ fmtFare(itinerary.statistics?.allTimeLow ?? null, baseCurrency) }}
          </div>
        </div>

        <div
          class="stat px-5 py-4"
          :class="archived ? '' : 'transition-colors group-hover:bg-base-200/80'"
        >
          <div
            class="stat-title"
            :class="archived ? 'text-base-content/50' : 'text-base-content/55'"
          >
            歷史最高
          </div>

          <div
            class="stat-value text-2xl"
            :class="archived ? 'text-base-content/60' : 'text-error'"
          >
            {{ fmtFare(itinerary.statistics?.allTimeHigh ?? null, baseCurrency) }}
          </div>
        </div>
      </div>

      <div v-if="!archived" class="my-auto">
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

                <span class="text-sm font-bold text-success">入手訊號（最佳購買時機）</span>
              </template>

              <template v-else-if="itinerary.rule37Analysis.phase === 'OBSERVING'">
                <span class="status status-lg status-neutral"></span>

                <span class="text-sm font-bold text-neutral">數據觀察期</span>
              </template>

              <template v-else>
                <span class="status status-lg status-info"></span>

                <span class="text-sm font-bold text-info">
                  決策期（門檻:
                  {{ fmtFare(itinerary.rule37Analysis.historyBestVal ?? null, baseCurrency) }}）
                </span>
              </template>
            </div>

            <div class="text-xs text-base-content/60">
              <span class="font-medium">購票限期：</span>

              <span>{{ fmtDate(itinerary.deadline) }}</span>
            </div>
          </div>
        </div>

        <div
          v-else-if="itinerary.deadline && itinerary.statistics?.latestVal == null"
          class="bg-base-50/50 group-hover:border-base-400 rounded-lg border border-dashed border-base-300 px-4 py-5 text-center transition-all group-hover:bg-base-200/20"
        >
          <div class="flex flex-col items-center justify-center space-y-2">
            <div class="space-y-0.5">
              <span class="text-sm font-bold text-base-content/80">正在收集票價數據...</span>
            </div>

            <div class="my-1 w-full border-t border-base-200/60"></div>

            <div class="flex items-center justify-center gap-1 text-xs text-base-content/60">
              <span class="font-medium opacity-70">購票限期：</span>

              <span>{{ fmtDate(itinerary.deadline) }}</span>
            </div>
          </div>
        </div>

        <div
          v-else
          class="group-hover:border-base-400 rounded-lg border border-dashed border-base-300 px-4 py-4 text-center transition-colors group-hover:bg-base-200/30"
        >
          <span class="text-sm font-medium text-base-content/60">
            未設定購票限期，無法分析最佳入手時機
          </span>
        </div>
      </div>

      <div v-else class="flex items-center justify-between border-t border-base-300/60 pt-4">
        <span class="text-xs font-medium text-base-content/50">
          封存於 {{ formatLocalDate(itinerary.archivedAt) }}
        </span>

        <button class="btn relative z-20 btn-ghost btn-sm" @click="emit('restore', itinerary)">
          恢復追蹤
        </button>
      </div>
    </div>
  </div>
</template>
