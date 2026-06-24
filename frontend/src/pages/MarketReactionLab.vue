<script setup lang="ts">
import { computed, ref } from "vue";

import {
  getDataMode,
  loadMarketDataBars,
  loadMarketDataPackages,
  loadMarketReactionErrorAnalysis,
  loadMarketReactionLabels,
  loadMarketReactionMetrics,
  loadMarketReactionOverview,
  loadMarketReactionScenarios,
  loadMarketReactionStudies,
} from "../api/client";
import StateBlock from "../components/StateBlock.vue";
import { useAsyncData } from "../composables/useAsyncData";
import type { MarketReactionMetric } from "../types/models";

const mode = getDataMode();
const selectedScenario = ref("synthetic-planted-reaction-v1");
const selectedHorizon = ref("");
const selectedAssetClass = ref("");
const selectedLabel = ref("");

const overview = useAsyncData(loadMarketReactionOverview);
const scenarios = useAsyncData(loadMarketReactionScenarios);
const studies = useAsyncData(loadMarketReactionStudies);
const labels = useAsyncData(loadMarketReactionLabels);
const metrics = useAsyncData(loadMarketReactionMetrics);
const errors = useAsyncData(loadMarketReactionErrorAnalysis);
const packages = useAsyncData(loadMarketDataPackages);
const bars = useAsyncData(loadMarketDataBars);

const horizonOptions = computed(() =>
  Array.from(new Set((labels.data.value ?? []).map((row) => row.horizon))).sort(),
);

const assetClassOptions = computed(() =>
  Array.from(new Set((labels.data.value ?? []).map((row) => row.asset_class))).sort(),
);

const labelOptions = computed(() =>
  Array.from(new Set((labels.data.value ?? []).map((row) => row.label))).sort(),
);

const filteredLabels = computed(() =>
  (labels.data.value ?? []).filter(
    (row) =>
      row.scenario_id === selectedScenario.value &&
      (!selectedHorizon.value || row.horizon === selectedHorizon.value) &&
      (!selectedAssetClass.value || row.asset_class === selectedAssetClass.value) &&
      (!selectedLabel.value || row.label === selectedLabel.value),
  ),
);

const scenarioMetrics = computed(() =>
  (metrics.data.value ?? []).filter((row) => row.scenario_id === selectedScenario.value),
);

const headlineMetric = computed(
  () =>
    scenarioMetrics.value.find(
      (row) => row.slice_type === "horizon" && row.slice_value === "one_week",
    ) ??
    scenarioMetrics.value.find((row) => row.slice_type === "scenario") ??
    null,
);

const sliceMetrics = computed(() =>
  scenarioMetrics.value
    .filter((row) => ["horizon", "asset_class", "regime"].includes(row.slice_type))
    .slice(0, 12),
);

const scenarioErrors = computed(() =>
  (errors.data.value ?? []).filter((row) => row.scenario_id === selectedScenario.value).slice(0, 8),
);

const scenarioBars = computed(() =>
  (bars.data.value ?? []).filter((row) => row.scenario_id === selectedScenario.value).slice(0, 10),
);

const scenarioStudies = computed(() =>
  (studies.data.value ?? [])
    .filter((row) => row.synthetic_scenario_id === selectedScenario.value)
    .slice(0, 8),
);

const scenarioPackage = computed(() =>
  (packages.data.value ?? []).find((row) => row.scenario_id === selectedScenario.value),
);

function formatRate(value: string | null | undefined): string {
  if (!value) {
    return "n/a";
  }
  return `${(Number(value) * 100).toFixed(1)}%`;
}

function metricValue(row: MarketReactionMetric, field: keyof MarketReactionMetric): string {
  const value = row[field];
  return value === null || value === undefined ? "n/a" : String(value);
}
</script>

