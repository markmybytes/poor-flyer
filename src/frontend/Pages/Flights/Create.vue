<script setup lang="ts">
import AppLayout from '@/Layouts/AppLayout.vue'
import { Link, useForm } from '@inertiajs/vue3'
import { watch } from 'vue'

const form = useForm({
  tripType: 'SINGLE',
  deadline: '',
  isActive: true,
  flights: [{ origin: '', destination: '', flightDate: '' }],
})

function addLeg() {
  form.flights.push({ origin: '', destination: '', flightDate: '' })
}

function removeLeg(index: number) {
  if (form.flights.length > 1) {
    form.flights.splice(index, 1)
  }
}

watch(
  () => form.tripType,
  (newVal) => {
    if (newVal === 'SINGLE') {
      form.flights = [form.flights[0] ?? { origin: '', destination: '', flightDate: '' }]
    } else if (newVal === 'ROUND_TRIP') {
      if (form.flights.length === 1) {
        form.flights.push({
          origin: form.flights[0].destination,
          destination: form.flights[0].origin,
          flightDate: '',
        })
      } else {
        form.flights = form.flights.slice(0, 2)
      }
    }
  },
)

function submit() {
  form.post('/api/flights', {
    onSuccess: () => {
      // Maybe redirect via inertia automatically handled by server
    },
  })
}
</script>

<template>
  <AppLayout>
    <div class="mb-8 flex items-center justify-between">
      <div>
        <div class="breadcrumbs mb-2 text-sm">
          <ul>
            <li><Link href="/">追蹤清單</Link></li>
            <li>新增航班</li>
          </ul>
        </div>
        <h2 class="text-3xl font-extrabold tracking-tight text-base-content">建立新追蹤</h2>
      </div>
    </div>

    <div class="tracker-panel max-w-2xl rounded-xl p-6 sm:p-8">
      <form @submit.prevent="submit" class="space-y-6">
        <div class="form-control">
          <label class="label">
            <span class="label-text font-bold">航程類型</span>
          </label>
          <select v-model="form.tripType" class="select-bordered select w-full">
            <option value="SINGLE">單程</option>
            <option value="ROUND_TRIP">來回</option>
            <option value="MULTI_CITY">多城市</option>
          </select>
        </div>

        <div class="space-y-4">
          <div
            v-for="(leg, index) in form.flights"
            :key="index"
            class="rounded-lg border bg-base-200/50 p-4"
          >
            <div class="mb-4 flex items-center justify-between">
              <h4 class="font-bold">航段 {{ index + 1 }}</h4>
              <button
                v-if="form.tripType === 'MULTI_CITY' && form.flights.length > 1"
                type="button"
                @click="removeLeg(index)"
                class="btn text-error btn-ghost btn-sm"
              >
                移除
              </button>
            </div>

            <div class="grid gap-4 sm:grid-cols-2">
              <div class="form-control">
                <label class="label">
                  <span class="label-text font-bold">出發地</span>
                </label>
                <input
                  v-model="leg.origin"
                  type="text"
                  placeholder="如: HKG"
                  class="input-bordered input uppercase"
                  required
                />
              </div>

              <div class="form-control">
                <label class="label">
                  <span class="label-text font-bold">目的地</span>
                </label>
                <input
                  v-model="leg.destination"
                  type="text"
                  placeholder="如: NRT"
                  class="input-bordered input uppercase"
                  required
                />
              </div>
            </div>

            <div class="form-control mt-4">
              <label class="label">
                <span class="label-text font-bold">出發日期</span>
              </label>
              <input v-model="leg.flightDate" type="date" class="input-bordered input" required />
            </div>
          </div>
        </div>

        <div v-if="form.tripType === 'MULTI_CITY'" class="flex justify-center">
          <button type="button" @click="addLeg" class="btn btn-outline btn-sm">+ 新增航段</button>
        </div>

        <div class="divider">其他設定</div>

        <div class="form-control">
          <label class="label">
            <span class="label-text font-bold">最遲購票日</span>
            <span class="label-text-alt text-base-content/60">選填</span>
          </label>
          <input v-model="form.deadline" type="date" class="input-bordered input" />
          <div class="label">
            <span class="label-text-alt text-base-content/60">
              設定後將啟用 Rule37 分析模型，判斷最佳購買時機
            </span>
          </div>
        </div>

        <div class="form-control">
          <label class="label cursor-pointer justify-start gap-4">
            <input v-model="form.isActive" type="checkbox" class="toggle toggle-success" />
            <span class="label-text font-bold">立即啟用追蹤</span>
          </label>
        </div>

        <div class="mt-8 flex gap-4 border-t border-base-200 pt-4">
          <Link href="/" class="btn flex-1 btn-ghost">取消</Link>
          <button
            type="submit"
            class="btn flex-1 shadow-sm btn-primary"
            :disabled="form.processing"
          >
            <span v-if="form.processing" class="loading loading-spinner"></span>
            建立追蹤
          </button>
        </div>
      </form>
    </div>
  </AppLayout>
</template>
