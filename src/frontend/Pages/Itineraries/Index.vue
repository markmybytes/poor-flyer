<script setup lang="ts">
import AppLayout from '@/Layouts/AppLayout.vue'
import type { Itinerary } from '@/types'
import { fmtDate, fmtFare, fmtItineraryName } from '@/utils'
import { Link, router } from '@inertiajs/vue3'
import { computed, ref } from 'vue'
import { useToast } from 'vue-toast-notification'
import { formatLocalDate } from '@/utils/timezone'

const props = defineProps<{ itineraries: Itinerary[]; baseCurrency: string }>()

const toast = useToast()

const archivedView = ref(
  typeof window !== 'undefined' &&
    new URLSearchParams(window.location.search).get('archived') === '1',
)

const ui = ref<{ pendingId: string | null; restoring: boolean }>({
  pendingId: null,
  restoring: false,
})

const pendingItinerary = computed(() =>
  props.itineraries?.find((it) => it.id === ui.value.pendingId),
)

const summary = computed(() => {
  const its = props.itineraries || []
  const active = its.filter((it) => it.isActive && !it.archivedAt).length
  const lows = its.map((it) => it.statistics?.allTimeLow).filter((v) => v != null) as number[]

  return {
    total: its.length,
    active,
    paused: its.length - active,
    buySignals: its.filter((it) => it.rule37Analysis?.phase === 'BUY_SIGNAL').length,
    lowestTotal: lows.length ? Math.min(...lows) : null,
  }
})

function switchView(archived: boolean) {
  if (archived === archivedView.value) return

  archivedView.value = archived
  router.get('/itineraries/', archived ? { archived: '1' } : {}, {
    preserveState: true,
    preserveScroll: true,
    replace: true,
  })
}

function confirmRestore(itinerary: Itinerary) {
  ui.value.pendingId = itinerary.id
}

