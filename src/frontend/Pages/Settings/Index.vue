<script setup lang="ts">
import AppLayout from '@/Layouts/AppLayout.vue'
import { computed, reactive } from 'vue'
import { useToast } from 'vue-toast-notification'

const props = defineProps<{
  settings: {
    currency?: {
      baseCurrency?: string
      fxratesApiKey?: string
      cacheTtl?: string | number
    }
    email?: {
      recipients?: string
    }
    itinerary?: {
      disableDeparturedItineraries?: string
    }
    smtp?: {
      host?: string
      port?: string | number
      user?: string
      password?: string
      senderEmail?: string
      requireAuth?: string
      protocol?: string
    }
  }
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
      props.settings.itinerary?.disableDeparturedItineraries !== 'false',
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
  if (!fxStatusState.last_updated) {
    return '—'
  }
  const parsed = new Date(fxStatusState.last_updated)
  return Number.isNaN(parsed.getTime())
    ? fxStatusState.last_updated
    : parsed.toLocaleString('zh-HK')
})

function saveSettings(sec: 'email' | 'currency' | 'smtp' | 'itinerary') {
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
  }

  fetch('/api/settings', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ [sec]: payloads[sec] }),
  })
    .then((res) => res.json())
    .then((data) => {
      if (!data.success) {
        return toast.error(data.message || '保存失敗')
      }
      toast.success('設定已保存')
      ui.lastSaved = new Date().toLocaleString('zh-HK')

      if (sec === 'smtp') {
        form.smtp.password = ''
      }
    })
    .catch(() => toast.error('保存設定時出錯'))
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
        throw new Error(res.message || 'Unable to refresh FX rates')
      }

      const d = res.data || {}
      Object.assign(fxStatusState, {
        base_currency: d.base_currency ?? form.currency.base_currency,
        last_updated: d.last_updated ?? null,
        rates: d.rates ?? {},
        error: null,
      })

      toast.success('已更新最新匯率')
    })
    .catch((err: Error) => {
      fxStatusState.error = err.message
      toast.error(err.message || '刷新匯率失敗')
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
        toast.success(data.message || '測試郵件已發送')
        ui.testAddress = ''
      } else {
        toast.error(data.message || '發送失敗')
      }
    })
    .catch(() => toast.error('發送測試郵件時出錯'))
    .finally(() => {
      ui.testLoading = false
    })
}
</script>

