<script setup lang="ts">
import FetchFilters from '@/Components/FetchFilters.vue'
import AppLayout from '@/Layouts/AppLayout.vue'
import { Link, router } from '@inertiajs/vue3'
import { VueDatePicker } from '@vuepic/vue-datepicker'
import '@vuepic/vue-datepicker/dist/main.css'
import { zhHK } from 'date-fns/locale'
import { computed, ref, watch } from 'vue'
import { useToast } from 'vue-toast-notification'

const toast = useToast()

const form = ref({
  tripType: 'SINGLE',
  deadline: '',
  isActive: true,
  flights: [{ origin: '', destination: '', flightDate: '' }],
  processing: false,
})

const filters = ref<{
  cabinClass: string
  maxStops: string
  airlines: string[] | null
}>({
  cabinClass: '',
  maxStops: '',
  airlines: null,
})

const roundTripDates = computed({
  get: () => [form.value.flights[0]?.flightDate, form.value.flights[1]?.flightDate].filter(Boolean),
  set: (val) => {
    if (form.value.flights[0]) form.value.flights[0].flightDate = val?.[0] || ''
    if (form.value.flights[1]) form.value.flights[1].flightDate = val?.[1] || ''
  },
})

const getStartDate = (index: number) => {
  const prevDate = form.value.flights[index - 1]?.flightDate
  return prevDate ? new Date(prevDate) : new Date()
}

const latestFlightDate = computed(() => {
  const times = form.value.flights
    .map((f) => f.flightDate)
    .filter(Boolean)
    .map((d) => new Date(d).getTime())
  return times.length ? new Date(Math.max(...times)) : new Date()
})

const deadlineMarkers = computed(() =>
  form.value.flights
    .map((f, i) =>
      f.flightDate
        ? {
            date: f.flightDate,
            type: 'dot' as const,
            color: '#10b981',
            tooltip: [
              {
                text:
                  form.value.tripType === 'ROUND_TRIP'
                    ? i === 0
                      ? '去程'
                      : '回程'
                    : `航段 ${i + 1}`,
              },
            ],
          }
        : null,
    )
    .filter(Boolean),
)

watch(
  () => form.value.tripType,
  (newVal) => {
    if (newVal === 'SINGLE') {
      form.value.flights = [
        form.value.flights[0] || { origin: '', destination: '', flightDate: '' },
      ]
    } else if (newVal === 'ROUND_TRIP') {
      form.value.flights = [
        form.value.flights[0] || { origin: '', destination: '', flightDate: '' },
        { origin: '', destination: '', flightDate: '' },
      ]
    } else if (newVal === 'MULTI_CITY') {
      form.value.flights = [
        form.value.flights[0] || { origin: '', destination: '', flightDate: '' },
        form.value.flights[1] || { origin: '', destination: '', flightDate: '' },
      ]
    }
  },
)

function submit() {
  form.value.processing = true

  const payload = {
    trip_type: form.value.tripType,
    deadline: form.value.deadline || null,
    is_active: form.value.isActive,
    cabin_class: filters.value.cabinClass || null,
    max_stops: filters.value.maxStops || null,
    ...(filters.value.airlines ? { airlines: filters.value.airlines } : {}),
    flights: form.value.flights.map((leg, i) => {
      const isRoundTripReturn = form.value.tripType === 'ROUND_TRIP' && i === 1
      return {
        origin: (isRoundTripReturn ? form.value.flights[0].destination : leg.origin).toUpperCase(),
        destination: (isRoundTripReturn
          ? form.value.flights[0].origin
          : leg.destination
        ).toUpperCase(),
        flight_date: leg.flightDate,
      }
    }),
  }

  router.post('/itineraries', payload, {
    preserveScroll: true,
    onSuccess: () => toast.success('已成功建立票價追蹤'),
    onError: (errors) => toast.error(errors.itinerary ?? '新增失敗，請檢查輸入內容'),
    onFinish: () => {
      form.value.processing = false
    },
  })
}
</script>

