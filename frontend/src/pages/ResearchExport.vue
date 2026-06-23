<script setup lang="ts">
import { computed, ref } from "vue";

import {
  getDataMode,
  loadResearchCalendars,
  loadResearchExports,
  loadResearchFeatureCatalog,
  loadResearchFeatureSample,
  loadResearchLineageSample,
  loadResearchOverview,
} from "../api/client";
import StateBlock from "../components/StateBlock.vue";
import { useAsyncData } from "../composables/useAsyncData";

const overview = useAsyncData(loadResearchOverview);
const calendars = useAsyncData(loadResearchCalendars);
const exports = useAsyncData(loadResearchExports);
const catalog = useAsyncData(loadResearchFeatureCatalog);
const features = useAsyncData(loadResearchFeatureSample);
const lineage = useAsyncData(loadResearchLineageSample);
const tickerFilter = ref("");
const windowFilter = ref("all");

const loading = computed(
  () =>
    overview.loading.value ||
    calendars.loading.value ||
    exports.loading.value ||
    catalog.loading.value ||
    features.loading.value ||
    lineage.loading.value,
);
const error = computed(
  () =>
    overview.error.value ||
    calendars.error.value ||
    exports.error.value ||
    catalog.error.value ||
    features.error.value ||
    lineage.error.value,
);
const filteredRows = computed(() =>
  (features.data.value ?? []).filter((row) => {
    const tickerMatch =
      !tickerFilter.value || row.ticker.includes(tickerFilter.value.toUpperCase());
    const windowMatch =
      windowFilter.value === "all" || row.window_sessions === Number(windowFilter.value);
    return tickerMatch && windowMatch;
  }),
);

function shortHash(value: string | undefined): string {
  return value ? value.slice(0, 12) : "";
}
</script>

<template>
  <section class="page">
    <div class="section-heading">
      <p class="eyebrow">Synthetic research export / no prices or returns</p>
      <h2>Research Export</h2>
      <p class="muted">
        Static/API mode: {{ getDataMode() }}. The package is point-in-time news-factor metadata for
        a future A-share research consumer.
      </p>
    </div>

    <StateBlock :loading="loading" :error="error" :empty="!overview.data.value" />

    <div v-if="overview.data.value && !loading && !error" class="stack">
      <section class="panel">
        <h3>Contract</h3>
        <div class="metric-grid">
          <div>
            <span class="label">Contract</span>
            <strong>{{ overview.data.value.contract_version }}</strong>
          </div>
          <div>
            <span class="label">Sessions</span>
            <strong>{{ overview.data.value.counts.session_count }}</strong>
          </div>
          <div>
            <span class="label">Companies</span>
            <strong>{{ overview.data.value.counts.company_count }}</strong>
          </div>
          <div>
            <span class="label">Rows</span>
            <strong>{{ overview.data.value.counts.feature_row_count }}</strong>
          </div>
        </div>
        <p class="muted">
          {{ overview.data.value.contract_name }} uses {{ overview.data.value.cutoff_policy }} and
          windows {{ overview.data.value.windows.join(", ") }} sessions.
        </p>
      </section>

      <section class="panel">
        <h3>Calendar And Hashes</h3>
        <div v-for="calendar in calendars.data.value ?? []" :key="calendar.calendar_hash">
          <strong>{{ calendar.calendar_id }} / {{ calendar.calendar_version }}</strong>
          <p class="muted">
            {{ calendar.timezone }}, {{ calendar.session_count }} sessions, synthetic calendar only,
            hash {{ shortHash(calendar.calendar_hash) }}.
          </p>
        </div>
        <p class="muted">
          Package hash {{ shortHash(overview.data.value.package_content_hash) }}. No official
          SSE/SZSE calendar, market prices, forward returns, or investment advice are included.
        </p>
      </section>

      <section class="panel">
        <h3>Point-In-Time Timeline</h3>
        <div class="timeline" aria-label="Point-in-time alignment">
          <span>published</span>
          <span>first seen</span>
          <span>available</span>
          <span>cutoff</span>
          <span>session</span>
        </div>
        <p class="muted">
          Availability is max(source published, first seen). Information after a cutoff moves to the
          next eligible session; rolling windows count sessions.
        </p>
      </section>

      <section class="panel">
        <h3>Quality And Leakage</h3>
        <div class="metric-grid">
          <div>
            <span class="label">Rows With News</span>
            <strong>{{ overview.data.value.counts.rows_with_news }}</strong>
          </div>
          <div>
            <span class="label">Rows Without News</span>
            <strong>{{ overview.data.value.counts.rows_without_news }}</strong>
          </div>
          <div>
            <span class="label">Lineage</span>
            <strong>{{ overview.data.value.counts.lineage_row_count }}</strong>
          </div>
          <div>
            <span class="label">Leakage</span>
            <strong>{{ exports.data.value?.[0]?.leakage_status }}</strong>
          </div>
        </div>
      </section>

      <section class="panel">
        <h3>Feature Catalog</h3>
        <p class="muted">{{ catalog.data.value?.null_policy }}</p>
        <div class="chip-row">
          <span
            v-for="feature in (catalog.data.value?.features ?? []).slice(0, 24)"
            :key="String(feature.name)"
            class="chip"
          >
            {{ feature.name }}
          </span>
        </div>
      </section>

      <section class="panel">
        <h3>Sample Dense Rows</h3>
        <div class="filters">
          <label>
            Ticker
            <input v-model="tickerFilter" type="search" placeholder="ALP" />
          </label>
          <label>
            Window
            <select v-model="windowFilter">
              <option value="all">All</option>
              <option value="1">1</option>
              <option value="3">3</option>
              <option value="5">5</option>
              <option value="10">10</option>
            </select>
          </label>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Session</th>
                <th>Ticker</th>
                <th>Window</th>
                <th>News</th>
                <th>Sentiment</th>
                <th>Cutoff</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in filteredRows.slice(0, 20)" :key="row.lineage_row_id">
                <td>{{ row.session_date }}</td>
                <td>{{ row.ticker }}</td>
                <td>{{ row.window_sessions }}</td>
                <td>{{ row.news_count }}</td>
                <td>{{ row.mean_sentiment_score ?? "null" }}</td>
                <td>{{ row.decision_cutoff_at }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="panel">
        <h3>Safe Lineage Sample</h3>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Lineage</th>
                <th>Article ID</th>
                <th>Source</th>
                <th>Available</th>
                <th>Cutoff</th>
                <th>Labels</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in (lineage.data.value ?? []).slice(0, 20)" :key="row.lineage_row_id">
                <td>{{ shortHash(row.lineage_row_id) }}</td>
                <td>{{ shortHash(row.canonical_article_id ?? "") }}</td>
                <td>{{ row.source_id }}</td>
                <td>{{ row.information_available_at }}</td>
                <td>{{ row.decision_cutoff_at }}</td>
                <td>{{ row.event_label }} / {{ row.sentiment_label }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="panel">
        <h3>Handoff Boundary</h3>
        <p class="muted">
          The future ashare-research-platform consumes package files, verifies hashes, maps company
          identifiers, and joins its own market data. FinNews does not calculate returns, backtests,
          portfolio weights, or recommendations.
        </p>
      </section>
    </div>
  </section>
</template>
