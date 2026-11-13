<script setup lang="ts">
import AppLayout from '@/Layouts/AppLayout.vue'
import ItineraryCard from '@/Components/ItineraryCard.vue'
import type { Itinerary } from '@/types'
import { fmtItineraryName } from '@/utils'
import { Link, router } from '@inertiajs/vue3'
import { computed, ref } from 'vue'
import { useToast } from 'vue-toast-notification'

const props = defineProps<{ itineraries: Itinerary[]; baseCurrency: string }>()

const toast = useToast()

const archivedView = ref(
  typeof window !== 'undefined' &&
    new URLSearchParams(window.location.search).get('archived') === '1',
)

const ui = ref<{ pendingId: string | null; restoring: boolean }>({
  pendingId: null,
  restoring: false,
})

const pendingItinerary = computed(() =>
  props.itineraries?.find((it) => it.id === ui.value.pendingId),
)

const summary = computed(() => {
  const its = props.itineraries || []
  const active = its.filter((it) => it.isActive && !it.archivedAt).length

  return {
    total: its.length,
    active,
    paused: its.length - active,
    buySignals: its.filter((it) => it.rule37Analysis?.phase === 'BUY_SIGNAL').length,
  }
})

function switchView(archived: boolean) {
  if (archived === archivedView.value) return

  archivedView.value = archived
  // Fresh navigation — Inertia resets scroll to top for each view's own layout.
  router.get('/itineraries/', archived ? { archived: '1' } : {}, {
    replace: true,
  })
}

function confirmRestore(itinerary: Itinerary) {
  ui.value.pendingId = itinerary.id
}

