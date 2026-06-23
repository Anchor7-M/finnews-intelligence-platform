<script setup lang="ts">
import StateBlock from "../components/StateBlock.vue";
import { getDataMode, loadMt5Readiness } from "../api/client";
import { useAsyncData } from "../composables/useAsyncData";

const { data, error, loading } = useAsyncData(loadMt5Readiness);
</script>

<template>
  <section class="page-stack">
    <div class="section-heading">
      <p class="eyebrow">Optional local integration boundary</p>
      <h2>Integration Readiness</h2>
      <p class="muted">
        Mode: {{ getDataMode() }}. This screen is an audit surface, not a connector.
      </p>
    </div>

    <StateBlock :loading="loading" :error="error" :empty="!data" />

    <div v-if="data && !loading && !error" class="stack">
      <section class="metric-grid">
        <div>
          <span class="label">Signal Contract</span>
          <strong>{{ data.signal_contract_status }}</strong>
        </div>
        <div>
          <span class="label">Symbol Map</span>
          <strong>{{ data.symbol_map_schema_status }}</strong>
        </div>
        <div>
          <span class="label">Terminal Adapter</span>
          <strong>{{ data.terminal_adapter_status }}</strong>
        </div>
        <div>
          <span class="label">Execution</span>
          <strong>{{ data.execution_status }}</strong>
        </div>
      </section>

      <section class="panel">
        <h3>Safety Boundary</h3>
        <dl class="definition-list">
          <dt>Terminal connection</dt>
          <dd>{{ data.mt5_terminal_connection }}</dd>
          <dt>Credentials accepted</dt>
          <dd>{{ data.credentials_accepted ? "yes" : "no" }}</dd>
          <dt>Account data access</dt>
          <dd>{{ data.account_data_access ? "yes" : "no" }}</dd>
          <dt>Order routes</dt>
          <dd>{{ data.order_routes ? "enabled" : "disabled" }}</dd>
          <dt>UTC policy</dt>
          <dd>{{ data.utc_policy }}</dd>
        </dl>
      </section>

      <section class="panel">
        <h3>Canonical Mapping Coverage</h3>
        <p>
          {{ data.canonical_mapping_coverage.mapped_assets }} /
          {{ data.canonical_mapping_coverage.total_assets }} assets are mapped in the demo readiness
          state.
        </p>
        <p v-for="note in data.notes" :key="note" class="muted">{{ note }}</p>
      </section>
    </div>
  </section>
</template>
