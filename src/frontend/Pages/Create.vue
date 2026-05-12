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
    const res = await fetch('/api/entries', {
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
    router.visit(`/detail/${data.data.id}`)
  } catch (err) {
    form.value.error = err instanceof Error ? err.message : '未知錯誤'
  } finally {
    form.value.loading = false
  }
}
</script>

<template>
  <AppLayout>
    <div class="mx-auto max-w-2xl">
      <div class="mb-8">
        <Link
          href="/"
          class="text-sm font-medium text-gray-500 transition-colors hover:text-gray-900"
          >← 返回列表</Link
        >
      </div>

      <div class="overflow-hidden rounded-3xl border border-gray-200 bg-white shadow-sm">
        <div class="border-b border-gray-100 bg-gray-50/50 px-8 py-6">
          <h2 class="text-2xl font-black tracking-tight text-gray-900">追蹤新航班</h2>

          <p class="mt-1 text-sm font-medium text-gray-500">
            輸入航班資訊，我們將每日為您自動追蹤最低票價。
          </p>
        </div>

        <form class="p-8" @submit.prevent="handleSubmit">
          <div v-if="form.error" class="mb-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3">
            <p class="text-sm font-medium text-red-700">{{ form.error }}</p>
          </div>

          <div class="mb-6 grid grid-cols-2 gap-6">
            <div>
              <label class="mb-2 block text-sm font-bold tracking-wide text-gray-700"
                >出發地機場代碼</label
              >

              <input
                v-model="form.origin"
                type="text"
                maxlength="3"
                placeholder="例如: HKG"
                class="w-full rounded-xl border border-gray-300 bg-gray-50/50 px-4 py-3 font-semibold text-gray-900 uppercase transition-all placeholder:font-normal focus:border-blue-500 focus:bg-white focus:ring-4 focus:ring-blue-500/10 focus:outline-none"
                required
                :disabled="form.loading"
              />
            </div>

            <div>
              <label class="mb-2 block text-sm font-bold tracking-wide text-gray-700"
                >目的地機場代碼</label
              >

              <input
                v-model="form.destination"
                type="text"
                maxlength="3"
                placeholder="例如: NRT"
                class="w-full rounded-xl border border-gray-300 bg-gray-50/50 px-4 py-3 font-semibold text-gray-900 uppercase transition-all placeholder:font-normal focus:border-blue-500 focus:bg-white focus:ring-4 focus:ring-blue-500/10 focus:outline-none"
                required
                :disabled="form.loading"
              />
            </div>
          </div>

          <div class="mb-8 grid grid-cols-2 gap-6">
            <div>
              <label class="mb-2 block text-sm font-bold tracking-wide text-gray-700"
                >目標出發日期</label
              >

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
                    class="w-full cursor-pointer rounded-xl border border-gray-300 bg-gray-50/50 px-4 py-3 font-medium text-gray-900 transition-all focus:border-blue-500 focus:bg-white focus:ring-4 focus:ring-blue-500/10 focus:outline-none"
                    readonly
                    required
                    :disabled="form.loading"
                  />
                </template>
              </VueDatePicker>
            </div>

            <div>
              <label class="mb-2 block text-sm font-bold tracking-wide text-gray-700">
                最遲購票期限 <span class="font-medium text-gray-400">(選填)</span>
              </label>

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
                    class="w-full cursor-pointer rounded-xl border border-gray-300 bg-gray-50/50 px-4 py-3 font-medium text-gray-900 transition-all focus:border-blue-500 focus:bg-white focus:ring-4 focus:ring-blue-500/10 focus:outline-none"
                    readonly
                    :disabled="form.loading"
                  />
                </template>
              </VueDatePicker>

              <p class="mt-2 text-xs font-medium text-gray-400">系統將依此計算 37% 最佳購買時機</p>
            </div>
          </div>

          <div class="flex gap-4 border-t border-gray-100 pt-4">
            <Link
              href="/"
              class="flex-1 rounded-xl bg-gray-100 py-3.5 text-center text-sm font-bold text-gray-600 transition-colors hover:bg-gray-200"
            >
              取消返回
            </Link>

            <button
              type="submit"
              class="flex-2 rounded-xl bg-blue-600 py-3.5 text-sm font-bold text-white shadow-sm transition-all hover:bg-blue-500 hover:shadow-md disabled:opacity-50"
              :disabled="form.loading"
            >
              {{ form.loading ? '設定中...' : '開始自動追蹤' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </AppLayout>
</template>
