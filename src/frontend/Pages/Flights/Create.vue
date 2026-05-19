<script setup lang="ts">
import AppLayout from '@/Layouts/AppLayout.vue'
import { Link, router } from '@inertiajs/vue3'
import { VueDatePicker } from '@vuepic/vue-datepicker'
import '@vuepic/vue-datepicker/dist/main.css'
import { zhHK } from 'date-fns/locale'
import { ref } from 'vue'
import { useToast } from 'vue-toast-notification'

const toast = useToast()

const form = ref({
  origin: '',
  destination: '',
  flight_date: '',
  deadline: '',
  loading: false,
})

function handleSubmit() {
  form.value.loading = true

  fetch('/api/flights', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      origin: form.value.origin.toUpperCase(),
      destination: form.value.destination.toUpperCase(),
      flight_date: form.value.flight_date,
      deadline: form.value.deadline || null,
    }),
  })
    .then((res) =>
      res.json().then((data) => {
        if (!res.ok) {
          toast.error(data.message || 'Error creating entry')
          return
        }
        toast.success('航班追蹤已建立')
        router.visit(`/flights/${data.data.id}`)
      }),
    )
    .catch((err: unknown) => {
      toast.error(err instanceof Error ? err.message : '未知錯誤')
    })
    .finally(() => {
      form.value.loading = false
    })
}
</script>

<template>
  <AppLayout>
    <div class="mb-8">
      <h2 class="text-3xl font-extrabold tracking-tight text-base-content">追蹤新航班</h2>

      <p class="mt-2 text-sm font-medium text-base-content/65">
        輸入航班資訊，系統會依照排程抓取最新票價並建立價格歷史。
      </p>
    </div>

    <div class="tracker-panel card mb-6 rounded-lg">
      <div class="card-body p-6 md:p-8">
        <h3 class="mb-3 text-base font-bold text-base-content">購買時機分析原理</h3>

        <div class="space-y-3 text-sm leading-relaxed text-base-content/70">
          <p>
            PoorFlyer 採用<span class="font-semibold text-base-content">「37% 法則」</span
            >來判斷購票時機。這是一個來自最優停止理論（Optimal Stopping
            Theory）的數學策略，用於在有限時間內做出最優決策。
          </p>

          <p>運作方式：當你設定購票限期後，系統會將整段觀察期分為兩個階段——</p>

          <ul class="list-inside list-disc space-y-1.5 pl-1">
            <li>
              <span class="font-semibold text-base-content">觀察期</span>

              （前 37% 時間）：純粹收集數據，記錄出現過的最低票價作為基準。
            </li>

            <li>
              <span class="font-semibold text-base-content">決策期</span>

              （後 63% 時間）：一旦出現低於觀察期最低價的票價，即發出<span
                class="font-medium text-success"
                >購買信號</span
              >。
            </li>
          </ul>

          <p class="text-xs text-base-content/50">
            設定購票限期為選填項目。若不設定，系統仍會持續追蹤票價歷史，但不會提供購買時機建議。
          </p>
        </div>
      </div>
    </div>

    <div class="tracker-panel card rounded-lg">
      <div class="card-body gap-8 p-8">
        <form class="space-y-6" @submit.prevent="handleSubmit">
          <div class="grid gap-6 md:grid-cols-2">
            <fieldset class="fieldset">
              <legend class="fieldset-legend text-sm font-bold">出發地機場代碼</legend>

              <input
                v-model="form.origin"
                type="text"
                maxlength="3"
                placeholder="例如: HKG"
                class="input-bordered input input-lg w-full uppercase"
                required
                :disabled="form.loading"
              />
            </fieldset>

            <fieldset class="fieldset">
              <legend class="fieldset-legend text-sm font-bold">目的地機場代碼</legend>

              <input
                v-model="form.destination"
                type="text"
                maxlength="3"
                placeholder="例如: NRT"
                class="input-bordered input input-lg w-full uppercase"
                required
                :disabled="form.loading"
              />
            </fieldset>
          </div>

          <div class="grid gap-6 md:grid-cols-2">
            <fieldset class="fieldset">
              <legend class="fieldset-legend text-sm font-bold">目標出發日期</legend>

              <VueDatePicker
                v-model="form.flight_date"
                :enable-time-picker="false"
                :locale="zhHK"
                auto-apply
                model-type="yyyy-MM-dd"
                teleport="body"
              >
                <template #trigger>
                  <input
                    type="text"
                    :value="form.flight_date"
                    placeholder="選擇日期"
                    class="input-bordered input input-lg w-full cursor-pointer"
                    readonly
                    required
                    :disabled="form.loading"
                  />
                </template>
              </VueDatePicker>
            </fieldset>

            <fieldset class="fieldset">
              <legend class="fieldset-legend text-sm font-bold">
                購票限期
                <span class="text-base-content/50">（選填）</span>
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
                    class="input-bordered input input-lg w-full cursor-pointer"
                    readonly
                    :disabled="form.loading"
                  />
                </template>
              </VueDatePicker>

              <p class="label text-xs text-base-content/55">系統將依此計算最佳購買時機</p>
            </fieldset>
          </div>

          <div class="flex flex-col gap-3 border-t border-base-300/70 pt-5 sm:flex-row">
            <Link href="/flights/" class="btn flex-1 btn-ghost btn-lg">取消</Link>

            <button type="submit" class="btn flex-1 btn-lg btn-primary" :disabled="form.loading">
              <span v-if="form.loading" class="loading loading-sm loading-spinner"></span>
              {{ form.loading ? '設定中...' : '開始追蹤' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </AppLayout>
</template>
