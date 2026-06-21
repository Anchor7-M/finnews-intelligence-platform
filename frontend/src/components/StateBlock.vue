<script setup lang="ts">
defineProps<{
  loading?: boolean;
  error?: string | null;
  empty?: boolean;
}>();
</script>

<template>
  <p v-if="loading" class="notice" role="status">Loading data.</p>
  <p v-else-if="error" class="notice" role="alert">Unable to load data: {{ error }}</p>
  <p v-else-if="empty" class="notice">No matching synthetic records.</p>
  <slot v-else />
</template>
