<script setup lang="ts">
import AppLayout from '@/Layouts/AppLayout.vue'
import { Link, router } from '@inertiajs/vue3'
import { ref, watch } from 'vue'
import { useToast } from 'vue-toast-notification'

import { VueDatePicker } from '@vuepic/vue-datepicker'
import '@vuepic/vue-datepicker/dist/main.css'
import { zhHK } from 'date-fns/locale'

const toast = useToast()

// Swapped useForm for a standard reactive ref
const form = ref({
  tripType: 'SINGLE',
  deadline: '',
  isActive: true,
  flights: [{ origin: '', destination: '', flightDate: '' }],
  processing: false,
})

// Handle trip type changes to automatically adjust flight legs
watch(
  () => form.value.tripType,
  (newVal) => {
    if (newVal === 'SINGLE') {
      form.value.flights = [
        form.value.flights[0] ?? { origin: '', destination: '', flightDate: '' },
      ]
    } else if (newVal === 'ROUND_TRIP') {
      form.value.flights = [
        form.value.flights[0],
        {
          origin: form.value.flights[0]?.destination || '',
          destination: form.value.flights[0]?.origin || '',
          flightDate: form.value.flights[1]?.flightDate || '',
        },
      ]
    } else if (newVal === 'MULTI_CITY') {
      form.value.flights = [
        form.value.flights[0],
        form.value.flights[1] ?? { origin: '', destination: '', flightDate: '' },
      ]
    }
  },
)

// Auto-sync airports for the return leg if the user modifies the first leg during a ROUND_TRIP
watch(
  () => [form.value.flights[0]?.origin, form.value.flights[0]?.destination],
  ([newOrigin, newDest]) => {
    if (form.value.tripType === 'ROUND_TRIP' && form.value.flights.length > 1) {
      form.value.flights[1].origin = newDest || ''
      form.value.flights[1].destination = newOrigin || ''
    }
  },
  { deep: true },
)

