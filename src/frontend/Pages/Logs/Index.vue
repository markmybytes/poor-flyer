<script setup lang="ts">
import AppLayout from '@/Layouts/AppLayout.vue'
import { router } from '@inertiajs/vue3'
import { VueDatePicker } from '@vuepic/vue-datepicker'
import '@vuepic/vue-datepicker/dist/main.css'
import { computed, ref, useTemplateRef, watch } from 'vue'
import { useToast } from 'vue-toast-notification'

const props = defineProps<{
  logs: {
    timestamp: string
    level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL' | string
    logger: string
    message: string
    traceback: string | null
  }[]
  pagination: {
    total: number
    page: number
    perPage: number
  }
  filters: {
    level: string
    startDate: string
    endDate: string
  }
}>()

const toast = useToast()
const confirmModal = useTemplateRef<HTMLDialogElement>('confirmModal')
const clearing = ref(false)

const LOG_LEVELS = ['ALL', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'] as const

const selectedLevel = ref(props.filters.level || 'ALL')

const dateRange = ref<Date[] | null>(
  props.filters.startDate && props.filters.endDate
    ? [new Date(props.filters.startDate), new Date(props.filters.endDate)]
    : null,
)

function levelBadgeClass(level: string): string {
  switch (level) {
    case 'DEBUG':
      return 'badge-ghost'
    case 'INFO':
      return 'badge-info'
    case 'WARNING':
      return 'badge-warning'
    case 'ERROR':
      return 'badge-error'
    case 'CRITICAL':
      return 'badge-error badge-outline'
    default:
      return 'badge-ghost'
  }
}

function navigate(page = 1) {
  const data: Record<string, string | number> = {
    page,
    level: selectedLevel.value,
  }

  if (Array.isArray(dateRange.value)) {
    if (dateRange.value[0]) {
      data.start_date = (dateRange.value[0] as Date).toISOString().slice(0, 10)
    }
    if (dateRange.value[1]) {
      data.end_date = (dateRange.value[1] as Date).toISOString().slice(0, 10)
    }
  }

  router.visit('/logs/', { data, preserveState: true, replace: true })
}

watch([selectedLevel, dateRange], () => navigate(1))

const totalPages = computed(() => Math.ceil(props.pagination.total / props.pagination.perPage))

const pageNumbers = computed((): (number | '...')[] => {
  const { page } = props.pagination
  const total = totalPages.value
  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i + 1)
  }
  const pages: (number | '...')[] = [1]
  if (page > 3) pages.push('...')
  for (let i = Math.max(2, page - 1); i <= Math.min(total - 1, page + 1); i++) {
    pages.push(i)
  }
  if (page < total - 2) pages.push('...')
  pages.push(total)
  return pages
})

function clearLogs() {
  clearing.value = true
  fetch('/api/logs', { method: 'DELETE' })
    .then((r) => r.json())
    .then((d: { success: boolean; message?: string }) => {
      if (!d.success) throw new Error(d.message || '清除失敗')
      toast.success('日誌已清除')
      confirmModal.value?.close()
      router.reload()
    })
    .catch((e: Error) => toast.error(e.message))
    .finally(() => (clearing.value = false))
}
</script>

