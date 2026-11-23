<script setup lang="ts">
import AppLayout from '@/Layouts/AppLayout.vue'
import FieldError from '@/Components/FieldError.vue'
import type { Settings } from '@/types'
import { formatLocalDateTime } from '@/utils/timezone'
import { router, useForm, usePage } from '@inertiajs/vue3'
import { ref } from 'vue'
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

const itineraryForm = useForm({ ...props.settings.itinerary })
const currencyForm = useForm({ ...props.settings.currency })
const smtpForm = useForm({ ...props.settings.smtp, password: '' })
const emailForm = useForm({ ...props.settings.email })

const testEmail = ref({ address: '' })

const ui = ref({
  loading: null as 'refresh' | 'test-email' | null,
  saved: { itinerary: false, currency: false, smtp: false, email: false } as Record<
    'itinerary' | 'currency' | 'smtp' | 'email',
    boolean
  >,
  fxModalOpen: false,
})

// the page route redirects with the session errors bag; useForm.errors only fills from 422s
function toastSaveError(): void {
  const errors = usePage().props.errors ?? {}
  toast.error(errors.settings ?? '儲存失敗')
}

function refreshFxRates() {
  ui.value.loading = 'refresh'
  fetch('/api/settings/fx-rates/refresh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ base_currency: currencyForm.baseCurrency }),
  })
    .then((res) => {
      if (!res.ok) throw new Error()
      return router.reload()
    })
    // fetch action, not a page visit: the server flash is unreachable, so the failure copy is local
    .catch(() => toast.error('更新匯率失敗，請稍後再試'))
    .finally(() => {
      ui.value.loading = null
    })
}

