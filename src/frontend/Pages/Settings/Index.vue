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
      <h2 class="text-3xl font-extrabold tracking-tight text-gray-900">設定</h2>

      <p class="mt-2 text-sm font-medium text-gray-500">管理您的應用程式設定</p>
    </div>

    <div
      v-if="ui.message"
      class="mb-6 rounded-xl border px-4 py-3"
      :class="
        ui.message.type === 'success' ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'
      "
    >
      <p
        :class="
          ui.message.type === 'success'
            ? 'text-sm font-medium text-green-700'
            : 'text-sm font-medium text-red-700'
        "
      >
        {{ ui.message.text }}
      </p>
    </div>

    <div class="space-y-6">
      <!-- SMTP Configuration Section -->
      <div class="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
        <div class="border-b border-gray-100 bg-gray-50/50 px-6 py-4">
          <h3 class="text-base font-bold text-gray-900">SMTP 伺服器</h3>

          <p class="mt-0.5 text-sm font-medium text-gray-500">設定寄件伺服器連線資訊</p>
        </div>

        <form class="space-y-5 p-6" @submit.prevent="saveSettings">
          <div class="grid grid-cols-3 gap-4">
            <div class="col-span-2">
              <label class="mb-2 block text-sm font-bold tracking-wide text-gray-700">主機</label>

              <input
                v-model="form.smtp.host"
                type="text"
                placeholder="mail.example.com"
                class="w-full rounded-xl border border-gray-300 bg-gray-50/50 px-4 py-3 font-medium text-gray-900 transition-all placeholder:font-normal focus:border-blue-500 focus:bg-white focus:ring-4 focus:ring-blue-500/10 focus:outline-none"
              />
            </div>

            <div>
              <label class="mb-2 block text-sm font-bold tracking-wide text-gray-700">連接埠</label>

              <input
                v-model.number="form.smtp.port"
                type="number"
                placeholder="587"
                class="w-full rounded-xl border border-gray-300 bg-gray-50/50 px-4 py-3 font-medium text-gray-900 transition-all placeholder:font-normal focus:border-blue-500 focus:bg-white focus:ring-4 focus:ring-blue-500/10 focus:outline-none"
              />
            </div>
          </div>

          <div>
            <label class="mb-2 block text-sm font-bold tracking-wide text-gray-700">
              發件人地址
              <span class="ml-1 font-normal text-gray-400">（選填）</span>
            </label>

            <input
              v-model="form.smtp.sender_email"
              type="email"
              placeholder="noreply@example.com"
              class="w-full rounded-xl border border-gray-300 bg-gray-50/50 px-4 py-3 font-medium text-gray-900 transition-all placeholder:font-normal focus:border-blue-500 focus:bg-white focus:ring-4 focus:ring-blue-500/10 focus:outline-none"
            />

            <p class="mt-1.5 text-xs font-medium text-gray-400">留空則使用登入用戶名作為發件人</p>
          </div>

          <div>
            <label class="mb-2 block text-sm font-bold tracking-wide text-gray-700"
              >SMTP 協議</label
            >

            <select
              v-model="form.smtp.protocol"
              class="w-full rounded-xl border border-gray-300 bg-gray-50/50 px-4 py-3 font-medium text-gray-900 transition-all focus:border-blue-500 focus:bg-white focus:ring-4 focus:ring-blue-500/10 focus:outline-none"
            >
              <option value="STARTTLS">STARTTLS</option>

              <option value="SMTP_SSL">SMTP_SSL</option>
            </select>
          </div>

          <label
            class="flex cursor-pointer items-center gap-3 rounded-xl border border-gray-200 bg-gray-50/50 px-4 py-3 transition-colors hover:border-blue-200 hover:bg-blue-50/30"
          >
            <div class="relative shrink-0">
              <input v-model="form.smtp.require_auth" type="checkbox" class="peer sr-only" />

              <div
                class="h-5 w-9 rounded-full bg-gray-300 transition-colors peer-checked:bg-blue-600"
              ></div>

              <div
                class="absolute top-0.5 left-0.5 h-4 w-4 rounded-full bg-white shadow transition-all peer-checked:translate-x-4"
              ></div>
            </div>

            <div>
              <p class="text-sm font-bold text-gray-700">需要 SMTP 驗證</p>

              <p class="text-xs font-medium text-gray-400">停用後可使用無需登入的開放中繼伺服器</p>
            </div>
          </label>

          <div
            :class="[
              'space-y-5 rounded-xl border border-gray-300 p-4 transition-all',
              form.smtp.require_auth
                ? 'bg-gray-50/50 opacity-100'
                : 'pointer-events-none bg-gray-100/50 opacity-60',
            ]"
          >
            <div>
              <label class="mb-2 block text-sm font-bold tracking-wide text-gray-700"
                >使用者名稱</label
              >

              <input
                v-model="form.smtp.user"
                type="email"
                placeholder="user@example.com"
                :disabled="!form.smtp.require_auth"
                class="w-full rounded-xl border border-gray-300 bg-gray-50/50 px-4 py-3 font-medium text-gray-900 transition-all placeholder:font-normal focus:border-blue-500 focus:bg-white focus:ring-4 focus:ring-blue-500/10 focus:outline-none disabled:bg-gray-100 disabled:text-gray-500"
              />
            </div>

            <div>
              <label class="mb-2 block text-sm font-bold tracking-wide text-gray-700">密碼</label>

              <input
                v-model="form.smtp.password"
                type="password"
                :placeholder="props.settings.smtp?.password ? '不更改請留空' : '輸入密碼'"
                :disabled="!form.smtp.require_auth"
                class="w-full rounded-xl border border-gray-300 bg-gray-50/50 px-4 py-3 font-medium text-gray-900 transition-all placeholder:font-normal focus:border-blue-500 focus:bg-white focus:ring-4 focus:ring-blue-500/10 focus:outline-none disabled:bg-gray-100 disabled:text-gray-500"
              />
            </div>
          </div>

          <div class="flex items-center gap-3 border-t border-gray-100 pt-4">
            <button
              type="submit"
              :disabled="ui.saving"
              class="rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition-all hover:bg-blue-500 hover:shadow-md disabled:opacity-50"
            >
              {{ ui.saving ? '保存中...' : '保存設定' }}
            </button>

            <p v-if="ui.lastSaved" class="text-xs font-medium text-green-600">
              ✓ 最後保存於 {{ ui.lastSaved }}
            </p>
          </div>
        </form>
      </div>

      <!-- Test Email Section -->
      <div class="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
        <div class="border-b border-gray-100 bg-gray-50/50 px-6 py-4">
          <h3 class="text-base font-bold text-gray-900">測試郵件</h3>

          <p class="mt-0.5 text-sm font-medium text-gray-500">驗證 SMTP 設定是否正確</p>
        </div>

        <div class="p-6">
          <div
            v-if="!$props.settings.smtp?.host || !$props.settings.smtp?.port"
            class="rounded-xl bg-amber-50 px-4 py-3"
          >
            <p class="text-sm font-semibold text-amber-700">⚠ 請先完成 SMTP 伺服器設定</p>
          </div>

          <div v-else class="space-y-4">
            <div>
              <label class="mb-2 block text-sm font-bold tracking-wide text-gray-700"
                >收件地址</label
              >

              <input
                v-model="ui.testAddress"
                type="email"
                placeholder="test@example.com"
                class="w-full rounded-xl border border-gray-300 bg-gray-50/50 px-4 py-3 font-medium text-gray-900 transition-all placeholder:font-normal focus:border-blue-500 focus:bg-white focus:ring-4 focus:ring-blue-500/10 focus:outline-none"
              />
            </div>

            <button
              :disabled="!ui.testAddress || ui.testLoading"
              class="w-full rounded-xl bg-gray-900 py-2.5 text-sm font-semibold text-white shadow-sm transition-all hover:bg-gray-800 hover:shadow disabled:opacity-50"
              @click="sendTestEmail"
            >
              {{ ui.testLoading ? '發送中...' : '發送測試郵件' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Email Recipients Section -->
      <div class="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
        <div class="border-b border-gray-100 bg-gray-50/50 px-6 py-4">
          <h3 class="text-base font-bold text-gray-900">通知收件者</h3>

          <p class="mt-0.5 text-sm font-medium text-gray-500">接收價格警報的郵件地址</p>
        </div>

        <form class="space-y-4 p-6">
          <div>
            <label class="mb-2 block text-sm font-bold tracking-wide text-gray-700">郵件地址</label>

            <textarea
              v-model="form.email.recipients"
              placeholder="user@example.com&#10;admin@example.com"
              rows="4"
              class="w-full rounded-xl border border-gray-300 bg-gray-50/50 px-4 py-3 font-medium text-gray-900 transition-all placeholder:font-normal focus:border-blue-500 focus:bg-white focus:ring-4 focus:ring-blue-500/10 focus:outline-none"
            ></textarea>

            <p class="mt-1.5 text-xs font-medium text-gray-400">每行一個郵件地址</p>
          </div>

          <button
            type="submit"
            :disabled="ui.saving"
            class="w-full rounded-xl bg-blue-600 py-2.5 text-sm font-semibold text-white transition-all hover:bg-blue-500 disabled:opacity-50"
            @click.prevent="saveSettings"
          >
            {{ ui.saving ? '保存中...' : '保存收件者' }}
          </button>
        </form>
      </div>
    </div>
  </AppLayout>
</template>
