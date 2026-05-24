<script setup lang="ts">
import FareGraph from '@/Components/FareGraph.vue'
import FaretList from '@/Components/FareList.vue'
import AppLayout from '@/Layouts/AppLayout.vue'
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

const activeTab = ref('0')
const loading = ref<string | null>(null)

const showModal = ref(false)
const deadlineValue = ref(props.itinerary.deadline || '')

const openEditModal = () => {
  deadlineValue.value = props.itinerary.deadline || ''
  showModal.value = true
}

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
  if (action === 'delete' && !confirm('確定刪除此追蹤？')) {
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
          <div class="flex items-start justify-between gap-4">
            <div>
              <h3 class="flex items-center gap-2 text-base font-bold text-base-content">
                {{ fmtItineraryName(itinerary) }}
              </h3>

              <p class="mt-0.5 text-sm font-medium text-base-content/60">
                出發日期：{{ fmtDate(itinerary.flights[0].flightDate) }}
                <span v-if="itinerary.deadline" class="mx-2 text-base-content/30">|</span>

                <span v-if="itinerary.deadline">購票限期：{{ fmtDate(itinerary.deadline) }}</span>
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
              :disabled="loading === 'delete'"
              @click="runAction('delete')"
            >
              <Icon
                :icon="loading === 'delete' ? 'mdi:loading' : 'mdi:delete'"
                :class="{ 'animate-spin': loading === 'delete' }"
              />
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
        <div class="flex flex-1 flex-col justify-center p-5 sm:p-6">
          <template v-if="itinerary.deadline && itinerary.rule37Analysis?.phase">
            <div class="flex items-center gap-3">
              <span
                class="status status-lg shadow-sm"
                :class="{
                  'animate-pulse status-success': itinerary.rule37Analysis.phase === 'BUY_SIGNAL',
                  'status-neutral': itinerary.rule37Analysis.phase === 'OBSERVING',
                  'status-info': itinerary.rule37Analysis.phase === 'WAITING',
                }"
              ></span>

              <span
                class="text-xl font-extrabold tracking-tight"
                :class="{
                  'text-success': itinerary.rule37Analysis.phase === 'BUY_SIGNAL',
                  'text-neutral': itinerary.rule37Analysis.phase === 'OBSERVING',
                  'text-info': itinerary.rule37Analysis.phase === 'WAITING',
                }"
              >
                {{
                  itinerary.rule37Analysis.phase === 'BUY_SIGNAL'
                    ? '入手訊號'
                    : itinerary.rule37Analysis.phase === 'OBSERVING'
                      ? '數據觀察期'
                      : '決策期'
                }}
              </span>

              <span
                v-if="itinerary.rule37Analysis.phase === 'OBSERVING'"
                class="badge badge-outline px-2 badge-sm font-semibold"
              >
                {{ calculateDaysRemaining(itinerary.rule37Analysis.cutoffDate) }} 天後結束 天後結束
              </span>
            </div>

            <p class="mt-2 text-xs font-medium text-base-content/60">
              <span v-if="itinerary.rule37Analysis.phase === 'BUY_SIGNAL'">
                最新總計已跌穿觀察期錄得的最低價格。
              </span>

              <span v-else-if="itinerary.rule37Analysis.phase === 'OBSERVING'">
                系統現正收集票價數據，決策期將於
                <span class="font-bold">{{ fmtDate(itinerary.rule37Analysis.cutoffDate) }}</span>
                開始。
              </span>

              <span v-else>已進入決策階段。只要總價低於對比基準，系統便會即時提示你出手。</span>
            </p>
          </template>

          <template v-else-if="itinerary.deadline">
            <div class="flex items-center gap-3">
              <span class="status status-lg status-warning shadow-sm"></span>

              <span class="text-xl font-extrabold tracking-tight text-warning">收集數據中</span>
            </div>

            <p class="mt-2 text-sm font-medium text-base-content/60">未有足夠數據分析購買時機。</p>
          </template>

          <template v-else>
            <div class="flex items-center gap-3">
              <span class="status status-lg status-neutral opacity-40"></span>

              <span class="text-xl font-extrabold tracking-tight text-base-content/40">
                未啟用數據分析
              </span>
            </div>

            <p class="mt-2 text-sm font-medium text-base-content/60">
              <button class="inline-block link font-bold link-primary" @click="openEditModal">
                設定購票限期
              </button>
              以啟用購買時機分析。
            </p>
          </template>
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
              <template v-if="itinerary.rule37Analysis?.historyBestVal">
                門檻：{{ fmtFare(itinerary.rule37Analysis.historyBestVal, baseCurrency) }}
              </template>

              <template v-else-if="itinerary.deadline">觀察中...</template>
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
            價格趨勢圖
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
  </AppLayout>
</template>
