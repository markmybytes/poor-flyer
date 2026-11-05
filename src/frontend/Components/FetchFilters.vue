<script setup lang="ts">
import {
  CABIN_CLASS_OPTIONS,
  COMMON_AIRLINES,
  MAX_STOPS_OPTIONS,
  normalizeAirlineCode,
} from '@/options'
import { computed, ref } from 'vue'

const model = defineModel<{
  cabinClass: string
  maxStops: string
  airlines: string[] | null
}>({ required: true })

const airlineInput = ref('')

const selectedAirlines = computed(() => model.value.airlines ?? [])

const extraAirlines = computed(() =>
  selectedAirlines.value.filter((code) => !COMMON_AIRLINES.some((a) => a.value === code)),
)

function addAirline() {
  const code = normalizeAirlineCode(airlineInput.value)
  airlineInput.value = ''
  if (!code || selectedAirlines.value.includes(code)) {
    return
  }
  model.value.airlines = [...selectedAirlines.value, code]
}

function toggleAirline(code: string) {
  const airlines = selectedAirlines.value
  model.value.airlines = airlines.includes(code)
    ? airlines.filter((c) => c !== code)
    : [...airlines, code]
}

function removeAirline(code: string) {
  model.value.airlines = selectedAirlines.value.filter((c) => c !== code)
}
</script>

<template>
  <div class="grid gap-4 sm:grid-cols-2">
    <fieldset class="fieldset">
      <legend class="fieldset-legend text-sm font-bold">
        艙等 <span class="font-normal text-base-content/50">（選填）</span>
      </legend>

      <select v-model="model.cabinClass" class="select-bordered select w-full">
        <option value="">使用預設（不限）</option>

        <option v-for="option in CABIN_CLASS_OPTIONS" :key="option.value" :value="option.value">
          {{ option.label }}
        </option>
      </select>
    </fieldset>

    <fieldset class="fieldset">
      <legend class="fieldset-legend text-sm font-bold">
        轉機次數 <span class="font-normal text-base-content/50">（選填）</span>
      </legend>

      <select v-model="model.maxStops" class="select-bordered select w-full">
        <option value="">使用預設（不限）</option>

        <option v-for="option in MAX_STOPS_OPTIONS" :key="option.value" :value="option.value">
          {{ option.label }}
        </option>
      </select>
    </fieldset>

    <fieldset class="fieldset sm:col-span-2">
      <legend class="fieldset-legend text-sm font-bold">
        航空公司 <span class="font-normal text-base-content/50">（選填，不選表示不限制）</span>
      </legend>

      <div class="grid gap-x-4 gap-y-1 sm:grid-cols-3 lg:grid-cols-4">
        <label
          v-for="airline in COMMON_AIRLINES"
          :key="airline.value"
          class="label cursor-pointer justify-start gap-2 px-0 py-1"
        >
          <input
            type="checkbox"
            class="checkbox checkbox-sm"
            :value="airline.value"
            :checked="selectedAirlines.includes(airline.value)"
            @change="toggleAirline(airline.value)"
          />

          <span class="text-sm">{{ airline.label }}</span>
        </label>
      </div>

      <div class="mt-2 flex flex-wrap items-center gap-2">
        <input
          v-model="airlineInput"
          type="text"
          maxlength="3"
          placeholder="其他 IATA 代碼"
          class="input-bordered input input-sm w-40 uppercase"
          @keydown.enter.prevent="addAirline"
          @blur="addAirline"
        />

        <span v-for="code in extraAirlines" :key="code" class="badge gap-1 badge-sm">
          {{ code }}

          <button
            type="button"
            class="cursor-pointer text-base-content/50 hover:text-error"
            :aria-label="`移除 ${code}`"
            @click="removeAirline(code)"
          >
            ✕
          </button>
        </span>

        <span class="text-xs text-base-content/50">輸入 2-3 位代碼後按 Enter 新增</span>
      </div>
    </fieldset>
  </div>
</template>
