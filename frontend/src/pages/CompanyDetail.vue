<script setup lang="ts">
import { computed, ref, watchEffect } from "vue";
import { useRoute } from "vue-router";

import StateBlock from "../components/StateBlock.vue";
import { loadArticles, loadCompanies, loadSignals } from "../api/client";
import { useAsyncData } from "../composables/useAsyncData";

const route = useRoute();
const selectedTicker = ref("");
const companies = useAsyncData(loadCompanies);
const articles = useAsyncData(loadArticles);
const signals = useAsyncData(loadSignals);

watchEffect(() => {
  const routeTicker = typeof route.params.ticker === "string" ? route.params.ticker : "";
  selectedTicker.value =
    routeTicker || selectedTicker.value || companies.data.value?.[0]?.ticker || "";
});

const company = computed(() =>
  (companies.data.value ?? []).find((item) => item.ticker === selectedTicker.value),
);
const relatedArticles = computed(() =>
  (articles.data.value ?? []).filter((article) => article.tickers.includes(selectedTicker.value)),
);
const relatedSignals = computed(() =>
  (signals.data.value ?? []).filter((signal) => signal.ticker === selectedTicker.value),
);
</script>

<template>
  <section>
    <h2>Company Detail</h2>
    <StateBlock :loading="companies.loading.value" :error="companies.error.value" :empty="!company">
      <label>
        Company
        <select v-model="selectedTicker">
          <option
            v-for="item in companies.data.value ?? []"
            :key="item.ticker"
            :value="item.ticker"
          >
            {{ item.ticker }} · {{ item.short_name }}
          </option>
        </select>
      </label>
      <article v-if="company" class="card">
        <h3>{{ company.short_name }} ({{ company.ticker }})</h3>
        <p>{{ company.legal_name }}</p>
        <p class="meta">{{ company.exchange }} · {{ company.sector }}</p>
      </article>
      <div class="grid">
        <article class="card">
          <h3>Timeline</h3>
          <p v-for="article in relatedArticles" :key="article.id">
            {{ article.market_date }} · {{ article.title }}
          </p>
        </article>
        <article class="card">
          <h3>Signals</h3>
          <p v-for="signal in relatedSignals" :key="`${signal.signal_date}-${signal.ticker}`">
            {{ signal.signal_date }} · sentiment {{ signal.weighted_sentiment_score }} · novelty
            {{ signal.novelty_score }}
          </p>
        </article>
      </div>
    </StateBlock>
  </section>
</template>