<template>
  <AppLayout>
    <div class="mb-8">
      <h2 class="text-3xl font-extrabold tracking-tight text-base-content">設定</h2>

      <p class="mt-2 text-sm font-medium text-base-content/65">管理您的應用程式設定</p>
    </div>

    <div class="space-y-6">
      <div class="tracker-panel card rounded-lg">
        <div class="card-body p-0">
          <div class="border-b border-base-300/70 px-6 py-5">
            <h3 class="text-base font-bold text-base-content">行程設定</h3>

            <p class="mt-0.5 text-sm font-medium text-base-content/60">管理行程相關設定</p>
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
                <p class="text-sm font-bold text-base-content">停止追蹤過期航線</p>

                <p class="text-xs font-medium text-base-content/55">
                  自動在航線出發日期過後，停止追蹤機票價格。<br />
                  以最後出發的航班日期作為準。
                </p>
              </div>
            </label>

            <div
              class="flex flex-col items-start gap-3 border-t border-base-300/70 pt-4 sm:flex-row sm:items-center"
            >
              <button type="submit" :disabled="ui.saving" class="btn btn-primary">
                <span v-if="ui.saving" class="loading loading-sm loading-spinner"></span>
                {{ ui.saving ? '保存中...' : '保存設定' }}
              </button>

              <p v-if="ui.lastSaved" class="text-xs font-medium text-success">
                ✓ 最後保存於 {{ ui.lastSaved }}
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
              設定票價顯示基準貨幣與 FXRatesAPI 快取策略
            </p>
          </div>

          <form class="space-y-5 p-6" @submit.prevent="saveSettings('currency')">
            <fieldset class="fieldset">
              <legend class="fieldset-legend text-sm font-bold">基準貨幣／顯示貨幣</legend>

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
                留空時系統仍會嘗試向 FXRatesAPI 查詢匯率；若失敗，請到 FXRatesAPI 註冊以取得 API
                Key。
              </p>
            </fieldset>

            <fieldset class="fieldset">
              <legend class="fieldset-legend text-sm font-bold">快取有效秒數 (TTL)</legend>

              <input
                v-model.number="form.currency.cache_ttl"
                type="number"
                min="1"
                class="input-bordered input w-full"
              />

              <p class="label text-xs text-base-content/55">
                越短的快取時間可以讓匯率更貼近實際，但同時也會增加查詢次數。建議根據 FXRatesAPI
                的使用限制與更新頻率來調整此值。
              </p>
            </fieldset>

            <div
              class="flex flex-col items-start gap-3 border-t border-base-300/70 pt-4 sm:flex-row sm:items-center"
            >
              <button type="submit" :disabled="ui.saving" class="btn btn-primary">
                <span v-if="ui.saving" class="loading loading-sm loading-spinner"></span>
                {{ ui.saving ? '保存中...' : '保存設定' }}
              </button>

              <button type="button" class="btn btn-outline" @click="ui.fxModalOpen = true">
                查看目前匯率
              </button>

              <p v-if="ui.lastSaved" class="text-xs font-medium text-success">
                ✓ 最後保存於 {{ ui.lastSaved }}
              </p>
            </div>
          </form>
        </div>
      </div>

      <div class="tracker-panel card rounded-lg">
        <div class="card-body p-0">
          <div class="border-b border-base-300/70 px-6 py-5">
            <h3 class="text-base font-bold text-base-content">SMTP 伺服器</h3>

            <p class="mt-0.5 text-sm font-medium text-base-content/60">設定寄件伺服器連線資訊</p>
          </div>

          <form class="space-y-5 p-6" @submit.prevent="saveSettings('smtp')">
            <div class="grid gap-4 md:grid-cols-3">
              <div class="md:col-span-2">
                <fieldset class="fieldset">
                  <legend class="fieldset-legend text-sm font-bold">主機</legend>

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
                  <legend class="fieldset-legend text-sm font-bold">連接埠</legend>

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
                發件人地址
                <span class="text-base-content/45">（選填）</span>
              </legend>

              <input
                v-model="form.smtp.sender_email"
                type="email"
                placeholder="noreply@example.com"
                class="input-bordered input w-full"
              />

              <p class="label text-xs text-base-content/55">留空則使用登入用戶名作為發件人</p>
            </fieldset>

            <fieldset class="fieldset">
              <legend class="fieldset-legend text-sm font-bold">SMTP 協議</legend>

              <select v-model="form.smtp.protocol" class="select-bordered select w-full">
                <option value="STARTTLS">STARTTLS</option>

                <option value="SMTP_SSL">SSL／無</option>
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
                  停用後可使用無需登入的開放中繼伺服器
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
                <legend class="fieldset-legend text-sm font-bold">使用者名稱</legend>

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
                  :placeholder="props.settings.smtp?.password ? '不更改請留空' : '輸入密碼'"
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
                {{ ui.saving ? '保存中...' : '保存設定' }}
              </button>

              <p v-if="ui.lastSaved" class="text-xs font-medium text-success">
                ✓ 最後保存於 {{ ui.lastSaved }}
              </p>
            </div>
          </form>
        </div>
      </div>

      <div class="tracker-panel card rounded-lg">
        <div class="card-body p-0">
          <div class="border-b border-base-300/70 px-6 py-5">
            <h3 class="text-base font-bold text-base-content">測試郵件</h3>

            <p class="mt-0.5 text-sm font-medium text-base-content/60">驗證 SMTP 設定是否正確</p>
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
                <legend class="fieldset-legend text-sm font-bold">收件地址</legend>

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
                {{ ui.testLoading ? '發送中...' : '發送測試郵件' }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <div class="tracker-panel card rounded-lg">
        <div class="card-body p-0">
          <div class="border-b border-base-300/70 px-6 py-5">
            <h3 class="text-base font-bold text-base-content">通知收件者</h3>

            <p class="mt-0.5 text-sm font-medium text-base-content/60">接收系統通知的郵件地址</p>
          </div>

          <form class="space-y-4 p-6">
            <fieldset class="fieldset">
              <legend class="fieldset-legend text-sm font-bold">郵件地址</legend>

              <textarea
                v-model="form.email.recipients"
                placeholder="user@example.com&#10;admin@example.com"
                rows="4"
                class="textarea-bordered textarea w-full"
              ></textarea>

              <p class="label text-xs text-base-content/55">每行一個郵件地址</p>
            </fieldset>

            <button
              type="submit"
              :disabled="ui.saving"
              class="btn w-full btn-primary"
              @click.prevent="saveSettings('email')"
            >
              <span v-if="ui.saving" class="loading loading-sm loading-spinner"></span>
              {{ ui.saving ? '保存中...' : '保存設定' }}
            </button>
          </form>
        </div>
      </div>
    </div>

    <div :class="['modal', { 'modal-open': ui.fxModalOpen }]" role="dialog">
      <div class="modal-box max-w-2xl overflow-hidden rounded-lg border border-base-300 p-0">
        <div class="flex items-center justify-between border-b border-base-300/70 px-6 py-5">
          <div>
            <h3 class="text-base font-bold text-base-content">貨幣匯率換算</h3>

            <p class="mt-0.5 text-sm font-medium text-base-content/60">
              目前使用 {{ fxStatusState.base_currency }} 作為換算基準
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
                最後更新
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
                {{ ui.refreshingRates ? '更新中...' : '下載最新匯率' }}
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
