<script setup lang="ts">
import { useForm, Link } from '@inertiajs/vue3'

import AppLayout from '@/Layouts/AppLayout.vue'

const form = useForm({
  origin: '',
  destination: '',
  flight_date: '',
  deadline: '',
})

function submit() {
  form.post('/entries')
}
</script>

<template>
  <AppLayout>
    <div class="mx-auto max-w-2xl rounded-xl border bg-white p-8 shadow-sm">
      <h2 class="mb-6 text-3xl font-bold">追蹤航班</h2>

      <form class="space-y-6" @submit.prevent="submit">
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="mb-1 block text-sm font-medium text-gray-700">出發地</label>

            <input
              v-model="form.origin"
              type="text"
              maxlength="3"
              placeholder="e.g. HKG"
              class="w-full rounded-lg border px-4 py-2 uppercase focus:ring-2 focus:ring-blue-500 focus:outline-none"
              required
            />
          </div>

          <div>
            <label class="mb-1 block text-sm font-medium text-gray-700">目的地</label>

            <input
              v-model="form.destination"
              type="text"
              maxlength="3"
              placeholder="e.g. NRT"
              class="w-full rounded-lg border px-4 py-2 uppercase focus:ring-2 focus:ring-blue-500 focus:outline-none"
              required
            />
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="mb-1 block text-sm font-medium text-gray-700">航班日期</label>

            <input
              v-model="form.flight_date"
              type="date"
              class="w-full rounded-lg border px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:outline-none"
              required
            />
          </div>

          <div>
            <label class="mb-1 block text-sm font-medium text-gray-700">
              期限<span class="font-normal text-gray-400">(選填)</span>
            </label>

            <input
              v-model="form.deadline"
              type="date"
              class="w-full rounded-lg border px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />

            <p class="mt-1 text-xs text-gray-400">37%關鍵日期由今日至期限計算</p>
          </div>
        </div>

        <div class="flex gap-4 pt-2">
          <button
            type="submit"
            class="flex-1 rounded-lg bg-blue-600 py-2.5 font-medium text-white"
            :disabled="form.processing"
          >
            開始追蹤
          </button>

          <Link
            href="/"
            class="flex-1 rounded-lg bg-gray-100 py-2.5 text-center font-medium text-gray-700"
          >
            取消
          </Link>
        </div>
      </form>
    </div>
  </AppLayout>
</template>
