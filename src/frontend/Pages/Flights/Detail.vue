<script setup lang="ts">
import FareGraph from '@/Components/FareGraph.vue'
import FaretList from '@/Components/FareList.vue'
import AppLayout from '@/Layouts/AppLayout.vue'
import type { Itinerary } from '@/types'
import { fmtDate, fmtFare, fmtItineraryName } from '@/utils'
import { router } from '@inertiajs/vue3'
import { ref } from 'vue'
import { useToast } from 'vue-toast-notification'

const props = defineProps<{ itinerary: Itinerary }>()
const toast = useToast()

const activeTab = ref('0')
const loading = ref<string | null>(null)
const detailPanel = ref(props.itinerary.deadline ? 'analysis' : 'summary')

const runAction = async (action: 'toggle' | 'scrape' | 'delete') => {
  if (action === 'delete' && !confirm('確認刪除此航班追蹤？')) {
    return
  }
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
    if (!res.ok) {
      throw new Error()
    }

    if (action === 'delete') {
      router.visit('/flights/')
    } else {
      router.reload()
    }
  } catch {
    toast.error(
      `${action === 'scrape' ? '擷取' : action === 'delete' ? '刪除' : '操作'}失敗，請稍後再試`,
    )
  } finally {
    loading.value = null
  }
}
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
        'bg-success/10':
          detailPanel === 'analysis' && itinerary.rule37Analysis?.phase === 'BUY_SIGNAL',
        'bg-info/10': detailPanel === 'analysis' && itinerary.rule37Analysis?.phase === 'WAITING',
        'bg-neutral/10':
          detailPanel === 'analysis' && itinerary.rule37Analysis?.phase === 'OBSERVING',
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
          :class="
            detailPanel !== 'analysis' ? 'pointer-events-none invisible opacity-0' : 'opacity-100'
          "
        >
          <div v-if="itinerary.deadline && itinerary.rule37Analysis?.phase" class="space-y-4">
            <div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div class="flex items-center gap-3">
                <template v-if="itinerary.rule37Analysis.phase === 'BUY_SIGNAL'">
                  <span class="status status-lg status-success"></span>

                  <span class="text-lg font-bold text-success">購買信號 (最佳時機)</span>
                </template>

                <template v-else-if="itinerary.rule37Analysis.phase === 'OBSERVING'">
                  <span class="status status-lg status-neutral"></span>

                  <span class="text-lg font-bold text-neutral">觀察期</span>

                  <span class="badge px-2 py-1 text-xs font-medium badge-warning">
                    {{
                      Math.ceil(
                        (new Date(itinerary.rule37Analysis.cutoffDate).getTime() - Date.now()) /
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
                  {{ fmtDate(itinerary.rule37Analysis.cutoffDate) }}
                </p>

                <p>
                  <span class="font-medium">門檻：</span>
                  {{ fmtFare(itinerary.rule37Analysis.historyBestVal) }}
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
          :class="
            detailPanel !== 'summary' ? 'pointer-events-none invisible opacity-0' : 'opacity-100'
          "
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
      <div class="card-body gap-6 p-4 md:p-6">
        <div class="tabs-box tabs flex-nowrap overflow-x-auto bg-base-200/70 p-1 whitespace-nowrap">
          <button
            v-if="itinerary.tripType === 'SINGLE'"
            class="tab h-12 shrink-0 px-6 text-sm font-bold"
            :class="activeTab === '0' ? 'tab-active' : ''"
            @click="activeTab = '0'"
          >
            詳細數據列表
          </button>

          <template v-else>
            <button
              v-for="(f, i) in itinerary.flights"
              :key="f.id"
              class="tab h-12 shrink-0 px-6 text-sm font-bold"
              :class="activeTab === String(i) ? 'tab-active' : ''"
              @click="activeTab = String(i)"
            >
              {{ f.origin }} → {{ f.destination }}
            </button>
          </template>

          <button
            class="tab h-12 shrink-0 px-6 text-sm font-bold"
            :class="activeTab === 'graph' ? 'tab-active' : ''"
            @click="activeTab = 'graph'"
          >
            價格趨勢圖表
          </button>
        </div>

        <div class="grid overflow-hidden">
          <Transition
            v-for="(f, i) in itinerary.flights"
            :key="f.id"
            enter-active-class="transition-all duration-300 ease-out"
            enter-from-class="opacity-0 -translate-x-8"
            enter-to-class="opacity-100 translate-x-0"
            leave-active-class="transition-all duration-200 ease-in"
            leave-from-class="opacity-100 translate-x-0"
            leave-to-class="opacity-0 -translate-x-8"
          >
            <div v-show="activeTab === String(i)" class="col-start-1 row-start-1">
              <FaretList :flight="f" :rule37-analysis="itinerary.rule37Analysis" />
            </div>
          </Transition>

          <Transition
            enter-active-class="transition-all duration-300 ease-out"
            enter-from-class="opacity-0 translate-x-8"
            enter-to-class="opacity-100 translate-x-0"
            leave-active-class="transition-all duration-200 ease-in"
            leave-from-class="opacity-100 translate-x-0"
            leave-to-class="opacity-0 translate-x-8"
          >
            <div v-show="activeTab === 'graph'" class="col-start-1 row-start-1">
              <FareGraph :itinerary="itinerary" />
            </div>
          </Transition>
        </div>
      </div>
    </div>
  </AppLayout>
</template>
