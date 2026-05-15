<script setup lang="ts">
import AppLayout from '@/Layouts/AppLayout.vue'
import { Link, router } from '@inertiajs/vue3'
import { VueDatePicker } from '@vuepic/vue-datepicker'
import '@vuepic/vue-datepicker/dist/main.css'
import { zhHK } from 'date-fns/locale'
import { ref } from 'vue'

const form = ref({
  origin: '',
  destination: '',
  flight_date: '',
  deadline: '',
  loading: false,
  error: '',
})

async function handleSubmit() {
  form.value.error = ''
  form.value.loading = true

  try {
    const res = await fetch('/api/flights', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        origin: form.value.origin.toUpperCase(),
        destination: form.value.destination.toUpperCase(),
        flight_date: form.value.flight_date,
        deadline: form.value.deadline || null,
      }),
    })

    if (!res.ok) {
      const data = await res.json()
      form.value.error = data.message || 'Error creating entry'
      return
    }

    const data = await res.json()
    router.visit(`/flights/${data.data.id}`)
  } catch (err) {
    form.value.error = err instanceof Error ? err.message : '未知錯誤'
  } finally {
    form.value.loading = false
  }
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

    <div class="mx-auto max-w-2xl">
      <div class="tracker-panel card rounded-lg">
        <div class="card-body gap-8 p-8">
          <form class="space-y-6" @submit.prevent="handleSubmit">
            <div v-if="form.error" class="alert rounded-[1.25rem] alert-error">
              <span>{{ form.error }}</span>
            </div>

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
              <Link href="/flights/" class="btn flex-1 btn-ghost btn-lg">取消返回</Link>

              <button type="submit" class="btn flex-1 btn-lg btn-primary" :disabled="form.loading">
                <span v-if="form.loading" class="loading loading-sm loading-spinner"></span>
                {{ form.loading ? '設定中...' : '開始追蹤' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </AppLayout>
</template>
