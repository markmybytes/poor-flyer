<script setup lang="ts">
import type { Flight, Rule37Analysis } from '@/types'
import { fmtDate, fmtFare, fmtTime, fmtTz } from '@/utils'
import { computed, ref } from 'vue'

const props = defineProps<{ flight: Flight; rule37Analysis?: Rule37Analysis | null }>()

const expandedGroups = ref(new Set<number>())

const stats = computed(() => {
  const fares = (props.flight.fareSnapshots || [])
    .filter((s) => s.scrapeStatus === 'success' && s.fare !== null)
    .map((s) => s.fare as number)

  if (!fares.length) {
    return { min: null, max: null }
  }

  const min = Math.min(...fares)
  const max = Math.max(...fares)
  return min === max ? { min: null, max: null } : { min, max }
})

const dailySnapshots = computed(() => {
  const byDate = (props.flight.fareSnapshots || []).reduce(
    (acc, s) => {
      ;(acc[s.createdAt.split('T')[0]] ??= []).push(s)
      return acc
    },
    {} as Record<string, typeof props.flight.fareSnapshots>,
  )

  return Object.entries(byDate)
    .sort(([a], [b]) => b.localeCompare(a))
    .map(([date, snaps]) => {
      const low = snaps!
        .filter((s) => s.scrapeStatus === 'success' && s.fare != null)
        .sort((a, b) => (a.fare as number) - (b.fare as number))[0]

      return {
        date,
        lowestFare: low?.fare ?? null,
        lowestSnapshot: low ? { flightNumber: low.flightNumber, fare: low.fare } : null,
        snapshots: snaps!.sort((a, b) => b.createdAt.localeCompare(a.createdAt)),
      }
    })
})
</script>

<template>
  <div>
    <div class="py-1">
      <div v-if="dailySnapshots.length" class="flex justify-end py-2">
        <button
          class="btn btn-outline btn-xs btn-neutral"
          @click="
            () => {
              if (expandedGroups.size === 0) {
                expandedGroups = new Set(Array(dailySnapshots.length).keys())
              } else {
                expandedGroups.clear()
              }
            }
          "
        >
          {{ expandedGroups.size === 0 ? '全部展開' : '全部收起' }}
        </button>
      </div>
    </div>

    <template v-if="dailySnapshots.length">
      <div
        v-for="(group, i) in dailySnapshots"
        :key="group.date"
        class="collapse-plus collapse mb-3 border border-base-300/70 bg-base-100 last:mb-0"
        :class="expandedGroups.has(i) ? 'collapse-open' : 'collapse-close'"
      >
        <button
          class="collapse-title flex w-full items-center justify-between pr-14 pl-5 text-left transition-colors hover:bg-base-200/40"
          :class="{
            'bg-success/10':
              stats.min !== null &&
              group.snapshots.some((s) => s.fare === stats.min) &&
              !group.snapshots.some((s) => s.fare === stats.max),
          }"
          @click="expandedGroups.has(i) ? expandedGroups.delete(i) : expandedGroups.add(i)"
        >
          <div class="flex flex-1 items-center gap-4">
            <div>
              <p class="leading-tight font-bold text-base-content">
                {{ fmtDate(group.date) }}
                <span class="ml-1 text-xs font-medium text-base-content/55">
                  （{{
                    ['日', '一', '二', '三', '四', '五', '六'][new Date(group.date).getDay()]
                  }}）
                </span>
              </p>

              <p class="text-xs font-medium text-base-content/60">
                <template v-if="group.lowestSnapshot">
                  當日最低：<span class="font-bold text-base-content">{{
                    fmtFare(group.lowestFare)
                  }}</span>

                  <template v-if="group.lowestSnapshot.flightNumber">
                    · {{ group.lowestSnapshot.flightNumber }}
                  </template>
                </template>

                <span v-else class="text-error">無有效價格數據</span>
              </p>
            </div>
          </div>

          <div class="badge shrink-0 badge-outline px-3 py-3 text-xs font-semibold badge-primary">
            {{ group.snapshots.length }} 筆紀錄
          </div>
        </button>

        <div
          v-if="rule37Analysis?.phase && group.date === rule37Analysis.cutoffDate"
          class="border-y border-warning/20 bg-warning/15 px-5 py-1.5 text-center"
        >
          <p class="text-[11px] font-bold tracking-widest text-warning-content">
            ▴ 購買時機分析 · 決策期 ▴
          </p>
        </div>

        <div
          v-show="expandedGroups.has(i)"
          class="collapse-content border-t border-base-300/70 bg-base-200/40 px-5 py-4"
        >
          <div class="overflow-x-auto rounded-[1.25rem] border border-base-300/70 bg-base-100">
            <table class="table w-full table-zebra text-sm">
              <thead>
                <tr>
                  <th class="text-xs font-bold tracking-wider text-base-content/55 uppercase">
                    航班編號
                  </th>

                  <th class="text-xs font-bold tracking-wider text-base-content/55 uppercase">
                    起飛時間
                  </th>

                  <th class="text-xs font-bold tracking-wider text-base-content/55 uppercase">
                    降落時間
                  </th>

                  <th
                    class="text-right text-xs font-bold tracking-wider text-base-content/55 uppercase"
                  >
                    票價
                  </th>
                </tr>
              </thead>

              <tbody>
                <tr
                  v-for="snap in group.snapshots"
                  :key="snap.id"
                  :class="[snap.scrapeStatus === 'error' ? 'bg-error/10' : '']"
                >
                  <td class="font-semibold text-base-content">{{ snap.flightNumber ?? '—' }}</td>

                  <td class="text-base-content/70">
                    {{ fmtTime(snap.departureAt) }}
                    <span class="text-[10px] text-base-content/40">
                      {{ fmtTz(snap.departureAt) }}
                    </span>
                  </td>

                  <td class="text-base-content/70">
                    {{ fmtTime(snap.arrivalAt) }}
                    <span class="text-[10px] text-base-content/40">
                      {{ fmtTz(snap.arrivalAt) }}
                    </span>
                  </td>

                  <td class="text-right font-bold text-base-content">
                    <template v-if="snap.scrapeStatus === 'success' && snap.fare !== null">
                      <div
                        class="flex flex-col items-end justify-end gap-2 sm:flex-row sm:items-center"
                      >
                        <div class="flex flex-wrap justify-end gap-1">
                          <span
                            v-if="snap.fare === stats.min"
                            class="badge badge-soft badge-xs badge-success"
                          >
                            [歷史低位]
                          </span>

                          <span
                            v-if="snap.fare === stats.max"
                            class="badge badge-soft badge-xs badge-error"
                          >
                            [歷史高位]
                          </span>
                        </div>

                        <span>{{ fmtFare(snap.fare, snap.currency) }}</span>
                      </div>
                    </template>

                    <span v-else class="text-xs text-error">擷取失敗</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </template>

    <div v-else class="hero py-16 text-center">
      <div class="hero-content">
        <p class="font-medium text-base-content/50">暫無價格數據。</p>
      </div>
    </div>
  </div>
</template>
