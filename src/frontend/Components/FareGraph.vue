<script setup lang="ts">
import type { Itinerary } from '@/types'
import type { ChartDataset } from 'chart.js'
import Chart from 'chart.js/auto'
import { onMounted, onUnmounted, useTemplateRef } from 'vue'

const props = defineProps<{ itinerary: Itinerary }>()

const chartCanvas = useTemplateRef<HTMLCanvasElement>('chartCanvas')
let chart: InstanceType<typeof Chart> | null = null

onMounted(() => {
  if (!chartCanvas.value || !props.itinerary.flights.length) {
    return
  }

  if (chart) {
    chart.destroy()
  }

  const labels = [
    ...new Set([
      ...props.itinerary.flights.flatMap((f) =>
        (f.fareSnapshots || []).map((s) => s.createdAt.split('T')[0]),
      ),
      ...(props.itinerary.rule37Analysis?.cutoffDate
        ? [props.itinerary.rule37Analysis.cutoffDate]
        : []),
    ]),
  ]
    .filter(Boolean)
    .sort()

  const datasets: ChartDataset<'line'>[] = []

  if (props.itinerary.tripType !== 'SINGLE' && props.itinerary.statistics) {
    datasets.push({
      label: '總價 (最低)',
      data: labels.map((date) => {
        const totals = props.itinerary.flights.map((f) => {
          const fares = (f.fareSnapshots || [])
            .filter(
              (s) =>
                s.createdAt.startsWith(date) && s.scrapeStatus === 'success' && s.fare !== null,
            )
            .map((s) => s.fare as number)
          return fares.length ? Math.min(...fares) : null
        })
        return totals.includes(null) ? null : totals.reduce((a, b) => a! + b!, 0)
      }),
      borderColor: '#ff9800',
      backgroundColor: 'rgba(255, 152, 0, 0.1)',
      borderWidth: 3,
      tension: 0.1,
      fill: false,
      spanGaps: false,
    })
  }

  props.itinerary.flights.forEach((f, idx) => {
    const dataObj = (f.fareSnapshots || [])
      .filter((s) => s.scrapeStatus === 'success' && s.fare !== null)
      .reduce(
        (acc, s) => {
          const d = s.createdAt.split('T')[0]
          if (!acc[d] || s.fare! < acc[d]) acc[d] = s.fare!
          return acc
        },
        {} as Record<string, number>,
      )

    datasets.push({
      label: props.itinerary.tripType === 'SINGLE' ? '最低票價' : `${f.origin} → ${f.destination}`,
      data: labels.map((l) => dataObj[l] ?? null),
      borderColor:
        props.itinerary.tripType === 'SINGLE' ? '#2563eb' : `hsl(${(idx * 137.5) % 360}, 70%, 50%)`,
      backgroundColor:
        props.itinerary.tripType === 'SINGLE' ? 'rgba(37, 99, 235, 0.1)' : 'transparent',
      borderWidth: 2,
      tension: 0.1,
      fill: props.itinerary.tripType === 'SINGLE',
      spanGaps: false,
    })
  })

  if (props.itinerary.rule37Analysis?.historyBestVal) {
    datasets.push({
      label: '門檻',
      data: labels.map(() => props.itinerary.rule37Analysis!.historyBestVal),
      borderColor: 'rgba(255, 99, 132, 0.8)',
      borderDash: [10, 10],
      borderWidth: 1,
      spanGaps: false,
      pointRadius: 0,
    })
  }

  chart = new Chart(chartCanvas.value, {
    type: 'line',
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: props.itinerary.tripType !== 'SINGLE' },
        tooltip: { padding: 12, cornerRadius: 8 },
      },
      scales: {
        y: { grid: { color: '#f3f4f6' } },
        x: {
          grid: { display: false },
          ticks: {
            callback: function (_, index) {
              if (labels.length <= 30) {
                return this.getLabelForValue(index)
              }
              return index % 4 === 0 ? this.getLabelForValue(index) : ''
            },
          },
        },
      },
      interaction: { intersect: false, mode: 'index' },
    },
  })
})

onUnmounted(() => chart?.destroy())
</script>

<template>
  <template v-if="itinerary.flights.length">
    <div class="relative h-100 rounded-3xl bg-base-100 p-4 max-sm:h-80 md:p-6">
      <canvas ref="chartCanvas"></canvas>
    </div>
  </template>

  <div v-else class="hero py-16 text-center">
    <div class="hero-content">
      <p class="font-medium text-base-content/50">暫無趨勢數據。</p>
    </div>
  </div>
</template>
