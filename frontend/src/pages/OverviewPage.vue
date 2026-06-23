<script setup lang="ts">
import StateBlock from "../components/StateBlock.vue";
import { loadCrossAssetOverview, loadOverview } from "../api/client";
import { useAsyncData } from "../composables/useAsyncData";

const { data, error, loading } = useAsyncData(loadOverview);
const crossAsset = useAsyncData(loadCrossAssetOverview);
</script>

<template>
  <section>
    <h2>Overview</h2>
    <StateBlock
      :loading="loading || crossAsset.loading.value"
      :error="error || crossAsset.error.value"
      :empty="!data"
    >
      <div v-if="data" class="grid">
        <article v-if="crossAsset.data.value" class="card">
          <h3>Cross-Asset Assets</h3>
          <p class="metric">{{ crossAsset.data.value.asset_count }}</p>
        </article>
        <article v-if="crossAsset.data.value" class="card">
          <h3>Signal Candidates</h3>
          <p class="metric">{{ crossAsset.data.value.signal_candidate_count }}</p>
        </article>
        <article class="card">
          <h3>Canonical Articles</h3>
          <p class="metric">{{ data.canonical_article_count }}</p>
        </article>
        <article class="card">
          <h3>Companies</h3>
          <p class="metric">{{ data.company_count }}</p>
        </article>
        <article class="card">
          <h3>Raw Observations</h3>
          <p class="metric">{{ data.deduplication.raw_observation_count }}</p>
        </article>
        <article class="card">
          <h3>Duplicate Observations</h3>
          <p>
            exact {{ data.deduplication.exact_duplicate_observation_count }} / near
            {{ data.deduplication.near_duplicate_observation_count }}
          </p>
          <p>clusters {{ data.deduplication.duplicate_cluster_count }}</p>
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
