<script setup lang="ts">
import FareGraph from '@/Components/FareGraph.vue'
import FaretList from '@/Components/FareList.vue'
import AppLayout from '@/Layouts/AppLayout.vue'
import { CABIN_CLASS_OPTIONS, MAX_STOPS_OPTIONS } from '@/options'
import type { Itinerary } from '@/types'
import { fmtDate, fmtFare, fmtItineraryName } from '@/utils'
import { router } from '@inertiajs/vue3'
import { computed, ref } from 'vue'
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

const filterSummary = computed(() => {
  const cabin = CABIN_CLASS_OPTIONS.find(
    (option) => option.value === props.itinerary.cabinClass,
  )?.label
  const stops = MAX_STOPS_OPTIONS.find(
    (option) => option.value === props.itinerary.maxStops && option.value !== 'ANY',
  )?.label
  const { airlines } = props.itinerary

  return {
    cabin,
    stops,
    airlines,
    empty: !cabin && !stops && !airlines?.length,
  }
})

const openEditModal = () => {
  deadlineValue.value = props.itinerary.deadline || ''
  showModal.value = true
}

const showDeleteModal = ref(false)
const showRestoreModal = ref(false)
const showArchiveModal = ref(false)
const isArchived = computed(() => !!props.itinerary.archivedAt)