function runRestore() {
  const id = ui.value.pendingId
  if (!id) return

  ui.value.restoring = true

  fetch(`/api/itineraries/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ archived: false }),
  })
    .then((res) => {
      if (!res.ok) throw new Error()
      ui.value.pendingId = null
      toast.success('已恢復追蹤')
      router.reload()
    })
    .catch(() => {
      toast.error('恢復追蹤失敗，請稍後再試')
    })
    .finally(() => {
      ui.value.restoring = false
    })
}
</script>

<template>
  <AppLayout>
    <div class="mb-8">
      <h2 class="text-3xl font-extrabold tracking-tight text-base-content">追蹤清單</h2>

      <p class="mt-2 text-sm font-medium text-base-content/65">
        集中管理已儲存的旅程，查看最新價格資訊。
      </p>
    </div>

    <div
      v-if="!archivedView"
      class="tracker-panel stats mb-8 w-full stats-horizontal gap-0 rounded-lg border border-base-200 shadow-sm"
    >
      <div class="stat px-4 py-3 sm:px-6 sm:py-4">
        <div class="stat-title text-xs sm:text-sm">旅程</div>

        <div class="stat-value text-xl text-primary sm:text-3xl">{{ summary.total }}</div>

        <div class="stat-desc hidden sm:block">已儲存的追蹤項目</div>
      </div>

      <div class="stat px-4 py-3 sm:px-6 sm:py-4">
        <div class="stat-title text-xs sm:text-sm">自動追蹤中</div>

        <div class="stat-value text-xl text-secondary sm:text-3xl">{{ summary.active }}</div>

        <div class="stat-desc hidden sm:block">{{ summary.paused }} 個追蹤已暫停</div>
      </div>

      <div class="stat px-4 py-3 sm:px-6 sm:py-4">
        <div class="stat-title text-xs sm:text-sm">可入手提示</div>

        <div class="stat-value text-xl text-success sm:text-3xl">{{ summary.buySignals }}</div>

        <div class="stat-desc hidden sm:block">正值最佳入手時機</div>
      </div>
    </div>

    <div class="mb-8 flex items-center justify-between">
      <div class="join gap-0 shadow-sm">
        <button
          class="btn join-item btn-sm"
          :class="archivedView ? 'border border-base-300 btn-ghost' : 'btn-primary'"
          @click="switchView(false)"
        >
          追蹤中
        </button>

        <button
          class="btn join-item btn-sm"
          :class="archivedView ? 'btn-primary' : 'border border-base-300 btn-ghost'"
          @click="switchView(true)"
        >
          已封存
        </button>
      </div>

      <Link href="/itineraries/create" class="btn shadow-sm btn-primary">新增監察項目</Link>
    </div>

    <div v-if="archivedView" class="grid gap-6 lg:grid-cols-2">
      <div
        v-if="!itineraries?.length"
        class="tracker-panel hero rounded-lg border-2 border-dashed border-base-300 py-12 text-center sm:py-20"
      >
        <div class="hero-content flex-col">
          <div class="mb-4 text-5xl opacity-40">🗄️</div>

          <h3 class="mb-2 text-2xl font-bold text-base-content">沒有已封存的旅程</h3>

          <p class="max-w-xl text-sm leading-relaxed text-base-content/65">
            已完結的旅程會被封存於此，僅保留紀錄供回顧。
          </p>
        </div>
      </div>

      <template v-else>
        <div
          v-for="itinerary in itineraries.toSorted((a, b) =>
            a.createdAt.localeCompare(b.createdAt),
          )"
          :key="itinerary.id"
          class="tracker-panel card rounded-lg border border-base-200 bg-base-200/40"
        >
          <div class="card-body gap-5 p-6">
            <div class="flex flex-col gap-2 opacity-70">
              <div class="flex justify-between gap-2">
                <Link
                  :href="`/itineraries/${itinerary.id}`"
                  class="text-xl font-black tracking-tight text-base-content/80 hover:text-base-content"
                >
                  {{ fmtItineraryName(itinerary) }}
                </Link>

                <span class="badge shrink-0 badge-soft badge-neutral max-sm:p-1">已封存</span>
              </div>

              <p class="text-sm font-medium text-base-content/55">
                日期：{{
                  itinerary.flights.length == 1
                    ? fmtDate(itinerary.flights.at(0).flightDate)
                    : `${fmtDate(itinerary.flights.at(0).flightDate)} - ${fmtDate(itinerary.flights.at(-1).flightDate)}`
                }}
              </p>
            </div>

            <div
              class="stats stats-vertical rounded-lg border border-base-200 bg-base-100/60 lg:stats-horizontal"
            >
              <div class="stat px-5 py-4">
                <div class="stat-title text-base-content/50">最新總計</div>

                <div class="stat-value text-3xl text-base-content/70">
                  {{ fmtFare(itinerary.statistics?.latestVal ?? null, baseCurrency) }}
                </div>
              </div>

              <div class="stat px-5 py-4">
                <div class="stat-title text-base-content/50">歷史最低</div>

                <div class="stat-value text-2xl text-base-content/60">
                  {{ fmtFare(itinerary.statistics?.allTimeLow ?? null, baseCurrency) }}
                </div>
              </div>

              <div class="stat px-5 py-4">
                <div class="stat-title text-base-content/50">歷史最高</div>

                <div class="stat-value text-2xl text-base-content/60">
                  {{ fmtFare(itinerary.statistics?.allTimeHigh ?? null, baseCurrency) }}
                </div>
              </div>
            </div>

            <div class="flex items-center justify-between border-t border-base-300/60 pt-4">
              <span class="text-xs font-medium text-base-content/50">
                封存於 {{ formatLocalDate(itinerary.archivedAt) }}
              </span>

              <button class="btn btn-ghost btn-sm" @click="confirmRestore(itinerary)">
                恢復追蹤
              </button>
            </div>
          </div>
        </div>
      </template>
    </div>

    <template v-else>
      <div v-if="itineraries?.length" class="grid gap-6 lg:grid-cols-2">
        <Link
          v-for="itinerary in itineraries.toSorted((a, b) =>
            a.createdAt.localeCompare(b.createdAt),
          )"
          :key="itinerary.id"
          :href="`/itineraries/${itinerary.id}`"
          class="tracker-panel group card rounded-lg border bg-base-100 transition-all duration-300 hover:-translate-y-1 hover:shadow-xl"
          :class="{
            'border-success/40 hover:border-success/70':
              itinerary.rule37Analysis?.phase === 'BUY_SIGNAL',
            'border-base-200': itinerary.rule37Analysis?.phase !== 'BUY_SIGNAL',
          }"
        >
          <div class="card-body gap-5 p-6">
            <div class="flex flex-col gap-2">
              <div class="flex justify-between gap-2">
                <div class="text-xl font-black tracking-tight text-base-content">
                  <span>{{ fmtItineraryName(itinerary) }}</span>
                </div>

                <div class="shrink-0">
                  <span
                    v-if="!itinerary.isActive"
                    class="badge gap-2 badge-soft badge-warning max-sm:p-1"
                  >
                    已暫停
                  </span>

                  <span v-else class="badge badge-soft badge-success max-sm:p-1">
                    <span class="status status-success"></span> 追蹤中
                  </span>
                </div>
              </div>

              <p class="text-sm font-medium text-base-content/65">
                日期：{{
                  itinerary.flights.length == 1
                    ? fmtDate(itinerary.flights.at(0).flightDate)
                    : `${fmtDate(itinerary.flights.at(0).flightDate)} - ${fmtDate(itinerary.flights.at(-1).flightDate)}`
                }}
              </p>
            </div>

            <div
              class="stats stats-vertical rounded-lg border border-base-200 bg-base-200/50 lg:stats-horizontal"
            >
              <div class="stat px-5 py-4 transition-colors group-hover:bg-base-200/80">
                <div class="stat-title text-base-content/55">最新總計</div>

                <div class="stat-value text-3xl text-primary">
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

            <div class="my-auto">
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
                        {{
                          fmtFare(itinerary.rule37Analysis.historyBestVal ?? null, baseCurrency)
                        }}）
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

          <h3 class="mb-2 text-2xl font-bold text-base-content">未有追蹤任何旅程</h3>

          <p class="mb-8 max-w-xl text-sm leading-relaxed text-base-content/65">
            新增你想關注的，系統將全天候自動收集機票價格，助你分析最佳的購買時機。
          </p>

          <Link href="/itineraries/create" class="btn shadow-sm btn-lg btn-primary">
            建立你的第一個追蹤
          </Link>
        </div>
      </div>
    </template>

    <dialog class="modal" :class="{ 'modal-open': pendingItinerary }">
      <div class="modal-box max-w-sm rounded-2xl border border-base-200 bg-base-100 shadow-xl">
        <h3 class="mb-2 text-lg font-extrabold text-base-content">恢復追蹤？</h3>

        <p class="text-sm text-base-content/60">
          確定恢復追蹤「{{ pendingItinerary ? fmtItineraryName(pendingItinerary) : '' }}」？
        </p>

        <p class="mt-1.5 text-sm text-base-content/60">
          若出發日期已過 30 天，此旅程會在下次自動更新時重新封存。
        </p>

        <div class="modal-action mt-6 justify-end gap-2 border-t border-base-200 pt-4">
          <button type="button" class="btn btn-ghost btn-sm" @click="ui.pendingId = null">
            取消
          </button>

          <button
            type="button"
            class="btn px-5 shadow-sm btn-sm btn-primary"
            :disabled="ui.restoring"
            @click="runRestore"
          >
            <span v-if="ui.restoring" class="loading loading-xs loading-spinner"></span>
            恢復追蹤
          </button>
        </div>
      </div>

      <div class="modal-backdrop bg-black/10 backdrop-blur-xs" @click="ui.pendingId = null"></div>
    </dialog>
  </AppLayout>
</template>
