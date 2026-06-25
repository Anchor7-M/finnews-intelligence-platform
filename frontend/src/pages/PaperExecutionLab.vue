<script setup lang="ts">
import { computed, ref } from "vue";

import {
  getDataMode,
  loadPaperFills,
  loadPaperNav,
  loadPaperOrders,
  loadPaperOverview,
  loadPaperPositions,
  loadPaperRiskDecisions,
  loadPaperRiskPolicies,
  loadPaperRuns,
} from "../api/client";
import StateBlock from "../components/StateBlock.vue";
import { useAsyncData } from "../composables/useAsyncData";

const mode = getDataMode();
const selectedScenario = ref("paper-planted-reaction-v1");

const overview = useAsyncData(loadPaperOverview);
const policies = useAsyncData(loadPaperRiskPolicies);
const decisions = useAsyncData(loadPaperRiskDecisions);
const orders = useAsyncData(loadPaperOrders);
const fills = useAsyncData(loadPaperFills);
const positions = useAsyncData(loadPaperPositions);
const navRows = useAsyncData(loadPaperNav);
const runs = useAsyncData(loadPaperRuns);

const scenarioOptions = computed(() => overview.data.value?.scenario_ids ?? []);
const activePolicy = computed(() => (policies.data.value ?? [])[0] ?? null);
const scenarioRun = computed(() =>
  (runs.data.value ?? []).find((row) => row.scenario_id === selectedScenario.value),
);
const scenarioDecisions = computed(() =>
  (decisions.data.value ?? []).filter((row) => row.scenario_id === selectedScenario.value),
);
const scenarioOrders = computed(() =>
  (orders.data.value ?? []).filter((row) =>
    row.paper_order_id.startsWith(`paper-order|${selectedScenario.value}|`),
  ),
);
const scenarioFills = computed(() =>
  (fills.data.value ?? []).filter((row) => row.scenario_id === selectedScenario.value),
);
const scenarioPositions = computed(() =>
  (positions.data.value ?? []).filter((row) => row.scenario_id === selectedScenario.value),
);
const scenarioNav = computed(() =>
  (navRows.data.value ?? []).filter((row) => row.scenario_id === selectedScenario.value),
);
</script>