<template>
  <AppLayout>
    <div class="mb-8 flex flex-col gap-2">
      <div class="breadcrumbs text-sm text-base-content/60">
        <ul>
          <li><Link href="/">追蹤清單</Link></li>

          <li>建立新旅程</li>
        </ul>
      </div>

      <div>
        <h2 class="text-3xl font-extrabold tracking-tight text-base-content">建立新旅程</h2>

        <p class="mt-2 text-base-content/70">
          輸入你想追蹤的航段資料，系統將依排程自動追蹤並記錄機票價格變動。
        </p>
      </div>
    </div>

    <div class="card mb-6 rounded-2xl border border-base-200 bg-base-100 shadow-sm">
      <div class="card-body p-6 md:p-8">
        <h3 class="mb-3 text-lg font-bold text-base-content">最佳購買時機分析原理</h3>

        <div class="space-y-3 text-sm leading-relaxed text-base-content/70">
          <p>
            PoorFlyer 採用<span class="font-semibold text-base-content">「37% 法則」</span>
            判斷黃金購票時機。此策略源自數學的「最佳停止理論」（Optimal Stopping
            Theory），旨在有限時間及選擇內找出最的選項。
          </p>

          <p>運作原理：設定購票限期後，系統會將整個觀察期自動分為兩個階段：</p>

          <ul class="list-inside list-disc space-y-1.5 pl-1">
            <li>
              <span class="font-semibold text-base-content">數據觀察期</span>（前 37%
              時間）：純粹收集票價，記錄期間出現過的最低價格作為「對比基準」。
            </li>

            <li>
              <span class="font-semibold text-base-content">決策期</span>

              （後 63% 時間）：一旦票價跌穿觀察期的最低價格，系統便會發出
              <span class="font-medium text-success">入手訊號 </span>
              。
            </li>
          </ul>

          <p class="mt-2 text-xs text-base-content/50">
            *
            購票限期為選填項目。若未有設定，系統仍會持續記錄歷史票價並繪製趨勢圖，但不會提供購票時機建議。
          </p>
        </div>
      </div>
    </div>

    <div class="card rounded-2xl border border-base-200 bg-base-100 shadow-sm">
      <div class="card-body gap-8 p-6 md:p-8">
        <form class="space-y-8" @submit.prevent="submit">
          <fieldset class="fieldset">
            <legend class="fieldset-legend mb-2 text-sm font-bold">航程類型</legend>

            <div class="join grid w-full max-w-md grid-cols-3">
              <input
                v-model="form.tripType"
                class="btn join-item"
                type="radio"
                name="tripType"
                value="SINGLE"
                aria-label="單程"
              />

              <input
                v-model="form.tripType"
                class="btn join-item"
                type="radio"
                name="tripType"
                value="ROUND_TRIP"
                aria-label="來回"
              />

              <input
                v-model="form.tripType"
                class="btn join-item"
                type="radio"
                name="tripType"
                value="MULTI_CITY"
                aria-label="多城市"
              />
            </div>
          </fieldset>

          <div class="space-y-6">
            <div v-for="(leg, index) in form.flights" :key="index">
              <div
                v-if="form.tripType !== 'ROUND_TRIP' || index === 0"
                class="relative rounded-xl border border-base-200 bg-base-200/20 p-5 transition-all hover:border-primary/30"
              >
                <div class="mb-5 flex items-center gap-3 border-b border-base-200 pb-3">
                  <h4 class="font-bold text-base-content">
                    {{ form.tripType === 'MULTI_CITY' ? `第 ${index + 1} 航段資料` : '航段資料' }}
                  </h4>
                </div>

                <div class="grid gap-4 md:grid-cols-3">
                  <fieldset class="fieldset">
                    <legend class="fieldset-legend text-sm font-bold">出發地 (IATA 代碼)</legend>

                    <input
                      v-model="leg.origin"
                      type="text"
                      placeholder="例如: HKG"
                      class="input-bordered input w-full uppercase transition-colors focus:input-primary"
                      required
                      maxlength="3"
                      :disabled="form.processing"
                    />
                  </fieldset>

                  <fieldset class="fieldset">
                    <legend class="fieldset-legend text-sm font-bold">目的地 (IATA 代碼)</legend>

                    <input
                      v-model="leg.destination"
                      type="text"
                      placeholder="例如: NRT"
                      class="input-bordered input w-full uppercase transition-colors focus:input-primary"
                      required
                      maxlength="3"
                      :disabled="form.processing"
                    />
                  </fieldset>

                  <fieldset class="fieldset">
                    <legend class="fieldset-legend text-sm font-bold">
                      {{ form.tripType === 'ROUND_TRIP' ? '去程及回程日期' : '出發日期' }}
                    </legend>

                    <VueDatePicker
                      v-if="form.tripType === 'ROUND_TRIP'"
                      v-model="roundTripDates"
                      range
                      :enable-time-picker="false"
                      :locale="zhHK"
                      auto-apply
                      model-type="yyyy-MM-dd"
                      teleport="body"
                    >
                      <template #trigger>
                        <input
                          type="text"
                          :value="
                            roundTripDates.length === 2
                              ? `${roundTripDates[0]} 至 ${roundTripDates[1]}`
                              : ''
                          "
                          placeholder="選擇日期"
                          class="input-bordered input w-full cursor-pointer transition-colors focus:input-primary"
                          readonly
                          required
                          :disabled="form.processing"
                        />
                      </template>
                    </VueDatePicker>

                    <VueDatePicker
                      v-else
                      v-model="leg.flightDate"
                      :start-date="getStartDate(index)"
                      :enable-time-picker="false"
                      :locale="zhHK"
                      auto-apply
                      model-type="yyyy-MM-dd"
                      teleport="body"
                    >
                      <template #trigger>
                        <input
                          type="text"
                          :value="leg.flightDate"
                          placeholder="選擇日期"
                          class="input-bordered input w-full cursor-pointer transition-colors focus:input-primary"
                          readonly
                          required
                          :disabled="form.processing"
                        />
                      </template>
                    </VueDatePicker>
                  </fieldset>
                </div>
              </div>
            </div>
          </div>

          <div class="divider text-base-content/30">分析設定</div>

          <div class="grid gap-4 md:grid-cols-2">
            <fieldset class="fieldset">
              <legend class="fieldset-legend text-sm font-bold">
                最遲購票限期 <span class="font-normal text-base-content/50">（選填）</span>
              </legend>

              <VueDatePicker
                v-model="form.deadline"
                :start-date="latestFlightDate"
                :markers="deadlineMarkers"
                :enable-time-picker="false"
                :locale="zhHK"
                auto-apply
                model-type="yyyy-MM-dd"
                teleport="body"
              >
                <template #trigger>
                  <input
                    type="text"
                    :value="form.deadline"
                    placeholder="選擇日期"
                    class="input-bordered input w-full cursor-pointer transition-colors focus:input-primary"
                    readonly
                  />
                </template>
              </VueDatePicker>

              <p class="label mt-1 p-0 text-xs text-base-content/55">
                設定限期後系統方可計算最佳購買時機
              </p>
            </fieldset>

            <fieldset class="fieldset justify-end">
              <label
                class="cursor-pointer.justify-start label gap-4 rounded-xl border border-base-200 bg-base-200/20 p-4 transition-colors hover:border-success/30"
              >
                <input
                  v-model="form.isActive"
                  type="checkbox"
                  class="toggle toggle-success"
                  :disabled="form.processing"
                />

                <div>
                  <span class="label-text block text-sm font-bold">啟用自動追蹤</span>

                  <span class="label-text-alt text-base-content/60">每日自動更新並記錄票價</span>
                </div>
              </label>
            </fieldset>
          </div>

          <div class="divider text-base-content/30">搜尋條件</div>

          <div>
            <p class="mb-3 text-xs text-base-content/55">
              留空表示套用系統預設；航空公司全部未選則不作限制。
            </p>

            <FetchFilters v-model="filters" />
          </div>

          <div class="mt-8 flex flex-col gap-3 border-t border-base-300/70 pt-5 sm:flex-row">
            <Link href="/" class="btn flex-1 btn-ghost">取消</Link>

            <button
              type="submit"
              class="btn flex-1 shadow-sm btn-primary"
              :disabled="form.processing"
            >
              <span v-if="form.processing" class="loading loading-spinner"></span>
              {{ form.processing ? '處理中...' : '建立' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </AppLayout>
</template>
