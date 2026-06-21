<script setup lang="ts">
import StateBlock from "../components/StateBlock.vue";
import { loadOverview } from "../api/client";
import { useAsyncData } from "../composables/useAsyncData";

const { data, error, loading } = useAsyncData(loadOverview);
</script>

<template>
  <section>
    <h2>Overview</h2>
    <StateBlock :loading="loading" :error="error" :empty="!data">
      <div v-if="data" class="grid">
        <article class="card">
          <h3>Articles</h3>
          <p class="metric">{{ data.article_count }}</p>
        </article>
        <article class="card">
          <h3>Companies</h3>
          <p class="metric">{{ data.company_count }}</p>
        </article>
        <article class="card">
          <h3>Events</h3>
          <p v-for="(count, name) in data.event_distribution" :key="name">
            {{ name }}: {{ count }}
          </p>
        </article>
        <article class="card">
          <h3>Sentiment</h3>
          <p v-for="(count, name) in data.sentiment_distribution" :key="name">
            {{ name }}: {{ count }}
          </p>
        </article>
      </div>
    </StateBlock>
  </section>
</template>