<template>
  <AppLayout>
    <div class="mb-8">
      <h2 class="text-3xl font-extrabold tracking-tight text-base-content">應用程式日誌</h2>

      <p class="mt-2 text-sm font-medium text-base-content/65">
        查看、篩選和管理應用程式運行日誌。
      </p>
    </div>

    <div class="tracker-panel mb-6 rounded-lg border border-base-200 bg-base-100 p-4 shadow-sm">
      <div class="flex flex-wrap items-end gap-4">
        <div class="min-w-48 flex-1">
          <div class="mb-2 text-xs font-semibold text-base-content/70">日誌級別</div>

          <div class="join flex flex-wrap gap-0">
            <button
              v-for="lvl in LOG_LEVELS"
              :key="lvl"
              class="btn join-item btn-xs"
              :class="selectedLevel === lvl ? 'btn-primary' : 'border border-base-300 btn-ghost'"
              @click="selectedLevel = lvl"
            >
              {{ lvl }}
            </button>
          </div>
        </div>

        <div class="min-w-48 flex-1">
          <div class="mb-2 text-xs font-semibold text-base-content/70">日期範圍</div>

          <VueDatePicker
            v-model="dateRange"
            range
            auto-apply
            :time-config="{ enableTimePicker: false }"
            :formats="{ input: 'yyyy-MM-dd' }"
            placeholder="選擇日期範圍"
            :teleport="true"
          />
        </div>

        <div class="flex-none">
          <button class="btn btn-outline btn-sm btn-error" @click="confirmModal?.showModal()">
            清除日誌
          </button>
        </div>
      </div>
    </div>

    <div class="mb-4 flex items-center justify-between text-sm text-base-content/60">
      <span>共 {{ pagination.total }} 筆記錄</span>

      <span v-if="totalPages > 1">第 {{ pagination.page }} / {{ totalPages }} 頁</span>
    </div>

    <div class="tracker-panel overflow-hidden rounded-lg border border-base-200 shadow-sm">
      <div v-if="logs.length === 0" class="py-16 text-center text-base-content/50">
        <div class="mb-2 text-4xl">📋</div>

        <div class="font-medium">沒有符合條件的日誌記錄</div>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="table w-full table-sm">
          <thead>
            <tr class="bg-base-200/60 text-xs uppercase">
              <th class="w-44">時間戳記</th>

              <th class="w-20">級別</th>

              <th class="hidden w-48 md:table-cell">來源</th>

              <th>訊息</th>
            </tr>
          </thead>

          <tbody>
            <template v-for="(entry, i) in logs" :key="i">
              <tr v-if="!entry.traceback" class="hover:bg-base-200/40">
                <td class="font-mono text-xs whitespace-nowrap text-base-content/60">
                  {{ entry.timestamp }}
                </td>

                <td>
                  <span class="badge badge-sm" :class="levelBadgeClass(entry.level)">
                    {{ entry.level }}
                  </span>
                </td>

                <td
                  class="hidden max-w-xs truncate font-mono text-xs text-base-content/50 md:table-cell"
                >
                  {{ entry.logger }}
                </td>

                <td class="text-sm break-all">{{ entry.message }}</td>
              </tr>

              <tr v-else class="p-0 hover:bg-base-200/40">
                <td colspan="4" class="p-0">
                  <details class="collapse-arrow collapse">
                    <summary
                      class="collapse-title grid min-h-0 cursor-pointer items-center gap-2 px-4 py-3 text-sm"
                      style="grid-template-columns: 11rem 5rem 1fr"
                    >
                      <span class="font-mono text-xs whitespace-nowrap text-base-content/60">
                        {{ entry.timestamp }}
                      </span>

                      <span>
                        <span class="badge badge-sm" :class="levelBadgeClass(entry.level)">
                          {{ entry.level }}
                        </span>
                      </span>

                      <span class="break-all">{{ entry.message }}</span>
                    </summary>

                    <div class="collapse-content">
                      <div class="mb-1 hidden font-mono text-xs text-base-content/50 md:block">
                        {{ entry.logger }}
                      </div>

                      <pre
                        class="rounded bg-base-200 p-3 font-mono text-xs break-all whitespace-pre-wrap text-error/80"
                        >{{ entry.traceback }}</pre
                      >
                    </div>
                  </details>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="totalPages > 1" class="mt-6 flex items-center justify-center gap-1">
      <button
        class="btn btn-ghost btn-sm"
        :disabled="pagination.page <= 1"
        @click="navigate(pagination.page - 1)"
      >
        «
      </button>

      <template v-for="p in pageNumbers" :key="p">
        <span v-if="p === '...'" class="px-1 text-base-content/40">…</span>

        <button
          v-else
          class="btn btn-sm"
          :class="p === pagination.page ? 'btn-primary' : 'btn-ghost'"
          @click="navigate(p as number)"
        >
          {{ p }}
        </button>
      </template>

      <button
        class="btn btn-ghost btn-sm"
        :disabled="pagination.page >= totalPages"
        @click="navigate(pagination.page + 1)"
      >
        »
      </button>
    </div>

    <dialog ref="confirmModal" class="modal">
      <div class="modal-box">
        <h3 class="text-lg font-bold">確認清除日誌</h3>

        <p class="py-4 text-base-content/70">
          此操作將永久清除所有日誌記錄，且無法復原。確定繼續嗎？
        </p>

        <div class="modal-action">
          <button class="btn btn-ghost" @click="confirmModal?.close()">取消</button>

          <button class="btn btn-error" :disabled="clearing" @click="clearLogs">
            <span v-if="clearing" class="loading loading-sm loading-spinner"></span>
            確認清除
          </button>
        </div>
      </div>

      <form method="dialog" class="modal-backdrop">
        <button>close</button>
      </form>
    </dialog>
  </AppLayout>
</template>
