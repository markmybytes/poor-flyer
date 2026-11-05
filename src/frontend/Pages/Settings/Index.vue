<script setup lang="ts">
import FetchFilters from '@/Components/FetchFilters.vue'
import AppLayout from '@/Layouts/AppLayout.vue'
import { parseAirlines } from '@/options'
import type { Settings } from '@/types'
import { formatLocalDateTime } from '@/utils/timezone'
import { computed, reactive, ref } from 'vue'
import { useToast } from 'vue-toast-notification'

const props = defineProps<{
  settings: Settings
  supportedCurrencies: string[]
  fxStatus: {
    baseCurrency?: string
    lastUpdated?: string | null
    rates?: Record<string, number>
    error?: string | null
  }
}>()

const toast = useToast()

const form = reactive({
  currency: {
    base_currency: props.settings.currency?.baseCurrency ?? 'HKD',
    fxrates_api_key: props.settings.currency?.fxratesApiKey ?? '',
    cache_ttl: Number(props.settings.currency?.cacheTtl ?? 86400),
  },
  email: {
    recipients: props.settings.email?.recipients ?? '',
  },
  itinerary: {
    disable_departured_itineraries:
      props.settings.itinerary?.disableDeparturedItineraries === 'true',
  },
  smtp: {
    host: props.settings.smtp?.host ?? '',
    port: Number(props.settings.smtp?.port ?? 587),
    user: props.settings.smtp?.user ?? '',
    password: '',
    sender_email: props.settings.smtp?.senderEmail ?? '',
    require_auth: props.settings.smtp?.requireAuth !== 'false',
    protocol: props.settings.smtp?.protocol ?? 'STARTTLS',
  },
})

const filters = ref<{
  cabinClass: string
  maxStops: string
  airlines: string[] | null
}>({
  cabinClass: props.settings.search?.defaultCabinClass ?? '',
  maxStops: props.settings.search?.defaultMaxStops ?? '',
  airlines: parseAirlines(props.settings.search?.defaultAirlines),
})

const fxStatusState = reactive({
  base_currency: props.fxStatus?.baseCurrency ?? form.currency.base_currency,
  last_updated: props.fxStatus?.lastUpdated ?? null,
  rates: props.fxStatus?.rates ?? ({} as Record<string, number>),
  error: props.fxStatus?.error ?? null,
})

const ui = reactive({
  saving: false,
  testAddress: '',
  testLoading: false,
  lastSaved: null as string | null,
  refreshingRates: false,
  fxModalOpen: false,
})

const displayedRates = computed(() => {
  return props.supportedCurrencies
    .filter((code) => code !== fxStatusState.base_currency)
    .map((code) => ({ code, value: (fxStatusState.rates ?? {})[code] }))
    .filter((item) => item.value !== undefined)
})

const fxStatusTime = computed(() => {
  return formatLocalDateTime(fxStatusState.last_updated)
})

function saveSettings(sec: 'email' | 'currency' | 'smtp' | 'itinerary' | 'search') {
  ui.saving = true
  const payloads = {
    smtp: {
      host: form.smtp.host,
      port: form.smtp.port,
      user: form.smtp.user,
      sender_email: form.smtp.sender_email,
      require_auth: form.smtp.require_auth,
      protocol: form.smtp.protocol,
      ...(form.smtp.password && { password: form.smtp.password }),
    },
    email: { recipients: form.email.recipients },
    currency: {
      base_currency: form.currency.base_currency,
      fxrates_api_key: form.currency.fxrates_api_key,
      cache_ttl: form.currency.cache_ttl,
    },
    itinerary: {
      disable_departured_itineraries: form.itinerary.disable_departured_itineraries,
    },
    search: {
      default_cabin_class: filters.value.cabinClass,
      default_max_stops: filters.value.maxStops,
      default_airlines: filters.value.airlines ?? [],
    },
  }

  fetch('/api/settings', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ [sec]: payloads[sec] }),
  })
    .then((res) => res.json())
    .then((data) => {
      if (!data.success) {
        return toast.error(data.message || '儲存失敗')
      }
      toast.success('設定已成功儲存')
      ui.lastSaved = new Date().toLocaleString('zh-HK')

      if (sec === 'smtp') {
        form.smtp.password = ''
      }
    })
    .catch(() => toast.error('儲存設定時發生錯誤'))
    .finally(() => (ui.saving = false))
}

