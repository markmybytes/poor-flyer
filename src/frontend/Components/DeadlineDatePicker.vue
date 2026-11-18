<script setup lang="ts">
import DatePicker from '@/Components/DatePicker.vue'
import { parseISO, subDays } from 'date-fns'
import { computed } from 'vue'

const props = defineProps<{
  trip?: { start?: string; end?: string }
}>()

const model = defineModel<string>({ required: true })

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
      markers: props.trip?.start
        ? [
            { date: props.trip.start, type: 'dot' as const, color: '#007af0' },
            ...(props.trip.end && props.trip.end !== props.trip.start
              ? [{ date: props.trip.end, type: 'dot' as const, color: '#10b981' }]
              : []),
          ]
        : undefined,
      presetDates: !props.trip?.start
        ? []
        : [7, 14, 30, 60, 90]
            .map((days) => ({
              label: `-${days}天`,
              value: subDays(parseISO(props.trip.start!), days),
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
