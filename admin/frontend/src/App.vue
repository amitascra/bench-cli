<script setup>
import { ref, onMounted } from 'vue'
import AppLayout from './components/AppLayout.vue'
import { Alert } from 'frappe-ui'

const adminEnabled = ref(true)
const adminError = ref('')

onMounted(async () => {
  try {
    const res = await fetch('/api/status')
    const data = await res.json()
    adminEnabled.value = data.enabled !== false
    if (!adminEnabled.value) {
      adminError.value = data.error || 'Admin is disabled in bench.toml'
    }
  } catch (e) {
    adminError.value = 'Could not reach the bench admin server.'
  }
})
</script>

<template>
  <div v-if="adminError" class="flex h-screen items-center justify-center p-8">
    <Alert theme="red" title="Admin Unavailable" :description="adminError" />
  </div>
  <AppLayout v-else />
</template>