function refreshFxRates() {
  ui.refreshingRates = true
  fetch('/api/settings/fx-rates/refresh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ base_currency: form.currency.base_currency }),
  })
    .then((res) => res.json())
    .then((res) => {
      if (!res.success) {
        throw new Error(res.message || '無法更新匯率數據')
      }

      const d = res.data || {}
      Object.assign(fxStatusState, {
        base_currency: d.baseCurrency ?? form.currency.base_currency,
        last_updated: d.lastUpdated ?? null,
        rates: d.rates ?? {},
        error: null,
      })

      toast.success('已成功更新最新匯率')
    })
    .catch((err: Error) => {
      fxStatusState.error = err.message
      toast.error(err.message || '更新匯率失敗')
    })
    .finally(() => {
      ui.refreshingRates = false
    })
}

function sendTestEmail() {
  if (!ui.testAddress) {
    return
  }

  ui.testLoading = true
  fetch('/api/settings/test-email', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ recipient: ui.testAddress }),
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.success) {
        toast.success(data.message || '測試電郵已發送')
        ui.testAddress = ''
      } else {
        toast.error(data.message || '發送失敗')
      }
    })
    .catch(() => toast.error('發送測試電郵時發生錯誤'))
    .finally(() => {
      ui.testLoading = false
    })
}
</script>

