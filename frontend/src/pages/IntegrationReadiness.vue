<script setup lang="ts">
import StateBlock from "../components/StateBlock.vue";
import {
  getDataMode,
  loadMt5Readiness,
  loadMt5ReadonlyOverview,
  loadMt5ReadonlyReadiness,
  loadMt5ReadonlySymbolMapSchema,
} from "../api/client";
import { useAsyncData } from "../composables/useAsyncData";

const { data, error, loading } = useAsyncData(async () => {
  const [legacy, overview, readiness, schema] = await Promise.all([
    loadMt5Readiness(),
    loadMt5ReadonlyOverview(),
    loadMt5ReadonlyReadiness(),
    loadMt5ReadonlySymbolMapSchema(),
  ]);
  return { legacy, overview, readiness, schema };
});
</script>

<template>
  <section class="page-stack">
    <div class="section-heading">
      <p class="eyebrow">Optional local integration boundary</p>
      <h2>MT5 Read-Only Readiness</h2>
      <p class="muted">
        Mode: {{ getDataMode() }}. Local terminal access is CLI-only and unavailable from this
        dashboard.
      </p>
    </div>

    <StateBlock :loading="loading" :error="error" :empty="!data" />

    <div v-if="data && !loading && !error" class="stack">
      <section class="metric-grid">
        <div>
          <span class="label">Bridge</span>
          <strong>{{ data.readiness.bridge_feature_status }}</strong>
        </div>
        <div>
          <span class="label">Terminal</span>
          <strong>{{ data.readiness.mt5_terminal_connection }}</strong>
        </div>
        <div>
          <span class="label">Account Access</span>
          <strong>{{ data.readiness.account_access }}</strong>
        </div>
        <div>
          <span class="label">Execution</span>
          <strong>{{ data.readiness.execution_status }}</strong>
        </div>
      </section>

      <section class="panel">
        <h3>Read-Only Boundary</h3>
        <dl class="definition-list">
          <dt>Purpose</dt>
          <dd>{{ data.overview.bridge_purpose }}</dd>
          <dt>Package status</dt>
          <dd>{{ data.readiness.package_status }}</dd>
          <dt>Terminal access</dt>
          <dd>{{ data.readiness.terminal_access_status }}</dd>
          <dt>Public API trigger</dt>
          <dd>{{ data.readiness.public_api_trigger }}</dd>
          <dt>Order support</dt>
          <dd>{{ data.readiness.order_support }}</dd>
        </dl>
      </section>

      <section class="panel">
        <h3>Symbol Map Schema</h3>
        <dl class="definition-list">
          <dt>Schema</dt>
          <dd>{{ data.schema.schema_version }}</dd>
          <dt>Local path</dt>
          <dd>{{ data.schema.ignored_local_path }}</dd>
          <dt>Allowed fields</dt>
          <dd>{{ data.schema.allowed_fields.join(", ") }}</dd>
          <dt>Credentials</dt>
          <dd>{{ data.schema.credentials_allowed ? "allowed" : "not accepted" }}</dd>
        </dl>
      </section>

      <section class="panel">
        <h3>Mapping Snapshot</h3>
        <p>
          {{ data.readiness.mapped_asset_count }} mapped assets,
          {{ data.readiness.unmapped_asset_count }} unmapped assets, and
          {{ data.readiness.duplicate_symbol_count }} duplicate active symbols in the safe public
          readiness state.
        </p>
        <p class="muted">
          Future demo execution is separate from this read-only milestone. This platform is research
          tooling and not investment advice.
        </p>
      </section>
    </div>
  </section>
</template>
