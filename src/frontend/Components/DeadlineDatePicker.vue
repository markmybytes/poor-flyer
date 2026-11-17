<script setup lang="ts">
import DatePicker from '@/Components/DatePicker.vue'
import type { Marker } from '@vuepic/vue-datepicker'
import { parseISO, subDays } from 'date-fns'
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    departure?: string
    markers?: Marker[] | null
    clearLabel?: string
  }>(),
  { departure: undefined, markers: null, clearLabel: '清除限期' },
)

const model = defineModel<string>({ required: true })

// the viewer's local calendar day (en-CA renders YYYY-MM-DD) as the picker floor
const minDate = new Date().toLocaleDateString('en-CA')

// a departed trip gets no upper bound, so max never undercuts min
const maxDate = computed(() =>
  props.departure && props.departure >= minDate ? props.departure : undefined,
)
</script>

<template>
  <DatePicker
    v-model="model"
    :clear-label="clearLabel"
    :options="{
      minDate,
      maxDate: maxDate,
      startDate: maxDate ?? minDate,
      markers:
        props.markers ??
        (departure ? [{ date: departure, type: 'dot', color: '#007af0' }] : undefined),
      presetDates: !departure
        ? []
        : [7, 14, 30, 60, 90]
            .map((days) => ({
              label: `前${days}天`,
              value: subDays(parseISO(departure), days),
            }))
            .filter((preset) => {
              const max = maxDate ? parseISO(maxDate).getTime() : null
              return (
                preset.value.getTime() >= parseISO(minDate).getTime() &&
                (!max || preset.value.getTime() <= max)
              )
            }),
    }"
  />
</template>