<template>
  <AppLayout>
    <div class="mb-8">
      <h2 class="text-3xl font-extrabold tracking-tight text-base-content">系統設定</h2>

      <p class="mt-2 text-sm font-medium text-base-content/65">管理應用程式設定。</p>
    </div>

    <div class="space-y-6">
      <div class="tracker-panel card rounded-lg">
        <div class="card-body p-0">
          <div class="border-b border-base-300/70 px-6 py-5">
            <h3 class="text-base font-bold text-base-content">旅程追蹤設定</h3>

            <p class="mt-0.5 text-sm font-medium text-base-content/60">
              管理旅程追蹤的自動監察排程
            </p>
          </div>

          <form class="space-y-5 p-6" @submit.prevent="saveSettings('itinerary')">
            <label
              class="label cursor-pointer justify-start gap-4 rounded-lg border border-base-300/70 bg-base-200/40 px-4 py-4"
            >
              <input
                v-model="form.itinerary.disable_departured_itineraries"
                type="checkbox"
                class="toggle toggle-primary"
              />

              <div>
                <p class="text-sm font-bold text-base-content">暫停追蹤過期的旅程</p>

                <p class="text-xs font-medium text-base-content/55">
                  當旅程中最後航班出發日期過後，暫停該項目的票價追蹤。<br />
                </p>
              </div>
            </label>

            <div
              class="flex flex-col items-start gap-3 border-t border-base-300/70 pt-4 sm:flex-row sm:items-center"
            >
              <button type="submit" :disabled="ui.saving" class="btn btn-primary">
                <span v-if="ui.saving" class="loading loading-sm loading-spinner"></span>
                {{ ui.saving ? '儲存中...' : '儲存設定' }}
              </button>

              <p v-if="ui.lastSaved" class="text-xs font-medium text-success">
                ✓ 最後儲存於 {{ ui.lastSaved }}
              </p>
            </div>
          </form>
        </div>
      </div>

      <div class="tracker-panel card rounded-lg">
        <div class="card-body p-0">
          <div class="border-b border-base-300/70 px-6 py-5">
            <h3 class="text-base font-bold text-base-content">預設搜尋條件</h3>

            <p class="mt-0.5 text-sm font-medium text-base-content/60">
              旅程未設定搜尋條件時，自動追蹤將採用以下預設
            </p>
          </div>

          <form class="space-y-5 p-6" @submit.prevent="saveSettings('search')">
            <FetchFilters v-model="filters" />

            <div
              class="flex flex-col items-start gap-3 border-t border-base-300/70 pt-4 sm:flex-row sm:items-center"
            >
              <button type="submit" :disabled="ui.saving" class="btn btn-primary">
                <span v-if="ui.saving" class="loading loading-sm loading-spinner"></span>
                {{ ui.saving ? '儲存中...' : '儲存設定' }}
              </button>

              <p v-if="ui.lastSaved" class="text-xs font-medium text-success">
                ✓ 最後儲存於 {{ ui.lastSaved }}
              </p>
            </div>
          </form>
        </div>
      </div>

      <div class="tracker-panel card rounded-lg">
        <div class="card-body p-0">
          <div class="border-b border-base-300/70 px-6 py-5">
            <h3 class="text-base font-bold text-base-content">貨幣與匯率設定</h3>

            <p class="mt-0.5 text-sm font-medium text-base-content/60">
              設定票價數據的顯示貨幣與 FXRatesAPI 快取機制
            </p>
          </div>

          <form class="space-y-5 p-6" @submit.prevent="saveSettings('currency')">
            <fieldset class="fieldset">
              <legend class="fieldset-legend text-sm font-bold">基準貨幣 / 顯示貨幣</legend>

              <select v-model="form.currency.base_currency" class="select-bordered select w-full">
                <option v-for="code in supportedCurrencies" :key="code" :value="code">
                  {{ code }}
                </option>
              </select>
            </fieldset>

            <fieldset class="fieldset">
              <legend class="fieldset-legend text-sm font-bold">
                FXRatesAPI API 金鑰
                <span class="text-base-content/45">（選填）</span>
              </legend>

              <input
                v-model="form.currency.fxrates_api_key"
                type="text"
                class="input-bordered input w-full"
              />

              <p class="label text-xs text-base-content/55">
                留空時系統仍會嘗試獲取匯率數據。若失敗，請到 FXRatesAPI 註冊以取得 API 金鑰。
              </p>
            </fieldset>

            <fieldset class="fieldset">
              <legend class="fieldset-legend text-sm font-bold">快取有效時間 (TTL；秒)</legend>

              <input
                v-model.number="form.currency.cache_ttl"
                type="number"
                min="1"
                class="input-bordered input w-full"
              />

              <p class="label text-xs text-base-content/55">
                快取時間愈短，匯率數據愈貼近現實，但亦會增加 API 查詢次數。建議根據 FXRatesAPI
                的用量限制與更新頻率進行調整。
              </p>
            </fieldset>

            <div
              class="flex flex-col items-start gap-3 border-t border-base-300/70 pt-4 sm:flex-row sm:items-center"
            >
              <button type="submit" :disabled="ui.saving" class="btn btn-primary">
                <span v-if="ui.saving" class="loading loading-sm loading-spinner"></span>
                {{ ui.saving ? '儲存中...' : '儲存設定' }}
              </button>

              <button type="button" class="btn btn-outline" @click="ui.fxModalOpen = true">
                檢視匯率
              </button>

              <p v-if="ui.lastSaved" class="text-xs font-medium text-success">
                ✓ 最後儲存於 {{ ui.lastSaved }}
              </p>
            </div>
          </form>
        </div>
      </div>

      <div class="tracker-panel card rounded-lg">
        <div class="card-body p-0">
          <div class="border-b border-base-300/70 px-6 py-5">
            <h3 class="text-base font-bold text-base-content">SMTP 伺服器</h3>

            <p class="mt-0.5 text-sm font-medium text-base-content/60">設定寄件伺服器連線資料</p>
          </div>

          <form class="space-y-5 p-6" @submit.prevent="saveSettings('smtp')">
            <div class="grid gap-4 md:grid-cols-3">
              <div class="md:col-span-2">
                <fieldset class="fieldset">
                  <legend class="fieldset-legend text-sm font-bold">伺服器主機 (Host)</legend>

                  <input
                    v-model="form.smtp.host"
                    type="text"
                    placeholder="mail.example.com"
                    class="input-bordered input w-full"
                  />
                </fieldset>
              </div>

              <div>
                <fieldset class="fieldset">
                  <legend class="fieldset-legend text-sm font-bold">連接埠 (Port)</legend>

                  <input
                    v-model.number="form.smtp.port"
                    type="number"
                    placeholder="587"
                    class="input-bordered input w-full"
                  />
                </fieldset>
              </div>
            </div>

            <fieldset class="fieldset">
              <legend class="fieldset-legend text-sm font-bold">
                寄件者電郵地址
                <span class="text-base-content/45">（選填）</span>
              </legend>

              <input
                v-model="form.smtp.sender_email"
                type="email"
                placeholder="noreply@example.com"
                class="input-bordered input w-full"
              />

              <p class="label text-xs text-base-content/55">
                留空則預設使用登入的用戶名稱作為寄件者電郵
              </p>
            </fieldset>

            <fieldset class="fieldset">
              <legend class="fieldset-legend text-sm font-bold">SMTP 加密協定</legend>

              <select v-model="form.smtp.protocol" class="select-bordered select w-full">
                <option value="STARTTLS">STARTTLS</option>

                <option value="SMTP_SSL">SSL / 無加密</option>
              </select>
            </fieldset>

            <label
              class="label cursor-pointer justify-start gap-4 rounded-lg border border-base-300/70 bg-base-200/40 px-4 py-4"
            >
              <input
                v-model="form.smtp.require_auth"
                type="checkbox"
                class="toggle toggle-primary"
              />

              <div>
                <p class="text-sm font-bold text-base-content">需要 SMTP 驗證</p>

                <p class="text-xs font-medium text-base-content/55">
                  停用後可配合無需登入的開放中繼 (Open Relay) 伺服器使用
                </p>
              </div>
            </label>

            <div
              :class="[
                'space-y-5 rounded-lg border border-base-300/70 p-4 transition-all',
                form.smtp.require_auth
                  ? 'bg-base-200/40 opacity-100'
                  : 'pointer-events-none bg-base-200/25 opacity-60',
              ]"
            >
              <fieldset class="fieldset">
                <legend class="fieldset-legend text-sm font-bold">用戶名稱</legend>

                <input
                  v-model="form.smtp.user"
                  type="email"
                  placeholder="user@example.com"
                  :disabled="!form.smtp.require_auth"
                  class="input-bordered input w-full"
                />
              </fieldset>

              <fieldset class="fieldset">
                <legend class="fieldset-legend text-sm font-bold">密碼</legend>

                <input
                  v-model="form.smtp.password"
                  type="password"
                  :placeholder="props.settings.smtp?.password ? '留空表示不作更改' : '請輸入密碼'"
                  :disabled="!form.smtp.require_auth"
                  class="input-bordered input w-full"
                />
              </fieldset>
            </div>

            <div
              class="flex flex-col items-start gap-3 border-t border-base-300/70 pt-4 sm:flex-row sm:items-center"
            >
              <button type="submit" :disabled="ui.saving" class="btn btn-primary">
                <span v-if="ui.saving" class="loading loading-sm loading-spinner"></span>
                {{ ui.saving ? '儲存中...' : '儲存設定' }}
              </button>

              <p v-if="ui.lastSaved" class="text-xs font-medium text-success">
                ✓ 最後儲存於 {{ ui.lastSaved }}
              </p>
            </div>
          </form>
        </div>
      </div>

      <div class="tracker-panel card rounded-lg">
        <div class="card-body p-0">
          <div class="border-b border-base-300/70 px-6 py-5">
            <h3 class="text-base font-bold text-base-content">發送測試電郵</h3>

            <p class="mt-0.5 text-sm font-medium text-base-content/60">
              驗證 SMTP 伺服器設定是否正確
            </p>
          </div>

          <div class="p-6">
            <div
              v-if="!$props.settings.smtp?.host || !$props.settings.smtp?.port"
              class="alert rounded-lg alert-warning"
            >
              <span>請先完成 SMTP 伺服器設定</span>
            </div>

            <div v-else class="space-y-4">
              <fieldset class="fieldset">
                <legend class="fieldset-legend text-sm font-bold">收件者電郵地址</legend>

                <input
                  v-model="ui.testAddress"
                  type="email"
                  placeholder="test@example.com"
                  class="input-bordered input w-full"
                />
              </fieldset>

              <button
                :disabled="!ui.testAddress || ui.testLoading"
                class="btn w-full btn-neutral"
                @click="sendTestEmail"
              >
                <span v-if="ui.testLoading" class="loading loading-sm loading-spinner"></span>
                {{ ui.testLoading ? '發送中...' : '發送測試電郵' }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <div class="tracker-panel card rounded-lg">
        <div class="card-body p-0">
          <div class="border-b border-base-300/70 px-6 py-5">
            <h3 class="text-base font-bold text-base-content">通知收件者名單</h3>

            <p class="mt-0.5 text-sm font-medium text-base-content/60">接收系統通知的郵件地址</p>
          </div>

          <form class="space-y-4 p-6">
            <fieldset class="fieldset">
              <legend class="fieldset-legend text-sm font-bold">電郵地址清單</legend>

              <textarea
                v-model="form.email.recipients"
                placeholder="user@example.com&#10;admin@example.com"
                rows="4"
                class="textarea-bordered textarea w-full"
              ></textarea>

              <p class="label text-xs text-base-content/55">每行填寫一個電郵地址</p>
            </fieldset>

            <button
              type="submit"
              :disabled="ui.saving"
              class="btn w-full btn-primary"
              @click.prevent="saveSettings('email')"
            >
              <span v-if="ui.saving" class="loading loading-sm loading-spinner"></span>
              {{ ui.saving ? '儲存中...' : '儲存設定' }}
            </button>
          </form>
        </div>
      </div>
    </div>

    <div :class="['modal', { 'modal-open': ui.fxModalOpen }]" role="dialog">
      <div class="modal-box max-w-2xl overflow-hidden rounded-lg border border-base-300 p-0">
        <div class="flex items-center justify-between border-b border-base-300/70 px-6 py-5">
          <div>
            <h3 class="text-base font-bold text-base-content">貨幣匯率</h3>

            <p class="mt-0.5 text-sm font-medium text-base-content/60">
              目前以 {{ fxStatusState.base_currency }} 作為基準貨幣
            </p>
          </div>

          <button
            type="button"
            class="btn btn-circle btn-ghost btn-sm"
            @click="ui.fxModalOpen = false"
          >
            ✕
          </button>
        </div>

        <div class="max-h-[65vh] space-y-4 overflow-y-auto p-6">
          <div class="flex items-center gap-3">
            <div class="grow rounded-lg border border-base-300/70 bg-base-200/40 px-3 py-2">
              <p class="text-xs font-bold tracking-wider text-base-content/55 uppercase">
                最後更新時間
              </p>

              <p class="mt-1 text-sm font-semibold text-base-content">{{ fxStatusTime }}</p>
            </div>

            <div class="flex items-center justify-end">
              <button
                class="btn btn-neutral"
                :disabled="ui.refreshingRates"
                @click="refreshFxRates"
              >
                <span v-if="ui.refreshingRates" class="loading loading-sm loading-spinner"></span>
                {{ ui.refreshingRates ? '更新中...' : '更新匯率' }}
              </button>
            </div>
          </div>

          <div v-if="fxStatusState.error" class="alert rounded-lg alert-warning">
            <span>{{ fxStatusState.error }}</span>
          </div>

          <div class="overflow-x-auto rounded-xl border border-base-300/70">
            <table class="table w-full table-zebra text-sm">
              <thead>
                <tr>
                  <th>貨幣</th>

                  <th class="text-right">1 {{ fxStatusState.base_currency }} =</th>
                </tr>
              </thead>

              <tbody>
                <tr v-if="displayedRates.length === 0">
                  <td colspan="2" class="text-center text-base-content/55">暫無匯率資料</td>
                </tr>

                <tr
                  v-for="item in displayedRates.toSorted((a, b) => a.code.localeCompare(b.code))"
                  :key="item.code"
                >
                  <td class="font-semibold">{{ item.code }}</td>

                  <td class="text-right">{{ Number(item.value).toFixed(6) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div class="modal-backdrop" @click="ui.fxModalOpen = false"></div>
    </div>
  </AppLayout>
</template>