<template>
  <section class="page-stack">
    <div class="section-heading">
      <p class="eyebrow">Synthetic market-reaction demo / not investment advice</p>
      <h2>Market Reaction Lab</h2>
      <p>
        {{ mode === "api" ? "FastAPI profile" : "Static demo profile" }}. Local synthetic bars
        validate event-study plumbing and point-in-time labels without live market data.
      </p>
    </div>

    <StateBlock
      :loading="overview.loading.value"
      :error="overview.error.value"
      :empty="!overview.data.value"
    />

    <div v-if="overview.data.value" class="metric-grid">
      <article>
        <span>Scenarios</span>
        <strong>{{ overview.data.value.scenario_count }}</strong>
      </article>
      <article>
        <span>Assets / Scenario</span>
        <strong>{{ overview.data.value.asset_count_per_scenario }}</strong>
      </article>
      <article>
        <span>Total Bars</span>
        <strong>{{ overview.data.value.total_bar_count }}</strong>
      </article>
      <article>
        <span>Studies</span>
        <strong>{{ overview.data.value.study_count }}</strong>
      </article>
      <article>
        <span>Labels</span>
        <strong>{{ overview.data.value.label_count }}</strong>
      </article>
      <article>
        <span>Error Cases</span>
        <strong>{{ overview.data.value.error_case_count }}</strong>
      </article>
    </div>

    <section v-if="overview.data.value" class="notice">
      {{ overview.data.value.disclaimer }}
    </section>

    <div class="filters">
      <label class="filter-label">
        Scenario
        <select v-model="selectedScenario">
          <option v-for="scenario in scenarios.data.value ?? []" :key="scenario.scenario_id">
            {{ scenario.scenario_id }}
          </option>
        </select>
      </label>
      <label class="filter-label">
        Horizon
        <select v-model="selectedHorizon">
          <option value="">All horizons</option>
          <option v-for="horizon in horizonOptions" :key="horizon" :value="horizon">
            {{ horizon }}
          </option>
        </select>
      </label>
      <label class="filter-label">
        Asset Class
        <select v-model="selectedAssetClass">
          <option value="">All asset classes</option>
          <option v-for="assetClass in assetClassOptions" :key="assetClass" :value="assetClass">
            {{ assetClass }}
          </option>
        </select>
      </label>
      <label class="filter-label">
        Label
        <select v-model="selectedLabel">
          <option value="">All labels</option>
          <option v-for="label in labelOptions" :key="label" :value="label">
            {{ label }}
          </option>
        </select>
      </label>
    </div>

    <div class="two-column">
      <section class="panel">
        <h3>Scenario Contract</h3>
        <StateBlock
          :loading="scenarios.loading.value || packages.loading.value"
          :error="scenarios.error.value || packages.error.value"
          :empty="!scenarioPackage"
        />
        <div v-if="scenarioPackage" class="metric-grid">
          <article>
            <span>Bar Count</span>
            <strong>{{ scenarioPackage.bar_count }}</strong>
          </article>
          <article>
            <span>Sessions</span>
            <strong>{{ scenarioPackage.session_count }}</strong>
          </article>
          <article>
            <span>First Session</span>
            <strong>{{ scenarioPackage.first_session_date }}</strong>
          </article>
          <article>
            <span>Last Session</span>
            <strong>{{ scenarioPackage.last_session_date }}</strong>
          </article>
        </div>
        <p v-if="scenarioPackage" class="source-note">
          {{ scenarioPackage.contract_name }} {{ scenarioPackage.contract_version }} /
          {{ scenarioPackage.provider }}
        </p>
      </section>

      <section class="panel">
        <h3>Signal Quality Snapshot</h3>
        <StateBlock
          :loading="metrics.loading.value"
          :error="metrics.error.value"
          :empty="!headlineMetric"
        />
        <div v-if="headlineMetric" class="metric-grid">
          <article>
            <span>Consistency</span>
            <strong>{{ formatRate(headlineMetric.directional_consistency_rate) }}</strong>
          </article>
          <article>
            <span>Opposite</span>
            <strong>{{ formatRate(headlineMetric.opposite_rate) }}</strong>
          </article>
          <article>
            <span>Muted</span>
            <strong>{{ formatRate(headlineMetric.muted_rate) }}</strong>
          </article>
          <article>
            <span>Coverage</span>
            <strong>{{ formatRate(headlineMetric.coverage) }}</strong>
          </article>
        </div>
      </section>
    </div>

    <section class="panel">
      <h3>Scenario Metrics</h3>
      <StateBlock
        :loading="metrics.loading.value"
        :error="metrics.error.value"
        :empty="sliceMetrics.length === 0"
      />
      <div v-if="sliceMetrics.length" class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Slice</th>
              <th>Coverage</th>
              <th>Consistency</th>
              <th>Opposite</th>
              <th>Mean Abnormal</th>
              <th>Rank IC</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in sliceMetrics" :key="row.metric_id" tabindex="0">
              <td>{{ row.slice_type }} / {{ row.slice_value }}</td>
              <td>{{ formatRate(row.coverage) }}</td>
              <td>{{ formatRate(row.directional_consistency_rate) }}</td>
              <td>{{ formatRate(row.opposite_rate) }}</td>
              <td>{{ metricValue(row, "mean_abnormal_return") }}</td>
              <td>{{ metricValue(row, "spearman_rank_ic") }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="panel">
      <h3>Reaction Labels</h3>
      <StateBlock
        :loading="labels.loading.value"
        :error="labels.error.value"
        :empty="filteredLabels.length === 0"
      />
      <div v-if="filteredLabels.length" class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Signal</th>
              <th>Asset</th>
              <th>Horizon</th>
              <th>Direction</th>
              <th>Label</th>
              <th>Abnormal</th>
              <th>Regime</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in filteredLabels.slice(0, 14)" :key="row.label_id" tabindex="0">
              <td>{{ row.signal_id }}</td>
              <td>{{ row.asset_id }}</td>
              <td>{{ row.horizon }}</td>
              <td>{{ row.signal_direction }}</td>
              <td>{{ row.label }}</td>
              <td>{{ row.abnormal_return ?? "n/a" }}</td>
              <td>{{ row.market_state }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <div class="two-column">
      <section class="panel">
        <h3>Error Analysis</h3>
        <StateBlock
          :loading="errors.loading.value"
          :error="errors.error.value"
          :empty="scenarioErrors.length === 0"
        />
        <article
          v-for="row in scenarioErrors"
          :key="row.error_case_id"
          class="source-card compact-card"
          tabindex="0"
        >
          <p class="eyebrow">{{ row.error_category }} / {{ row.horizon }}</p>
          <h4>{{ row.synthetic_signal_id }} on {{ row.asset_id }}</h4>
          <p>
            Expected {{ row.expected_direction }}, observed {{ row.observed_label }} in
            {{ row.regime }}.
          </p>
          <p class="source-note">{{ row.overclaim_guardrail }}</p>
        </article>
      </section>

      <section class="panel">
        <h3>Bar Sample</h3>
        <StateBlock
          :loading="bars.loading.value"
          :error="bars.error.value"
          :empty="scenarioBars.length === 0"
        />
        <div v-if="scenarioBars.length" class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Asset</th>
                <th>Session</th>
                <th>Close</th>
                <th>State</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in scenarioBars" :key="row.bar_id">
                <td>{{ row.asset_id }}</td>
                <td>{{ row.session_date }}</td>
                <td>{{ row.close }}</td>
                <td>{{ row.market_state }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>

    <section class="panel">
      <h3>Event-Study Sample</h3>
      <StateBlock
        :loading="studies.loading.value"
        :error="studies.error.value"
        :empty="scenarioStudies.length === 0"
      />
      <div v-if="scenarioStudies.length" class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Study</th>
              <th>Family</th>
              <th>Window</th>
              <th>Coverage</th>
              <th>Benchmark</th>
              <th>Quality</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in scenarioStudies" :key="row.study_id">
              <td>{{ row.signal_id }}</td>
              <td>{{ row.event_family }}</td>
              <td>{{ row.reaction_window }}</td>
              <td>{{ row.bar_coverage }}</td>
              <td>{{ row.benchmark_return ?? "n/a" }}</td>
              <td>{{ row.quality_flags.join(", ") || "clean" }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </section>
</template>
