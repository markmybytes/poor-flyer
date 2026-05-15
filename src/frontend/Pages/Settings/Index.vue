<script setup lang="ts">
import AppLayout from '@/Layouts/AppLayout.vue'
import { reactive } from 'vue'

const props = defineProps<{
  settings: {
    smtp?: {
      host?: string
      port?: string | number
      user?: string
      password?: string
      sender_email?: string
      require_auth?: string
      protocol?: string
    }
    email?: {
      recipients?: string
    }
  }
}>()

const form = reactive({
  smtp: {
    host: props.settings.smtp?.host ?? '',
    port: Number(props.settings.smtp?.port ?? 587),
    user: props.settings.smtp?.user ?? '',
    password: '',
    sender_email: props.settings.smtp?.sender_email ?? '',
    require_auth: props.settings.smtp?.require_auth !== 'false',
    protocol: props.settings.smtp?.protocol ?? 'STARTTLS',
  },
  email: {
    recipients: props.settings.email?.recipients ?? '',
  },
})

const ui = reactive({
  saving: false,
  testAddress: '',
  testLoading: false,
  message: null as { text: string; type: 'success' | 'error' } | null,
  lastSaved: null as string | null,
})

function setMessage(text: string, type: 'success' | 'error') {
  ui.message = { text, type }
}

async function saveSettings() {
  ui.saving = true
  try {
    const res = await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
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
      }),
    })
    const data = await res.json()
    if (data.success) {
      setMessage('設定已保存', 'success')
      ui.lastSaved = new Date().toLocaleString('zh-HK')
      form.smtp.password = ''
    } else {
      setMessage(data.message || '保存失敗', 'error')
    }
  } catch {
    setMessage('保存設定時出錯', 'error')
  } finally {
    ui.saving = false
  }
}

async function sendTestEmail() {
  if (!ui.testAddress) return
  ui.testLoading = true
  try {
    const res = await fetch('/api/settings/test-email', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ recipient: ui.testAddress }),
    })
    const data = await res.json()
    if (data.success) {
      setMessage(data.message || '測試郵件已發送', 'success')
      ui.testAddress = ''
    } else {
      setMessage(data.message || '發送失敗', 'error')
    }
  } catch {
    setMessage('發送測試郵件時出錯', 'error')
  } finally {
    ui.testLoading = false
  }
}
</script>

<template>
  <AppLayout>
    <div class="mb-8">
      <h2 class="text-3xl font-extrabold tracking-tight text-base-content">設定</h2>

      <p class="mt-2 text-sm font-medium text-base-content/65">管理您的應用程式設定</p>
    </div>

    <div
      v-if="ui.message"
      class="mb-6 alert rounded-lg border px-4 py-3"
      :class="ui.message.type === 'success' ? 'alert-success' : 'alert-error'"
    >
      <span>{{ ui.message.text }}</span>
    </div>

    <div class="space-y-6">
      <div class="tracker-panel card rounded-lg">
        <div class="card-body p-0">
          <div class="border-b border-base-300/70 px-6 py-5">
            <h3 class="text-base font-bold text-base-content">SMTP 伺服器</h3>

            <p class="mt-0.5 text-sm font-medium text-base-content/60">設定寄件伺服器連線資訊</p>
          </div>

          <form class="space-y-5 p-6" @submit.prevent="saveSettings">
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

                <option value="SMTP_SSL">SMTP_SSL</option>
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

            <p class="mt-0.5 text-sm font-medium text-base-content/60">接收價格警報的郵件地址</p>
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
              @click.prevent="saveSettings"
            >
              <span v-if="ui.saving" class="loading loading-sm loading-spinner"></span>
              {{ ui.saving ? '保存中...' : '保存收件者' }}
            </button>
          </form>
        </div>
      </div>
    </div>
  </AppLayout>
</template>
