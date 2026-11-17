<script setup lang="ts">
import DatePicker from '@/Components/DatePicker.vue'
import { parseISO, subDays } from 'date-fns'
import { computed } from 'vue'

const props = defineProps<{
  trip?: { start?: string; end?: string }
}>()

const model = defineModel<string>({ required: true })

// the viewer's local calendar day (en-CA renders YYYY-MM-DD) as the picker floor
const minDate = new Date().toLocaleDateString('en-CA')

// a departed trip gets no upper bound, so max never undercuts min
const maxDate = computed(() =>
  props.trip?.start && props.trip.start >= minDate ? props.trip.start : undefined,
)
</script>

<template>
  <DatePicker
    v-model="model"
    :options="{
      minDate,
      maxDate,
      startDate: maxDate,
      markers: trip?.start
        ? [
            { date: trip.start, type: 'dot' as const, color: '#007af0' },
            ...(trip.end && trip.end !== trip.start
              ? [{ date: trip.end, type: 'dot' as const, color: '#10b981' }]
              : []),
          ]
        : undefined,
      presetDates: !trip?.start
        ? []
        : [7, 14, 30, 60, 90]
            .map((days) => ({
              label: `-${days}天`,
              value: subDays(parseISO(trip.start!), days),
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
