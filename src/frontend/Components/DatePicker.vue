<script setup lang="ts">
import { Icon } from '@iconify/vue'
import type { RootProps } from '@vuepic/vue-datepicker'
import { VueDatePicker } from '@vuepic/vue-datepicker'
import '@vuepic/vue-datepicker/dist/main.css'
import { zhHK } from 'date-fns/locale'

defineOptions({ inheritAttrs: false })

const props = withDefaults(
  defineProps<{
    placeholder?: string
    clearable?: boolean
    clearLabel?: string
    options?: Omit<
      RootProps,
      'autoApply' | 'enableTimePicker' | 'locale' | 'modelType' | 'teleport' | 'modelValue'
    >
  }>(),
  { placeholder: '選擇日期', clearable: true, clearLabel: '清除', options: () => ({}) },
)

const model = defineModel<string | string[]>({ required: true })
</script>

<template>
  <div class="relative">
    <VueDatePicker
      v-model="model"
      v-bind="{
        enableTimePicker: false,
        locale: zhHK,
        autoApply: true,
        modelType: 'yyyy-MM-dd',
        teleport: 'body',
        ...props.options,
      }"
    >
      <template #trigger>
        <input
          type="text"
          :value="
            !Array.isArray(model) ? model : model.length === 2 ? `${model[0]} 至 ${model[1]}` : ''
          "
          :placeholder="props.placeholder"
          class="input-bordered input w-full cursor-pointer transition-colors focus:input-primary"
          readonly
          v-bind="$attrs"
        />
      </template>
    </VueDatePicker>

    <button
      v-if="props.clearable"
      type="button"
      :title="props.clearLabel"
      :aria-label="props.clearLabel"
      class="btn absolute top-1/2 right-1.5 -translate-y-1/2 text-base-content/40 btn-ghost btn-xs hover:text-base-content/60"
      :disabled="Array.isArray(model) ? model.length === 0 : !model || Boolean($attrs.disabled)"
      @click="model = Array.isArray(model) ? [] : ''"
    >
      <Icon icon="mdi:close" />
    </button>
  </div>
</template>
