<script setup lang="ts">
import StateBlock from "../components/StateBlock.vue";
import { loadDigests } from "../api/client";
import { useAsyncData } from "../composables/useAsyncData";

const { data, error, loading } = useAsyncData(loadDigests);
</script>

<template>
  <section>
    <h2>Daily Digest</h2>
    <p class="notice">Synthetic demo data only. This is not investment advice.</p>
    <StateBlock :loading="loading" :error="error" :empty="(data ?? []).length === 0">
      <article v-for="digest in data ?? []" :key="digest.digest_date" class="card">
        <h3>{{ digest.digest_date }} · {{ digest.timezone }}</h3>
        <p>{{ digest.article_count }} articles across {{ digest.company_count }} companies</p>
        <p v-for="(count, event) in digest.event_counts" :key="event">{{ event }}: {{ count }}</p>
      </article>
    </StateBlock>
  </section>
</template>
