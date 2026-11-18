<script setup lang="ts">
import { usePage } from '@inertiajs/vue3'
import { computed } from 'vue'

const props = defineProps<{ field: string }>()

const message = computed(() => {
  const value = usePage().props.errors?.[props.field]
  return Array.isArray(value) ? value[0] : value
})
</script>

<template>
  <p v-if="message" class="text-xs text-error">{{ message }}</p>
</template>