function sendTestEmail() {
  if (!testEmail.value.address) {
    return
  }

  ui.value.loading = 'test-email'
  fetch('/api/settings/test-email', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ recipient: testEmail.value.address }),
  })
    .then((res) => res.json().then((body) => ({ ok: res.ok, body })))
    .then(({ ok, body }) => {
      if (ok) {
        toast.success(body.message || '測試電郵已發送')
        testEmail.value.address = ''
      } else {
        toast.error(body.message || '發送失敗')
      }
    })
    .catch(() => toast.error('發送測試電郵時發生錯誤'))
    .finally(() => {
      ui.value.loading = null
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

          <form
            class="space-y-5 p-6"
            @input="ui.saved.itinerary = false"
            @submit.prevent="
              itineraryForm
                .transform((draft) => ({
                  itinerary: { disable_departured_itineraries: draft.disableDeparturedItineraries },
                }))
                .post('/settings', {
                  preserveScroll: true,
                  onSuccess: () => {
                    itineraryForm.defaults(props.settings.itinerary).reset()
                    ui.saved.itinerary = true
                  },
                  onError: toastSaveError,
                })
            "
          >
            <label
              class="label cursor-pointer justify-start gap-4 rounded-lg border border-base-300/70 bg-base-200/40 px-4 py-4"
            >
              <input
                v-model="itineraryForm.disableDeparturedItineraries"
                type="checkbox"
                class="toggle toggle-primary"
              />

              <div>
                <p class="text-sm font-bold text-base-content">暫停追蹤過期的旅程</p>

                <p class="text-xs font-medium text-base-content/55">
                  當旅程中最後航班出發日期過後，暫停該項目的票價追蹤，出發後 30
                  天的旅程會自動封存。<br />
                </p>
              </div>
            </label>

            <FieldError field="itinerary.disableDeparturedItineraries" />

            <div
              class="flex flex-col items-start gap-3 border-t border-base-300/70 pt-4 sm:flex-row sm:items-center"
            >
              <button type="submit" :disabled="itineraryForm.processing" class="btn btn-primary">
                <span
                  v-if="itineraryForm.processing"
                  class="loading loading-sm loading-spinner"
                ></span>
                {{ itineraryForm.processing ? '儲存中...' : '儲存設定' }}
              </button>

              <span v-if="ui.saved.itinerary" class="text-success" title="已儲存">✓</span>
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

          <form
            class="space-y-5 p-6"
            @input="ui.saved.currency = false"
            @submit.prevent="
              currencyForm
                .transform((draft) => ({
                  currency: {
                    base_currency: draft.baseCurrency,
                    fxrates_api_key: draft.fxratesApiKey,
                    cache_ttl: draft.cacheTtl,
                  },
                }))
                .post('/settings', {
                  preserveScroll: true,
                  onSuccess: () => {
                    currencyForm.defaults(props.settings.currency).reset()
                    ui.saved.currency = true
                  },
                  onError: toastSaveError,
                })
            "
          >
            <fieldset class="fieldset">
              <legend class="fieldset-legend text-sm font-bold">基準貨幣 / 顯示貨幣</legend>

              <select v-model="currencyForm.baseCurrency" class="select-bordered select w-full">
                <option v-for="code in props.supportedCurrencies" :key="code" :value="code">
                  {{ code }}
                </option>
              </select>

              <FieldError field="currency.baseCurrency" />
            </fieldset>

            <fieldset class="fieldset">
              <legend class="fieldset-legend text-sm font-bold">
                FXRatesAPI API 金鑰
                <span class="text-base-content/45">（選填）</span>
              </legend>

              <input
                v-model="currencyForm.fxratesApiKey"
                type="text"
                class="input-bordered input w-full"
              />

              <FieldError field="currency.fxratesApiKey" />

              <p class="label text-xs text-base-content/55">
                留空時系統仍會嘗試獲取匯率數據。若失敗，請到 FXRatesAPI 註冊以取得 API 金鑰。
              </p>
            </fieldset>

            <fieldset class="fieldset">
              <legend class="fieldset-legend text-sm font-bold">快取有效時間 (TTL；秒)</legend>

              <input
                v-model.number="currencyForm.cacheTtl"
                type="number"
                min="1"
                class="input-bordered input w-full"
              />

              <FieldError field="currency.cacheTtl" />

              <p class="label text-xs text-base-content/55">
                快取時間愈短，匯率數據愈貼近現實，但亦會增加 API 查詢次數。建議根據 FXRatesAPI
                的用量限制與更新頻率進行調整。
              </p>
            </fieldset>

            <div
              class="flex flex-col items-start gap-3 border-t border-base-300/70 pt-4 sm:flex-row sm:items-center"
            >
              <button type="submit" :disabled="currencyForm.processing" class="btn btn-primary">
                <span
                  v-if="currencyForm.processing"
                  class="loading loading-sm loading-spinner"
                ></span>
                {{ currencyForm.processing ? '儲存中...' : '儲存設定' }}
              </button>

              <button type="button" class="btn btn-outline" @click="ui.fxModalOpen = true">
                檢視匯率
              </button>

              <span v-if="ui.saved.currency" class="text-success" title="已儲存">✓</span>
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

          <form
            class="space-y-5 p-6"
            @input="ui.saved.smtp = false"
            @submit.prevent="
              smtpForm
                .transform((draft) => ({
                  smtp: {
                    host: draft.host,
                    port: draft.port,
                    user: draft.user,
                    sender_email: draft.senderEmail,
                    require_auth: draft.requireAuth,
                    protocol: draft.protocol,
                    ...(draft.password && { password: draft.password }),
                  },
                }))
                .post('/settings', {
                  preserveScroll: true,
                  onSuccess: () => {
                    smtpForm.defaults(props.settings.smtp).reset()
                    ui.saved.smtp = true
                  },
                  onError: toastSaveError,
                })
            "
          >
            <div class="grid gap-4 md:grid-cols-3">
              <div class="md:col-span-2">
                <fieldset class="fieldset">
                  <legend class="fieldset-legend text-sm font-bold">伺服器主機 (Host)</legend>

                  <input
                    v-model="smtpForm.host"
                    type="text"
                    placeholder="mail.example.com"
                    class="input-bordered input w-full"
                  />

                  <FieldError field="smtp.host" />
                </fieldset>
              </div>

              <div>
                <fieldset class="fieldset">
                  <legend class="fieldset-legend text-sm font-bold">連接埠 (Port)</legend>

                  <input
                    v-model.number="smtpForm.port"
                    type="number"
                    placeholder="587"
                    class="input-bordered input w-full"
                  />

                  <FieldError field="smtp.port" />
                </fieldset>
              </div>
            </div>

            <fieldset class="fieldset">
              <legend class="fieldset-legend text-sm font-bold">
                寄件者電郵地址
                <span class="text-base-content/45">（選填）</span>
              </legend>

              <input
                v-model="smtpForm.senderEmail"
                type="email"
                placeholder="noreply@example.com"
                class="input-bordered input w-full"
              />

              <FieldError field="smtp.senderEmail" />

              <p class="label text-xs text-base-content/55">
                留空則預設使用登入的用戶名稱作為寄件者電郵
              </p>
            </fieldset>

            <fieldset class="fieldset">
              <legend class="fieldset-legend text-sm font-bold">SMTP 加密協定</legend>

              <select v-model="smtpForm.protocol" class="select-bordered select w-full">
                <option value="STARTTLS">STARTTLS</option>

                <option value="SMTP_SSL">SSL / 無加密</option>
              </select>

              <FieldError field="smtp.protocol" />
            </fieldset>

            <label
              class="label cursor-pointer justify-start gap-4 rounded-lg border border-base-300/70 bg-base-200/40 px-4 py-4"
            >
              <input v-model="smtpForm.requireAuth" type="checkbox" class="toggle toggle-primary" />

              <div>
                <p class="text-sm font-bold text-base-content">需要 SMTP 驗證</p>

                <p class="text-xs font-medium text-base-content/55">
                  停用後可配合無需登入的開放中繼 (Open Relay) 伺服器使用
                </p>
              </div>
            </label>

            <FieldError field="smtp.requireAuth" />

            <div
              :class="[
                'space-y-5 rounded-lg border border-base-300/70 p-4 transition-all',
                smtpForm.requireAuth
                  ? 'bg-base-200/40 opacity-100'
                  : 'pointer-events-none bg-base-200/25 opacity-60',
              ]"
            >
              <fieldset class="fieldset">
                <legend class="fieldset-legend text-sm font-bold">用戶名稱</legend>

                <input
                  v-model="smtpForm.user"
                  type="email"
                  placeholder="user@example.com"
                  :disabled="!smtpForm.requireAuth"
                  class="input-bordered input w-full"
                />

                <FieldError field="smtp.user" />
              </fieldset>

              <fieldset class="fieldset">
                <legend class="fieldset-legend text-sm font-bold">密碼</legend>

                <input
                  v-model="smtpForm.password"
                  type="password"
                  placeholder="請輸入密碼"
                  :disabled="!smtpForm.requireAuth"
                  class="input-bordered input w-full"
                />
              </fieldset>
            </div>

            <div
              class="flex flex-col items-start gap-3 border-t border-base-300/70 pt-4 sm:flex-row sm:items-center"
            >
              <button type="submit" :disabled="smtpForm.processing" class="btn btn-primary">
                <span v-if="smtpForm.processing" class="loading loading-sm loading-spinner"></span>
                {{ smtpForm.processing ? '儲存中...' : '儲存設定' }}
              </button>

              <span v-if="ui.saved.smtp" class="text-success" title="已儲存">✓</span>
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
              v-if="!props.settings.smtp?.host || !props.settings.smtp?.port"
              class="alert rounded-lg alert-warning"
            >
              <span>請先完成 SMTP 伺服器設定</span>
            </div>

            <div v-else class="space-y-4">
              <fieldset class="fieldset">
                <legend class="fieldset-legend text-sm font-bold">收件者電郵地址</legend>

                <input
                  v-model="testEmail.address"
                  type="email"
                  placeholder="test@example.com"
                  class="input-bordered input w-full"
                />
              </fieldset>

              <button
                :disabled="!testEmail.address || ui.loading === 'test-email'"
                class="btn w-full btn-neutral"
                @click="sendTestEmail"
              >
                <span
                  v-if="ui.loading === 'test-email'"
                  class="loading loading-sm loading-spinner"
                ></span>
                {{ ui.loading === 'test-email' ? '發送中...' : '發送測試電郵' }}
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

          <form
            class="space-y-4 p-6"
            @input="ui.saved.email = false"
            @submit.prevent="
              emailForm
                .transform((draft) => ({ email: { recipients: draft.recipients } }))
                .post('/settings', {
                  preserveScroll: true,
                  onSuccess: () => {
                    emailForm.defaults(props.settings.email).reset()
                    ui.saved.email = true
                  },
                  onError: toastSaveError,
                })
            "
          >
            <fieldset class="fieldset">
              <legend class="fieldset-legend text-sm font-bold">電郵地址清單</legend>

              <textarea
                v-model="emailForm.recipients"
                placeholder="user@example.com&#10;admin@example.com"
                rows="4"
                class="textarea-bordered textarea w-full"
              ></textarea>

              <FieldError field="email.recipients" />

              <p class="label text-xs text-base-content/55">每行填寫一個電郵地址</p>
            </fieldset>

            <button type="submit" :disabled="emailForm.processing" class="btn w-full btn-primary">
              <span v-if="emailForm.processing" class="loading loading-sm loading-spinner"></span>
              {{ emailForm.processing ? '儲存中...' : '儲存設定' }}
            </button>

            <span v-if="ui.saved.email" class="text-success" title="已儲存">✓</span>
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
              目前以 {{ props.fxStatus?.baseCurrency ?? 'HKD' }} 作為基準貨幣
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

              <p class="mt-1 text-sm font-semibold text-base-content">
                {{ formatLocalDateTime(props.fxStatus?.lastUpdated) }}
              </p>
            </div>

            <div class="flex items-center justify-end">
              <button
                class="btn btn-neutral"
                :disabled="ui.loading === 'refresh'"
                @click="refreshFxRates"
              >
                <span
                  v-if="ui.loading === 'refresh'"
                  class="loading loading-sm loading-spinner"
                ></span>
                {{ ui.loading === 'refresh' ? '更新中...' : '更新匯率' }}
              </button>
            </div>
          </div>

          <div v-if="props.fxStatus?.error" class="alert rounded-lg alert-warning">
            <span>{{ props.fxStatus?.error }}</span>
          </div>

          <div class="overflow-x-auto rounded-xl border border-base-300/70">
            <table class="table w-full table-zebra text-sm">
              <thead>
                <tr>
                  <th>貨幣</th>

                  <th class="text-right">1 {{ props.fxStatus?.baseCurrency ?? 'HKD' }} =</th>
                </tr>
              </thead>

              <tbody>
                <tr v-if="!Object.keys(props.fxStatus?.rates ?? {}).length">
                  <td colspan="2" class="text-center text-base-content/55">暫無匯率資料</td>
                </tr>

                <tr
                  v-for="code in props.supportedCurrencies
                    .filter((code) => code !== (props.fxStatus?.baseCurrency ?? 'HKD'))
                    .filter((code) => (props.fxStatus?.rates ?? {})[code] !== undefined)
                    .toSorted((a, b) => a.localeCompare(b))"
                  :key="code"
                >
                  <td class="font-semibold">{{ code }}</td>

                  <td class="text-right">{{ Number(props.fxStatus?.rates?.[code]).toFixed(6) }}</td>
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
