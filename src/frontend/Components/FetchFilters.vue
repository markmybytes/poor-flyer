<script setup lang="ts">
import { CABIN_CLASS_OPTIONS, MAX_STOPS_OPTIONS, normalizeAirlineCode } from '@/options'
import { Icon } from '@iconify/vue'
import { computed, onMounted, ref } from 'vue'

const model = defineModel<{
  cabinClass: string
  maxStops: string
  airlines: string[] | null
}>({ required: true })

const airlineInput = ref('')
const airlineOptions = ref<{ code: string; name: string }[]>([])
const showSuggestions = ref(false)

const selectedAirlines = computed(() => model.value.airlines ?? [])

const suggestions = computed(() => {
  const query = airlineInput.value.trim().toLowerCase()
  if (!query) {
    return []
  }
  return airlineOptions.value
    .filter(
      (airline) =>
        airline.code.toLowerCase().startsWith(query) || airline.name.toLowerCase().includes(query),
    )
    .slice(0, 20)
})

onMounted(() => {
  fetch('/api/airlines')
    .then((response) => (response.ok ? response.json() : null))
    .then((body) => {
      if (Array.isArray(body?.data)) {
        airlineOptions.value = body.data
      }
    })
    .catch(() => {})
})

function addAirlineCode(code: string | null) {
  if (!code || selectedAirlines.value.includes(code)) {
    return
  }
  model.value.airlines = [...selectedAirlines.value, code]
}

function addAirline() {
  const raw = airlineInput.value.trim()
  airlineInput.value = ''
  showSuggestions.value = false
  if (!raw) {
    return
  }

  const known = airlineOptions.value.find(
    (airline) =>
      airline.code === raw.toUpperCase() || airline.name.toLowerCase() === raw.toLowerCase(),
  )
  addAirlineCode(known?.code ?? normalizeAirlineCode(raw))
}

function selectAirline(airline: { code: string; name: string }) {
  addAirlineCode(airline.code)
  airlineInput.value = ''
  showSuggestions.value = false
}

function removeAirline(code: string) {
  model.value.airlines = selectedAirlines.value.filter((current) => current !== code)
}

function airlineName(code: string) {
  return airlineOptions.value.find((airline) => airline.code === code)?.name
}
</script>

<template>
  <div class="grid gap-4 md:grid-cols-2">
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

      <div class="relative w-full">
        <input
          v-model="airlineInput"
          type="text"
          placeholder="搜尋航空公司名稱或代碼"
          class="input-bordered input input-sm w-full"
          @focus="showSuggestions = true"
          @input="showSuggestions = true"
          @keydown.enter.prevent="addAirline"
          @keydown.esc="showSuggestions = false"
          @blur="showSuggestions = false"
        />

        <ul
          v-if="showSuggestions && suggestions.length"
          class="absolute z-20 mt-1 max-h-56 w-full overflow-auto rounded-box border border-base-200 bg-base-100 p-1"
        >
          <li v-for="airline in suggestions" :key="airline.code">
            <button
              type="button"
              class="airline-suggestion block w-full px-2 py-1 text-left text-sm transition-colors hover:bg-base-200"
              @mousedown.prevent="selectAirline(airline)"
            >
              {{ airline.code }} · {{ airline.name }}
            </button>
          </li>
        </ul>
      </div>

      <TransitionGroup
        v-if="selectedAirlines.length"
        tag="div"
        name="chip"
        class="mt-2 flex flex-wrap items-center gap-1.5"
      >
        <span
          v-for="code in selectedAirlines"
          :key="code"
          class="airline-chip inline-flex items-start gap-1.5 rounded bg-base-200/60 px-2 py-1 text-xs"
        >
          <span class="font-bold">{{ code }}</span>

          <template v-if="airlineName(code)">
            <span class="text-base-content/60">{{ ' · ' + airlineName(code) }}</span>
          </template>

          <button
            type="button"
            class="mt-0.5 cursor-pointer text-base-content/35 transition-colors hover:text-error focus-visible:text-error"
            :aria-label="`移除 ${code}`"
            @click="removeAirline(code)"
          >
            <Icon icon="mdi:close" class="size-3" />
          </button>
        </span>
      </TransitionGroup>

      <span class="mt-1 text-xs text-base-content/50"
        >輸入 2-3 位代碼或航空公司名稱後按 Enter 新增</span
      >
    </fieldset>
  </div>
</template>

<style scoped>
.chip-enter-active,
.chip-leave-active {
  transition:
    opacity 0.15s ease,
    transform 0.15s ease;
}

.chip-enter-from,
.chip-leave-to {
  opacity: 0;
  transform: scale(0.95);
}

.chip-move {
  transition: transform 0.15s ease;
}
</style>
