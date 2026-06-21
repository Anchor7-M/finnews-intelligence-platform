<script setup lang="ts">
import { computed, ref } from "vue";

import StateBlock from "../components/StateBlock.vue";
import { loadArticles } from "../api/client";
import { useAsyncData } from "../composables/useAsyncData";

const { data, error, loading } = useAsyncData(loadArticles);
const query = ref("");
const ticker = ref("");
const event = ref("");
const sentiment = ref("");
const language = ref("");

const filtered = computed(() => {
  const rows = data.value ?? [];
  return rows.filter((article) => {
    const text = `${article.title} ${article.summary}`.toLowerCase();
    return (
      (!query.value || text.includes(query.value.toLowerCase())) &&
      (!ticker.value || article.tickers.includes(ticker.value)) &&
      (!event.value || article.event === event.value) &&
      (!sentiment.value || article.sentiment === sentiment.value) &&
      (!language.value || article.language === language.value)
    );
  });
});

const tickers = computed(() =>
  Array.from(new Set((data.value ?? []).flatMap((article) => article.tickers))),
);
const events = computed(() =>
  Array.from(new Set((data.value ?? []).map((article) => article.event))),
);
const sentiments = computed(() =>
  Array.from(new Set((data.value ?? []).map((article) => article.sentiment))),
);
</script>

<template>
  <section>
    <h2>Article Explorer</h2>
    <div class="toolbar" aria-label="Article filters">
      <label>Search <input v-model="query" type="search" /></label>
      <label>
        Ticker
        <select v-model="ticker">
          <option value="">All</option>
          <option v-for="item in tickers" :key="item" :value="item">{{ item }}</option>
        </select>
      </label>
      <label>
        Event
        <select v-model="event">
          <option value="">All</option>
          <option v-for="item in events" :key="item" :value="item">{{ item }}</option>
        </select>
      </label>
      <label>
        Sentiment
        <select v-model="sentiment">
          <option value="">All</option>
          <option v-for="item in sentiments" :key="item" :value="item">{{ item }}</option>
        </select>
      </label>
      <label>
        Language
        <select v-model="language">
          <option value="">All</option>
          <option value="en">English</option>
          <option value="zh">中文</option>
        </select>
      </label>
    </div>
    <StateBlock :loading="loading" :error="error" :empty="filtered.length === 0">
      <div class="article-list">
        <article v-for="article in filtered" :key="article.id" class="card">
          <h3>{{ article.title }}</h3>
          <p>{{ article.summary }}</p>
          <p class="meta">
            <span>{{ article.source_name }}</span>
            <span>{{ article.market_date }}</span>
            <span>{{ article.tickers.join(", ") }}</span>
            <span>{{ article.event }}</span>
            <span>{{ article.sentiment }}</span>
          </p>
          <a :href="article.url" rel="noreferrer">Source URL</a>
        </article>
      </div>
    </StateBlock>
  </section>
</template>