const submitDeadline = (clear = false) => {
  loading.value = 'update_deadline'
  const targetDeadline = clear ? null : deadlineValue.value || null

  fetch(`/api/itineraries/${props.itinerary.id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ deadline: targetDeadline }),
  })
    .then((res) => {
      if (!res.ok) {
        throw new Error()
      }

      toast.success(clear ? '已移除購票限期' : '已更新購票限期')
      showModal.value = false
      router.reload()
    })
    .catch(() => toast.error('更新限期失敗，請稍後再試'))
    .finally(() => {
      loading.value = null
    })
}

const runAction = (action: 'toggle' | 'scrape' | 'delete' | 'restore' | 'archive') => {
  if (action === 'delete') {
    showDeleteModal.value = false
  }
  if (action === 'restore') {
    showRestoreModal.value = false
  }
  if (action === 'archive') {
    showArchiveModal.value = false
  }
  loading.value = action

  const opts: RequestInit = {
    method:
      action === 'toggle' || action === 'restore' || action === 'archive'
        ? 'PATCH'
        : action === 'scrape'
          ? 'POST'
          : 'DELETE',
  }
  if (action === 'toggle') {
    opts.headers = { 'Content-Type': 'application/json' }
    opts.body = JSON.stringify({ is_active: !props.itinerary.isActive })
  }
  if (action === 'restore') {
    opts.headers = { 'Content-Type': 'application/json' }
    opts.body = JSON.stringify({ archived: false })
  }
  if (action === 'archive') {
    opts.headers = { 'Content-Type': 'application/json' }
    opts.body = JSON.stringify({ archived: true })
  }

  fetch(`/api/itineraries/${props.itinerary.id}${action === 'scrape' ? '/scrape' : ''}`, opts)
    .then((res) => {
      if (!res.ok) {
        throw new Error()
      }

      if (action === 'delete') {
        router.visit('/itineraries/')
      } else {
        if (action === 'restore') {
          toast.success('已恢復追蹤')
        }
        if (action === 'archive') {
          toast.success('已封存')
        }
        router.reload()
      }
    })
    .catch(() => {
      toast.error(
        `${
          action === 'scrape'
            ? '更新票價'
            : action === 'delete'
              ? '刪除'
              : action === 'restore'
                ? '恢復追蹤'
                : action === 'archive'
                  ? '封存'
                  : '操作'
        }失敗，請稍後再試`,
      )
    })
    .finally(() => {
      loading.value = null
    })
}
</script>

<template>
  <AppLayout>
    <div class="tracker-panel card mb-6 rounded-lg">
      <div class="card-body p-0">
        <div class="border-b border-base-300/70 px-4 py-4 md:px-6 md:py-5">
          <div class="flex flex-col gap-2">
            <div class="flex items-start justify-between gap-3">
              <h1 class="text-lg font-black tracking-tight text-base-content md:text-xl">
                {{ fmtItineraryName(itinerary) }}
              </h1>

              <div class="shrink-0">
                <span v-if="isArchived" class="badge badge-soft badge-neutral">已封存</span>

                <span v-else-if="!itinerary.isActive" class="badge gap-2 badge-soft badge-warning">
                  已暫停
                </span>

                <span v-else class="badge badge-soft badge-success">
                  <span class="status status-success"></span> 追蹤中
                </span>
              </div>
            </div>

            <p
              class="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm font-medium text-base-content/60"
            >
              <span
                >日期：{{
                  itinerary.flights.length == 1
                    ? fmtDate(itinerary.flights.at(0).flightDate)
                    : `${fmtDate(itinerary.flights.at(0).flightDate)} - ${fmtDate(itinerary.flights.at(-1).flightDate)}`
                }}</span
              >
            </p>

            <p
              class="flex flex-wrap items-center gap-x-2.5 gap-y-1 text-sm font-medium text-base-content/60"
            >
              <template v-if="!filterSummary.empty">
                <span v-if="filterSummary.cabin">{{ filterSummary.cabin }}</span>

                <span v-if="filterSummary.stops">轉機 {{ filterSummary.stops }}</span>

                <span
                  v-if="filterSummary.airlines?.length"
                  class="inline-flex flex-wrap items-center gap-x-1.5 gap-y-1"
                >
                  <span
                    v-for="code in filterSummary.airlines"
                    :key="code"
                    class="inline-flex rounded bg-base-200/60 px-2 py-0.5 text-xs font-bold text-base-content"
                  >
                    {{ code }}
                  </span>
                </span>
              </template>

              <span v-else class="text-base-content/45">未設定篩選</span>

              <span
                class="tooltip before:text-xs"
                tabindex="0"
                data-tip="修改搜尋條件請刪除後重新建立"
              >
                <Icon
                  icon="mdi:information-outline"
                  class="size-3.5 shrink-0 cursor-help text-base-content/40"
                />
              </span>
            </p>
          </div>
        </div>

        <div class="flex flex-wrap justify-end gap-2 px-4 py-4 md:px-6 md:py-5">
          <template v-if="isArchived">
            <button
              class="btn btn-sm btn-primary"
              :disabled="loading === 'restore'"
              @click="showRestoreModal = true"
            >
              恢復追蹤
            </button>
          </template>

          <template v-else>
            <button
              class="btn btn-sm"
              :disabled="loading === 'toggle'"
              @click="runAction('toggle')"
            >
              {{ itinerary.isActive ? '暫停追蹤' : '開始追蹤' }}
            </button>
          </template>

          <button
            title="修改購票限期"
            aria-label="修改購票限期"
            class="btn btn-sm"
            :disabled="loading !== null"
            @click="openEditModal"
          >
            <Icon icon="mdi:calendar-edit" />
          </button>

          <button
            v-if="!isArchived"
            type="button"
            title="封存此追蹤"
            aria-label="封存此追蹤"
            class="btn btn-sm"
            :disabled="loading !== null"
            @click="showArchiveModal = true"
          >
            <Icon icon="mdi:archive-outline" />
          </button>

          <button
            title="刪除此追蹤"
            aria-label="刪除此追蹤"
            class="btn btn-soft btn-sm btn-error"
            @click="showDeleteModal = true"
          >
            <Icon icon="mdi:delete" />
          </button>

          <button
            v-if="!isArchived"
            class="btn btn-sm btn-primary"
            :disabled="loading === 'scrape'"
            @click="runAction('scrape')"
          >
            <span v-if="loading === 'scrape'" class="loading loading-xs loading-spinner"></span>
            {{ loading === 'scrape' ? '更新中...' : '下載最新票價' }}
          </button>
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
      <div class="flex flex-col xl:flex-row xl:items-stretch">
        <div class="flex flex-1 flex-col justify-between p-4 md:p-5 lg:p-6">
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
          class="grid shrink-0 grid-cols-2 gap-px bg-base-300/60 sm:grid-cols-4 xl:w-140 xl:grid-cols-2"
        >
          <div
            class="col-span-2 flex flex-col justify-center bg-base-100 p-4 transition-colors md:p-5 lg:p-6 xl:col-span-1 xl:row-span-2 xl:p-5"
          >
            <span class="text-[10px] font-bold tracking-widest text-base-content/50 uppercase">
              最新總計
            </span>

            <span
              class="mt-1 text-2xl font-black text-primary tabular-nums md:text-3xl xl:text-2xl"
            >
              {{ fmtFare(itinerary.statistics?.latestVal ?? null, baseCurrency) }}
            </span>

            <span
              v-if="itinerary.deadline"
              class="mt-1.5 text-xs font-medium text-base-content/40 tabular-nums"
            >
              門檻：{{
                itinerary.rule37Analysis?.historyBestVal
                  ? fmtFare(itinerary.rule37Analysis.historyBestVal, baseCurrency)
                  : '--'
              }}
            </span>
          </div>

          <div
            class="flex flex-col justify-center bg-base-100 p-4 transition-colors md:p-5 lg:p-6 xl:flex-row xl:items-center xl:justify-between xl:gap-3 xl:px-5 xl:py-3.5"
          >
            <span class="text-[10px] font-bold tracking-widest text-base-content/50 uppercase">
              歷史最低
            </span>

            <span
              class="mt-1 text-base font-black text-success tabular-nums sm:text-lg md:text-xl xl:mt-0 xl:text-lg"
            >
              {{ fmtFare(itinerary.statistics?.allTimeLow ?? null, baseCurrency) }}
            </span>
          </div>

          <div
            class="flex flex-col justify-center bg-base-100 p-4 transition-colors md:p-5 lg:p-6 xl:flex-row xl:items-center xl:justify-between xl:gap-3 xl:px-5 xl:py-3.5"
          >
            <span class="text-[10px] font-bold tracking-widest text-base-content/50 uppercase">
              歷史最高
            </span>

            <span
              class="mt-1 text-base font-black text-error tabular-nums sm:text-lg md:text-xl xl:mt-0 xl:text-lg"
            >
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

    <dialog class="modal" :class="{ 'modal-open': showRestoreModal }">
      <div class="modal-box max-w-sm rounded-2xl border border-base-200 bg-base-100 shadow-xl">
        <h3 class="mb-2 text-lg font-extrabold text-base-content">恢復追蹤？</h3>

        <p class="text-sm text-base-content/60">
          確定恢復追蹤「{{ fmtItineraryName(itinerary) }}」？
        </p>

        <p class="mt-1.5 text-sm text-base-content/60">
          若出發日期已過 30 天，此旅程會在下次自動更新時重新封存。
        </p>

        <div class="modal-action mt-6 justify-end gap-2 border-t border-base-200 pt-4">
          <button type="button" class="btn btn-ghost btn-sm" @click="showRestoreModal = false">
            取消
          </button>

          <button
            type="button"
            class="btn px-5 shadow-sm btn-sm btn-primary"
            :disabled="loading === 'restore'"
            @click="runAction('restore')"
          >
            <span v-if="loading === 'restore'" class="loading loading-xs loading-spinner"></span>
            恢復追蹤
          </button>
        </div>
      </div>

      <div
        class="modal-backdrop bg-black/10 backdrop-blur-xs"
        @click="showRestoreModal = false"
      ></div>
    </dialog>

    <dialog class="modal" :class="{ 'modal-open': showArchiveModal }">
      <div class="modal-box max-w-sm rounded-2xl border border-base-200 bg-base-100 shadow-xl">
        <h3 class="mb-2 text-lg font-extrabold text-base-content">封存？</h3>

        <p class="text-sm text-base-content/60">
          確定封存「{{ fmtItineraryName(itinerary) }}」？追蹤將停止，並移至已封存列表。
        </p>

        <div class="modal-action mt-6 justify-end gap-2 border-t border-base-200 pt-4">
          <button type="button" class="btn btn-ghost btn-sm" @click="showArchiveModal = false">
            取消
          </button>

          <button
            type="button"
            class="btn px-5 shadow-sm btn-sm btn-primary"
            :disabled="loading === 'archive'"
            @click="runAction('archive')"
          >
            <span v-if="loading === 'archive'" class="loading loading-xs loading-spinner"></span>
            確認封存
          </button>
        </div>
      </div>

      <div
        class="modal-backdrop bg-black/10 backdrop-blur-xs"
        @click="showArchiveModal = false"
      ></div>
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
