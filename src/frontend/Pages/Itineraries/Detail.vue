<script setup lang="ts">
import FareGraph from '@/Components/FareGraph.vue'
import FaretList from '@/Components/FareList.vue'
import AppLayout from '@/Layouts/AppLayout.vue'
import { CABIN_CLASS_OPTIONS, MAX_STOPS_OPTIONS } from '@/options'
import type { Itinerary } from '@/types'
import { fmtDate, fmtFare, fmtItineraryName } from '@/utils'
import { router } from '@inertiajs/vue3'
import { ref } from 'vue'
import { useToast } from 'vue-toast-notification'

import { calculateDaysRemaining } from '@/utils/timezone'
import { Icon } from '@iconify/vue'
import { VueDatePicker } from '@vuepic/vue-datepicker'
import '@vuepic/vue-datepicker/dist/main.css'
import { zhHK } from 'date-fns/locale'

const props = defineProps<{ itinerary: Itinerary; baseCurrency: string }>()
const toast = useToast()

const activeTab = ref('graph')
const loading = ref<string | null>(null)

const showModal = ref(false)
const deadlineValue = ref(props.itinerary.deadline || '')

const filterLabels = {
  cabinClass:
    CABIN_CLASS_OPTIONS.find((option) => option.value === props.itinerary.cabinClass)?.label ??
    '未設定',
  maxStops:
    MAX_STOPS_OPTIONS.find((option) => option.value === props.itinerary.maxStops)?.label ??
    '未設定',
}

const openEditModal = () => {
  deadlineValue.value = props.itinerary.deadline || ''
  showModal.value = true
}

const showDeleteModal = ref(false)