function submit() {
  form.value.processing = true

  // Format the payload to match backend snake_case expectations
  const payload = {
    trip_type: form.value.tripType,
    deadline: form.value.deadline || null,
    is_active: form.value.isActive,
    flights: form.value.flights.map((leg) => ({
      origin: leg.origin,
      destination: leg.destination,
      flight_date: leg.flightDate,
    })),
  }

  fetch('/api/flights', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
    .then((res) =>
      res.json().then((data) => {
        if (!res.ok) {
          toast.error(data.message || '建立失敗，請檢查輸入內容')
          return
        }

        toast.success('航班追蹤已建立')
        // Manually trigger Inertia navigation to the home page
        router.visit('/')
      }),
    )
    .catch((err) => {
      toast.error(err instanceof Error ? err.message : '未知錯誤')
    })
    .finally(() => {
      form.value.processing = false
    })
}
</script>

<template>
  <AppLayout>
    <div class="mb-8 flex flex-col gap-2">
      <div class="breadcrumbs text-sm text-base-content/60">
        <ul>
          <li><Link href="/">追蹤清單</Link></li>

          <li>新增航班</li>
        </ul>
      </div>

      <div>
        <h2 class="text-3xl font-extrabold tracking-tight text-base-content">建立新追蹤</h2>

        <p class="mt-2 text-base-content/70">輸入航班資訊，系統會依照排程收集機票價格資料。</p>
      </div>
    </div>

    <div class="card mb-6 rounded-2xl border border-base-200 bg-base-100 shadow-sm">
      <div class="card-body p-6 md:p-8">
        <h3 class="mb-3 text-lg font-bold text-base-content">購買時機分析原理</h3>

        <div class="space-y-3 text-sm leading-relaxed text-base-content/70">
          <p>
            PoorFlyer 採用<span class="font-semibold text-base-content">「37% 法則」</span>
            來判斷購票時機。這是一個來自最優停止理論（Optimal Stopping
            Theory）的數學策略，用於在有限時間內做出最優決策。
          </p>

          <p>運作方式：當你設定購票限期後，系統會將整段觀察期分為兩個階段：</p>

          <ul class="list-inside list-disc space-y-1.5 pl-1">
            <li>
              <span class="font-semibold text-base-content">觀察期</span>
              （前 37% 時間）：收集數據，記錄出現過的最低票價格作為基準。
            </li>

            <li>
              <span class="font-semibold text-base-content">決策期</span>

              （後 63% 時間）：一旦出現低於觀察期最低價的票價，即發出<span
                class="font-medium text-success"
                >購買信號</span
              >。
            </li>
          </ul>

          <p class="mt-2 text-xs text-base-content/50">
            設定購票限期為選填項目。若不設定，系統仍會持續追蹤票價歷史，但不會提供購買時機建議。
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
            <div
              v-for="(leg, index) in form.flights"
              :key="index"
              class="relative rounded-xl border border-base-200 bg-base-200/20 p-5 transition-all hover:border-primary/30"
            >
              <div class="mb-5 flex items-center gap-3 border-b border-base-200 pb-3">
                <div
                  class="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-sm font-bold text-primary"
                >
                  {{ index + 1 }}
                </div>

                <h4 class="font-bold text-base-content">
                  {{
                    index === 0
                      ? '去程航班'
                      : form.tripType === 'ROUND_TRIP'
                        ? '回程航班'
                        : '第二航段'
                  }}
                </h4>
              </div>

              <div class="grid gap-6 md:grid-cols-3">
                <fieldset class="fieldset">
                  <legend class="fieldset-legend text-sm font-bold">出發地機場代碼</legend>

                  <input
                    v-model="leg.origin"
                    type="text"
                    placeholder="如: HKG"
                    class="input-bordered input w-full uppercase transition-colors focus:input-primary"
                    :readonly="form.tripType === 'ROUND_TRIP' && index === 1"
                    :class="{
                      'bg-base-200 text-base-content/50':
                        form.tripType === 'ROUND_TRIP' && index === 1,
                    }"
                    required
                    maxlength="3"
                    :disabled="form.processing"
                  />
                </fieldset>

                <fieldset class="fieldset">
                  <legend class="fieldset-legend text-sm font-bold">目的地機場代碼</legend>

                  <input
                    v-model="leg.destination"
                    type="text"
                    placeholder="如: NRT"
                    class="input-bordered input w-full uppercase transition-colors focus:input-primary"
                    :readonly="form.tripType === 'ROUND_TRIP' && index === 1"
                    :class="{
                      'bg-base-200 text-base-content/50':
                        form.tripType === 'ROUND_TRIP' && index === 1,
                    }"
                    required
                    maxlength="3"
                    :disabled="form.processing"
                  />
                </fieldset>

                <fieldset class="fieldset">
                  <legend class="fieldset-legend text-sm font-bold">目標出發日期</legend>

                  <VueDatePicker
                    v-model="leg.flightDate"
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

          <div class="divider text-base-content/30">進階設定</div>

          <div class="grid gap-6 md:grid-cols-2">
            <fieldset class="fieldset">
              <legend class="fieldset-legend text-sm font-bold">
                購票限期 <span class="font-normal text-base-content/50">（選填）</span>
              </legend>

              <VueDatePicker
                v-model="form.deadline"
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
                    :disabled="form.processing"
                  />
                </template>
              </VueDatePicker>

              <p class="label mt-1 p-0 text-xs text-base-content/55">設定後將啟用購買時機分析</p>
            </fieldset>

            <fieldset class="fieldset justify-end">
              <label
                class="label cursor-pointer justify-start gap-4 rounded-xl border border-base-200 bg-base-200/20 p-4 transition-colors hover:border-success/30"
              >
                <input
                  v-model="form.isActive"
                  type="checkbox"
                  class="toggle toggle-success"
                  :disabled="form.processing"
                />

                <div>
                  <span class="label-text block text-sm font-bold">啟用追蹤</span>

                  <span class="label-text-alt text-base-content/60">建立後將自動收集票價</span>
                </div>
              </label>
            </fieldset>
          </div>

          <div class="mt-8 flex flex-col gap-3 border-t border-base-300/70 pt-5 sm:flex-row">
            <Link href="/" class="btn flex-1 btn-ghost">取消</Link>

            <button
              type="submit"
              class="btn flex-1 shadow-sm btn-primary"
              :disabled="form.processing"
            >
              <span v-if="form.processing" class="loading loading-spinner"></span>
              {{ form.processing ? '設定中...' : '建立追蹤' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </AppLayout>
</template>