<template>
  <section class="page-stack">
    <div class="section-heading">
      <p class="eyebrow">Paper-only simulation / synthetic data / not investment advice</p>
      <h2>Paper Execution Lab</h2>
      <p>
        {{ mode === "api" ? "FastAPI profile" : "Static demo profile" }}. Risk gates, manual-review
        simulation, paper fills, and portfolio accounting use deterministic local data and are not
        connected to MT5 or any real account.
      </p>
    </div>

    <StateBlock
      :loading="overview.loading.value"
      :error="overview.error.value"
      :empty="!overview.data.value"
    />

    <section v-if="overview.data.value" class="notice">
      {{ overview.data.value.disclaimer }}
    </section>

    <div v-if="overview.data.value" class="metric-grid">
      <article>
        <span>Signals Considered</span>
        <strong>{{ overview.data.value.signal_candidates_considered }}</strong>
      </article>
      <article>
        <span>Paper Orders</span>
        <strong>{{ overview.data.value.paper_order_count }}</strong>
      </article>
      <article>
        <span>Paper Fills</span>
        <strong>{{ overview.data.value.filled_count }}</strong>
      </article>
      <article>
        <span>Failed Fills</span>
        <strong>{{ overview.data.value.failed_fill_count }}</strong>
      </article>
      <article>
        <span>Positions</span>
        <strong>{{ overview.data.value.position_count }}</strong>
      </article>
      <article>
        <span>Average NAV</span>
        <strong>{{ overview.data.value.average_final_nav }}</strong>
      </article>
    </div>

    <div class="filters">
      <label class="filter-label">
        Scenario
        <select v-model="selectedScenario">
          <option v-for="scenario in scenarioOptions" :key="scenario" :value="scenario">
            {{ scenario }}
          </option>
        </select>
      </label>
    </div>

    <div class="two-column">
      <section class="panel">
        <h3>Risk Policy</h3>
        <StateBlock
          :loading="policies.loading.value"
          :error="policies.error.value"
          :empty="!(policies.data.value ?? []).length"
        />
        <div v-if="activePolicy" class="detail-list">
          <div>
            <span>Policy</span><strong>{{ activePolicy.risk_policy_id }}</strong>
          </div>
          <div>
            <span>Confidence</span><strong>{{ activePolicy.confidence_threshold }}</strong>
          </div>
          <div>
            <span>Default Notional</span><strong>{{ activePolicy.default_order_notional }}</strong>
          </div>
          <div>
            <span>Manual Review</span><strong>{{ activePolicy.manual_approval_required }}</strong>
          </div>
          <div>
            <span>Kill Switch</span><strong>{{ activePolicy.kill_switch_active }}</strong>
          </div>
        </div>
      </section>

      <section class="panel">
        <h3>Scenario Summary</h3>
        <StateBlock :loading="runs.loading.value" :error="runs.error.value" :empty="!scenarioRun" />
        <div v-if="scenarioRun" class="metric-grid compact">
          <article>
            <span>Approved</span><strong>{{ scenarioRun.risk_approved }}</strong>
          </article>
          <article>
            <span>Manual Review</span><strong>{{ scenarioRun.manual_review }}</strong>
          </article>
          <article>
            <span>Rejected</span><strong>{{ scenarioRun.rejected }}</strong>
          </article>
          <article>
            <span>Expired</span><strong>{{ scenarioRun.expired }}</strong>
          </article>
          <article>
            <span>Turnover</span><strong>{{ scenarioRun.turnover }}</strong>
          </article>
          <article>
            <span>Costs</span><strong>{{ scenarioRun.costs }}</strong>
          </article>
        </div>
      </section>
    </div>

    <section class="panel">
      <h3>Risk Decisions</h3>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Signal</th>
              <th>Asset</th>
              <th>Decision</th>
              <th>Reasons</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in scenarioDecisions.slice(0, 12)" :key="row.risk_decision_id">
              <td>{{ row.signal_id }}</td>
              <td>{{ row.asset_id }}</td>
              <td>{{ row.risk_decision }}</td>
              <td>{{ row.reason_codes.join(", ") }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <div class="two-column">
      <section class="panel">
        <h3>Paper Orders And Fills</h3>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Paper Order</th>
                <th>Side</th>
                <th>Notional</th>
                <th>Fill Status</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="order in scenarioOrders" :key="order.paper_order_id">
                <td>{{ order.signal_id }}</td>
                <td>{{ order.paper_side }}</td>
                <td>{{ order.paper_notional }}</td>
                <td>
                  {{
                    scenarioFills.find((fill) => fill.paper_order_id === order.paper_order_id)
                      ?.fill_status ?? "not simulated"
                  }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="panel">
        <h3>Portfolio</h3>
        <div class="detail-list">
          <div v-for="row in scenarioNav" :key="row.scenario_id">
            <span>NAV</span><strong>{{ row.nav }}</strong>
          </div>
          <div v-for="row in scenarioNav" :key="`${row.scenario_id}-dd`">
            <span>Max Drawdown</span><strong>{{ row.maximum_drawdown }}</strong>
          </div>
          <div v-for="row in scenarioNav" :key="`${row.scenario_id}-rec`">
            <span>Reconciliation</span><strong>{{ row.reconciliation_status }}</strong>
          </div>
        </div>
        <ul class="plain-list">
          <li v-for="position in scenarioPositions" :key="position.asset_id">
            {{ position.asset_id }}: {{ position.quantity }} units, value
            {{ position.market_value }}
          </li>
        </ul>
      </section>
    </div>
  </section>
</template>