const submitDeadline = async (clear = false) => {
  loading.value = 'update_deadline'
  const targetDeadline = clear ? null : deadlineValue.value || null

  try {
    const res = await fetch(`/api/itineraries/${props.itinerary.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ deadline: targetDeadline }),
    })
    if (!res.ok) {
      throw new Error()
    }

    toast.success(clear ? '已移除購票限期' : '已更新購票限期')
    showModal.value = false
    router.reload()
  } catch {
    toast.error('更新限期失敗，請稍後再試')
  } finally {
    loading.value = null
  }
}

const runAction = async (action: 'toggle' | 'scrape' | 'delete') => {
  if (action === 'delete') {
    showDeleteModal.value = false
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
      `/api/itineraries/${props.itinerary.id}${action === 'scrape' ? '/scrape' : ''}`,
      opts,
    )
    if (!res.ok) {
      throw new Error()
    }

    if (action === 'delete') {
      router.visit('/itineraries/')
    } else {
      router.reload()
    }
  } catch {
    toast.error(
      `${action === 'scrape' ? '更新票價' : action === 'delete' ? '刪除' : '操作'}失敗，請稍後再試`,
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
          <div class="flex flex-col gap-2">
            <div class="flex justify-between gap-2">
              <div class="text-base font-bold text-base-content">
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

            <p class="text-sm font-medium text-base-content/60">
              日期：{{
                itinerary.flights.length == 1
                  ? fmtDate(itinerary.flights.at(0).flightDate)
                  : `${fmtDate(itinerary.flights.at(0).flightDate)} - ${fmtDate(itinerary.flights.at(-1).flightDate)}`
              }}
            </p>
          </div>
        </div>

        <div class="flex justify-end px-6 py-5">
          <div class="join gap-2">
            <button
              class="btn join-item btn-sm"
              :disabled="loading === 'toggle'"
              @click="runAction('toggle')"
            >
              {{ itinerary.isActive ? '暫停追蹤' : '開始追蹤' }}
            </button>

            <button
              title="修改購票限期"
              class="btn join-item btn-sm"
              :disabled="loading !== null"
              @click="openEditModal"
            >
              <Icon icon="mdi:calendar-edit" />
            </button>

            <button
              title="刪除此追蹤"
              class="btn join-item btn-soft btn-sm btn-error"
              @click="showDeleteModal = true"
            >
              <Icon icon="mdi:delete" />
            </button>

            <button
              class="btn join-item btn-sm btn-primary"
              :disabled="loading === 'scrape'"
              @click="runAction('scrape')"
            >
              <span v-if="loading === 'scrape'" class="loading loading-xs loading-spinner"></span>
              {{ loading === 'scrape' ? '更新中...' : '下載最新票價' }}
            </button>
          </div>
        </div>

        <div class="border-t border-base-300/70 px-6 py-5">
          <div class="flex flex-wrap items-center gap-2">
            <p class="text-sm font-bold text-base-content">票價搜尋條件</p>

            <span class="badge badge-soft badge-sm">艙等 {{ filterLabels.cabinClass }}</span>

            <span class="badge badge-soft badge-sm">轉機 {{ filterLabels.maxStops }}</span>

            <template v-if="itinerary.airlines?.length">
              <span
                v-for="code in itinerary.airlines"
                :key="code"
                class="inline-flex items-center rounded bg-base-200/60 px-2 py-1 text-xs font-bold"
              >
                {{ code }}
              </span>
            </template>

            <span v-else class="badge badge-soft badge-sm">航空公司 未設定</span>
          </div>

          <p class="mt-1 text-xs font-medium text-base-content/55">修改搜尋條件請刪除後重新建立</p>
        </div>
      </div>
    </div>

    <div
      class="tracker-panel mb-8 overflow-hidden rounded-xl border transition-all"
      :class="{
        'border-success/30 bg-success/5': itinerary.rule37Analysis?.phase === 'BUY_SIGNAL',
        'border-info/30 bg-info/5': itinerary.rule37Analysis?.phase === 'WAITING',
        'border-base-300 bg-base-200/30': itinerary.rule37Analysis?.phase === 'OBSERVING',
        'border-base-200 bg-base-100': !itinerary.rule37Analysis?.phase,
      }"
    >
      <div class="flex flex-col lg:flex-row lg:items-stretch">
        <div class="flex flex-1 flex-col justify-between p-4 sm:p-5">
          <div>
            <div class="flex items-center gap-2.5">
              <span
                class="status shadow-sm"
                :class="{
                  'animate-pulse status-success': itinerary.rule37Analysis?.phase === 'BUY_SIGNAL',
                  'status-info': itinerary.rule37Analysis?.phase === 'WAITING',
                  'status-neutral': itinerary.rule37Analysis?.phase === 'OBSERVING',
                  'status-warning': !itinerary.rule37Analysis?.phase && itinerary.deadline,
                  'status-neutral opacity-40': !itinerary.deadline,
                }"
              ></span>

              <span
                class="text-lg font-extrabold tracking-tight"
                :class="{
                  'text-success': itinerary.rule37Analysis?.phase === 'BUY_SIGNAL',
                  'text-info': itinerary.rule37Analysis?.phase === 'WAITING',
                  'text-neutral': itinerary.rule37Analysis?.phase === 'OBSERVING',
                  'text-warning': !itinerary.rule37Analysis?.phase && itinerary.deadline,
                  'text-base-content/40': !itinerary.deadline,
                }"
              >
                <template v-if="itinerary.rule37Analysis?.phase === 'BUY_SIGNAL'">
                  入手訊號
                </template>

                <template v-else-if="itinerary.rule37Analysis?.phase === 'WAITING'">
                  決策期
                </template>

                <template v-else-if="itinerary.rule37Analysis?.phase === 'OBSERVING'">
                  數據觀察期
                </template>

                <template v-else-if="itinerary.deadline">收集數據中</template>

                <template v-else>未啟用數據分析</template>
              </span>
            </div>

            <p class="mt-1.5 text-xs font-medium text-base-content/60">
              <template v-if="itinerary.rule37Analysis?.phase === 'BUY_SIGNAL'">
                最新總計已跌穿觀察期錄得的最低價格。
              </template>

              <template v-else-if="itinerary.rule37Analysis?.phase === 'WAITING'">
                已進入決策階段。系統將會分析價格變化，找出最佳購買時機。
              </template>

              <template v-else-if="itinerary.rule37Analysis?.phase === 'OBSERVING'">
                系統現正收集票價數據，決策期將於
                <span class="font-bold">{{ fmtDate(itinerary.rule37Analysis.cutoffDate) }}</span>
                開始。
              </template>

              <template v-else-if="itinerary.deadline">未有足夠數據分析購買時機。</template>

              <template v-else>
                <button class="inline-block link font-bold link-primary" @click="openEditModal">
                  設定購票限期
                </button>
                以啟用購買時機分析。
              </template>
            </p>
          </div>

          <div class="mt-2.5">
            <div class="my-2 border-t border-base-300/60"></div>

            <div class="flex flex-wrap items-center gap-x-3 gap-y-1.5 text-xs">
              <template v-if="itinerary.rule37Analysis?.phase === 'OBSERVING'">
                <div class="flex items-center gap-1.5">
                  <span class="font-medium text-base-content/50">決策期</span>

                  <span
                    class="rounded bg-base-300/50 px-1.5 py-0.5 font-bold text-base-content"
                    :class="{
                      'bg-error/10 text-error':
                        calculateDaysRemaining(itinerary.rule37Analysis.cutoffDate) <= 0,
                    }"
                  >
                    {{
                      calculateDaysRemaining(itinerary.rule37Analysis.cutoffDate) > 0
                        ? calculateDaysRemaining(itinerary.rule37Analysis.cutoffDate) + '天後'
                        : '已過'
                    }}
                  </span>
                </div>

                <span class="hidden text-base-content/25 sm:inline">|</span>
              </template>

              <template v-else-if="itinerary.deadline">
                <div class="flex items-center gap-1.5">
                  <span class="font-medium text-base-content/50">購票限期</span>

                  <span
                    class="rounded bg-base-300/50 px-1.5 py-0.5 font-bold text-base-content"
                    :class="{
                      'bg-error/10 text-error': calculateDaysRemaining(itinerary.deadline) <= 0,
                    }"
                  >
                    {{
                      calculateDaysRemaining(itinerary.deadline) > 0
                        ? calculateDaysRemaining(itinerary.deadline) + '天後'
                        : '已過'
                    }}
                  </span>
                </div>

                <span class="hidden text-base-content/25 sm:inline">|</span>
              </template>

              <div v-if="itinerary.flights?.length" class="flex items-center gap-1.5">
                <span class="font-medium text-base-content/50">出發日期</span>

                <span
                  class="rounded bg-base-300/50 px-1.5 py-0.5 font-bold text-base-content"
                  :class="{
                    'bg-error/10 text-error':
                      calculateDaysRemaining(itinerary.flights[0].flightDate) <= 0,
                  }"
                >
                  {{
                    calculateDaysRemaining(itinerary.flights[0].flightDate) > 0
                      ? calculateDaysRemaining(itinerary.flights[0].flightDate) + '天後'
                      : '已過'
                  }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div
          class="grid shrink-0 grid-cols-2 gap-px bg-base-300/60 sm:grid-cols-4 lg:w-120 xl:w-140"
        >
          <div
            class="col-span-2 flex flex-col justify-center bg-base-100 p-4 transition-colors sm:p-5"
          >
            <div class="flex items-center justify-between">
              <span class="text-[10px] font-bold tracking-widest text-base-content/50 uppercase">
                最新總計
              </span>
            </div>

            <div class="mt-1 flex items-baseline gap-2">
              <span class="text-3xl font-black text-primary lg:text-4xl">
                {{ fmtFare(itinerary.statistics?.latestVal ?? null, baseCurrency) }}
              </span>
            </div>

            <div class="mt-1.5 text-xs font-medium text-base-content/40">
              <template v-if="itinerary.deadline">
                門檻：{{
                  itinerary.rule37Analysis?.historyBestVal
                    ? fmtFare(itinerary.rule37Analysis.historyBestVal, baseCurrency)
                    : '--'
                }}
              </template>
            </div>
          </div>

          <div class="flex flex-col justify-center bg-base-100 p-4 transition-colors sm:p-5">
            <span class="text-[10px] font-bold tracking-widest text-base-content/50 uppercase">
              歷史最低
            </span>

            <span class="mt-1 text-xl font-black text-success lg:text-2xl">
              {{ fmtFare(itinerary.statistics?.allTimeLow ?? null, baseCurrency) }}
            </span>
          </div>

          <div class="flex flex-col justify-center bg-base-100 p-4 transition-colors sm:p-5">
            <span class="text-[10px] font-bold tracking-widest text-base-content/50 uppercase">
              歷史最高
            </span>

            <span class="mt-1 text-xl font-black text-error lg:text-2xl">
              {{ fmtFare(itinerary.statistics?.allTimeHigh ?? null, baseCurrency) }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <div class="tracker-panel card rounded-lg">
      <div class="card-body gap-2 p-4 md:p-6">
        <div class="tabs-box tabs flex-nowrap overflow-x-auto bg-base-200/70 p-1 whitespace-nowrap">
          <button
            class="tab h-12 shrink-0 px-6 text-sm font-bold"
            :class="activeTab === 'graph' ? 'tab-active' : ''"
            @click="activeTab = 'graph'"
          >
            價格趨勢圖
          </button>

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
              <FaretList
                :flight="f"
                :rule37-analysis="itinerary.rule37Analysis"
                :display-currency="baseCurrency"
              />
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
            <div v-show="activeTab === 'graph'" class="col-start-1 row-start-1 min-w-0">
              <FareGraph :itinerary="itinerary" />
            </div>
          </Transition>
        </div>
      </div>
    </div>

    <dialog class="modal" :class="{ 'modal-open': showModal }">
      <div class="modal-box max-w-sm rounded-2xl border border-base-200 bg-base-100 shadow-xl">
        <h3 class="mb-4 text-lg font-extrabold text-base-content">修改購票限期</h3>

        <fieldset class="fieldset">
          <legend class="fieldset-legend mb-2 text-sm font-bold">限期</legend>

          <VueDatePicker
            v-model="deadlineValue"
            :enable-time-picker="false"
            :locale="zhHK"
            auto-apply
            model-type="yyyy-MM-dd"
            teleport="body"
          >
            <template #trigger>
              <input
                type="text"
                :value="deadlineValue"
                placeholder="選擇日期"
                class="input-bordered input w-full cursor-pointer transition-colors focus:input-primary"
                readonly
              />
            </template>
          </VueDatePicker>
        </fieldset>

        <div
          class="modal-action mt-6 flex items-center justify-between border-t border-base-200 pt-4"
        >
          <div>
            <button
              v-if="itinerary.deadline"
              type="button"
              class="btn btn-soft btn-sm btn-error"
              :disabled="loading === 'update_deadline'"
              @click="submitDeadline(true)"
            >
              移除限期
            </button>
          </div>

          <div class="flex gap-2">
            <button type="button" class="btn btn-ghost btn-sm" @click="showModal = false">
              取消
            </button>

            <button
              type="button"
              class="btn px-5 shadow-sm btn-sm btn-primary"
              :disabled="loading === 'update_deadline'"
              @click="submitDeadline(false)"
            >
              <span
                v-if="loading === 'update_deadline'"
                class="loading loading-xs loading-spinner"
              ></span>
              更新
            </button>
          </div>
        </div>
      </div>

      <div class="modal-backdrop bg-black/10 backdrop-blur-xs" @click="showModal = false"></div>
    </dialog>

    <dialog class="modal" :class="{ 'modal-open': showDeleteModal }">
      <div class="modal-box max-w-sm rounded-2xl border border-base-200 bg-base-100 shadow-xl">
        <h3 class="mb-2 text-lg font-extrabold text-base-content">刪除此追蹤？</h3>

        <p class="text-sm text-base-content/60">
          刪除後將移除此旅程及其所有已收集的票價資料，此操作無法復原。
        </p>

        <div class="modal-action mt-6 justify-end gap-2 border-t border-base-200 pt-4">
          <button type="button" class="btn btn-ghost btn-sm" @click="showDeleteModal = false">
            取消
          </button>

          <button
            type="button"
            class="btn btn-soft btn-sm btn-error"
            :disabled="loading === 'delete'"
            @click="runAction('delete')"
          >
            <span v-if="loading === 'delete'" class="loading loading-xs loading-spinner"></span>
            刪除
          </button>
        </div>
      </div>

      <div
        class="modal-backdrop bg-black/10 backdrop-blur-xs"
        @click="showDeleteModal = false"
      ></div>
    </dialog>
  </AppLayout>
</template>