function runRestore() {
  const id = ui.value.pendingId
  if (!id) return

  ui.value.restoring = true

  fetch(`/api/itineraries/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ archived: false }),
  })
    .then((res) => {
      if (!res.ok) throw new Error()
      ui.value.pendingId = null
      toast.success('已恢復追蹤')
      router.reload()
    })
    .catch(() => {
      toast.error('恢復追蹤失敗，請稍後再試')
    })
    .finally(() => {
      ui.value.restoring = false
    })
}
</script>

<template>
  <AppLayout>
    <div class="mb-8">
      <h2 class="text-3xl font-extrabold tracking-tight text-base-content">追蹤清單</h2>

      <p class="mt-2 text-sm font-medium text-base-content/65">
        集中管理已儲存的旅程，查看最新價格資訊。
      </p>
    </div>

    <div
      class="tracker-panel stats mb-8 w-full stats-horizontal gap-0 rounded-lg border border-base-200 shadow-sm"
    >
      <div class="stat px-4 py-3 sm:px-6 sm:py-4">
        <div class="stat-title text-xs sm:text-sm">{{ archivedView ? '已封存' : '旅程' }}</div>

        <div class="stat-value text-xl text-primary sm:text-3xl">{{ summary.total }}</div>

        <div class="stat-desc hidden sm:block">
          {{ archivedView ? '已完結的旅程紀錄' : '已儲存的追蹤項目' }}
        </div>
      </div>

      <template v-if="!archivedView">
        <div class="stat px-4 py-3 sm:px-6 sm:py-4">
          <div class="stat-title text-xs sm:text-sm">自動追蹤中</div>

          <div class="stat-value text-xl text-secondary sm:text-3xl">{{ summary.active }}</div>

          <div class="stat-desc hidden sm:block">{{ summary.paused }} 個追蹤已暫停</div>
        </div>

        <div class="stat px-4 py-3 sm:px-6 sm:py-4">
          <div class="stat-title text-xs sm:text-sm">可入手提示</div>

          <div class="stat-value text-xl text-success sm:text-3xl">{{ summary.buySignals }}</div>

          <div class="stat-desc hidden sm:block">正值最佳入手時機</div>
        </div>
      </template>
    </div>

    <div class="mb-8 flex items-center justify-between">
      <div class="join gap-0 shadow-sm">
        <button
          class="btn join-item btn-sm"
          :class="archivedView ? 'border border-base-300 btn-ghost' : 'btn-primary'"
          @click="switchView(false)"
        >
          追蹤中
        </button>

        <button
          class="btn join-item btn-sm"
          :class="archivedView ? 'btn-primary' : 'border border-base-300 btn-ghost'"
          @click="switchView(true)"
        >
          已封存
        </button>
      </div>

      <Link href="/itineraries/create" class="btn shadow-sm btn-primary">新增監察項目</Link>
    </div>

    <div
      v-if="itineraries?.length"
      class="divide-y divide-base-200 overflow-hidden rounded-lg border border-base-200 bg-base-100 shadow-sm sm:grid sm:grid-cols-2 sm:gap-4 sm:divide-y-0 sm:overflow-visible sm:rounded-none sm:border-0 sm:bg-transparent sm:shadow-none md:gap-5 lg:gap-6"
    >
      <ItineraryCard
        v-for="itinerary in itineraries.toSorted((a, b) => a.createdAt.localeCompare(b.createdAt))"
        :key="itinerary.id"
        :itinerary="itinerary"
        :base-currency="baseCurrency"
        :archived="archivedView"
        @restore="confirmRestore"
      />
    </div>

    <div
      v-else
      class="tracker-panel hero rounded-lg border-2 border-dashed border-base-300 py-12 text-center sm:py-20"
    >
      <div class="hero-content flex-col">
        <div class="placeholder avatar mb-6 flex justify-center">
          <div
            class="flex h-24 w-24 items-center justify-center rounded-full text-5xl"
            :class="
              archivedView ? 'bg-base-200 text-base-content/50' : 'bg-primary/10 text-primary'
            "
          >
            {{ archivedView ? '🗄️' : '✈️' }}
          </div>
        </div>

        <h3 class="mb-2 text-2xl font-bold text-base-content">
          {{ archivedView ? '沒有已封存的旅程' : '未有追蹤任何旅程' }}
        </h3>

        <p class="mb-8 max-w-xl text-sm leading-relaxed text-base-content/65">
          {{
            archivedView
              ? '已完結的旅程會被封存於此，僅保留紀錄供回顧。'
              : '新增你想關注的，系統將全天候自動收集機票價格，助你分析最佳的購買時機。'
          }}
        </p>

        <Link href="/itineraries/create" class="btn shadow-sm btn-lg btn-primary">
          {{ archivedView ? '建立新的追蹤' : '建立你的第一個追蹤' }}
        </Link>
      </div>
    </div>

    <dialog class="modal" :class="{ 'modal-open': pendingItinerary }">
      <div class="modal-box max-w-sm rounded-2xl border border-base-200 bg-base-100 shadow-xl">
        <h3 class="mb-2 text-lg font-extrabold text-base-content">恢復追蹤？</h3>

        <p class="text-sm text-base-content/60">
          {{ `確定恢復追蹤「${pendingItinerary ? fmtItineraryName(pendingItinerary) : ''}」？` }}
        </p>

        <p class="mt-1.5 text-sm text-base-content/60">
          若出發日期已過 30 天，此旅程會在下次自動更新時重新封存。
        </p>

        <div class="modal-action mt-6 justify-end gap-2 border-t border-base-200 pt-4">
          <button type="button" class="btn btn-ghost btn-sm" @click="ui.pendingId = null">
            取消
          </button>

          <button
            type="button"
            class="btn px-5 shadow-sm btn-sm btn-primary"
            :disabled="ui.restoring"
            @click="runRestore"
          >
            <span v-if="ui.restoring" class="loading loading-xs loading-spinner"></span>
            恢復追蹤
          </button>
        </div>
      </div>

      <div class="modal-backdrop bg-black/10 backdrop-blur-xs" @click="ui.pendingId = null"></div>
    </dialog>
  </AppLayout>
</template>
