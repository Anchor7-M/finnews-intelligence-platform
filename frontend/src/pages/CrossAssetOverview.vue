<script setup lang="ts">
import StateBlock from "../components/StateBlock.vue";
import { getDataMode, loadCrossAssetOverview } from "../api/client";
import { useAsyncData } from "../composables/useAsyncData";

const { data, error, loading } = useAsyncData(loadCrossAssetOverview);
</script>

<template>
  <section class="page-stack">
    <div class="section-heading">
      <p class="eyebrow">Synthetic cross-asset intelligence / no execution</p>
      <h2>Cross-Asset Overview</h2>
      <p class="muted">Mode: {{ getDataMode() }}. Signals are research candidates only.</p>
    </div>

    <StateBlock :loading="loading" :error="error" :empty="!data" />

    <div v-if="data && !loading && !error" class="stack">
      <section class="panel">
        <h3>Scope</h3>
        <p>{{ data.product_positioning }}</p>
        <div class="chip-row">
          <span class="chip">synthetic data</span>
          <span class="chip">not investment advice</span>
          <span class="chip">no live prices</span>
          <span class="chip">execution disabled</span>
        </div>
      </section>

      <section class="metric-grid">
        <div>
          <span class="label">Assets</span>
          <strong>{{ data.asset_count }}</strong>
        </div>
        <div>
          <span class="label">Events</span>
          <strong>{{ data.event_count }}</strong>
        </div>
        <div>
          <span class="label">Impact Hypotheses</span>
          <strong>{{ data.impact_hypothesis_count }}</strong>
        </div>
        <div>
          <span class="label">Signal Candidates</span>
          <strong>{{ data.signal_candidate_count }}</strong>
        </div>
      </section>

      <section class="panel">
        <h3>Asset Classes</h3>
        <div class="bar-list">
          <div v-for="(count, name) in data.asset_class_counts" :key="name">
            <span>{{ name }}</span>
            <strong>{{ count }}</strong>
          </div>
        </div>
      </section>

      <section class="panel">
        <h3>Impact And Signal Coverage</h3>
        <div class="grid">
          <div>
            <h4>Directions</h4>
            <p v-for="(count, name) in data.impact_direction_counts" :key="name">
              {{ name }}: {{ count }}
            </p>
          </div>
          <div>
            <h4>Horizons</h4>
            <p v-for="(count, name) in data.impact_horizon_counts" :key="name">
              {{ name }}: {{ count }}
            </p>
          </div>
          <div>
            <h4>Status</h4>
            <p v-for="(count, name) in data.signal_status_counts" :key="name">
              {{ name }}: {{ count }}
            </p>
          </div>
        </div>
      </section>

      <section class="notice">
        {{ data.contract_name }} {{ data.contract_version }} is a file contract for local research
        handoff. It does not include broker credentials, account data, position sizing, or trade
        routing.
      </section>
    </div>
  </section>
</template>
