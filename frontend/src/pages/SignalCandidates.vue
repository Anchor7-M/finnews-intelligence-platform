<script setup lang="ts">
import { computed, ref } from "vue";

import { loadAssets, loadMarketSignalCandidates } from "../api/client";
import StateBlock from "../components/StateBlock.vue";
import { useAsyncData } from "../composables/useAsyncData";

const signals = useAsyncData(loadMarketSignalCandidates);
const assets = useAsyncData(loadAssets);
const status = ref("all");
const horizon = ref("all");
const assetClass = ref("all");

const loading = computed(() => signals.loading.value || assets.loading.value);
const error = computed(() => signals.error.value || assets.error.value);
const assetById = computed(() =>
  Object.fromEntries((assets.data.value ?? []).map((asset) => [asset.asset_id, asset])),
);
const statuses = computed(() =>
  Array.from(new Set((signals.data.value ?? []).map((signal) => signal.status))).sort(),
);
const horizons = computed(() =>
  Array.from(new Set((signals.data.value ?? []).map((signal) => signal.horizon))).sort(),
);
const assetClasses = computed(() =>
  Array.from(new Set((assets.data.value ?? []).map((asset) => asset.asset_class))).sort(),
);
const rows = computed(() =>
  (signals.data.value ?? []).filter((signal) => {
    const asset = assetById.value[signal.asset_id];
    const statusMatch = status.value === "all" || signal.status === status.value;
    const horizonMatch = horizon.value === "all" || signal.horizon === horizon.value;
    const classMatch = assetClass.value === "all" || asset?.asset_class === assetClass.value;
    return statusMatch && horizonMatch && classMatch;
  }),
);

function shortHash(value: string): string {
  return value.slice(0, 12);
}
</script>

<template>
  <section class="page-stack">
    <div class="section-heading">
      <p class="eyebrow">Research signal contract</p>
      <h2>Signal Candidates</h2>
      <p class="muted">
        Candidates preserve lineage and hashes. They do not carry account, sizing, or execution
        fields.
      </p>
    </div>

    <StateBlock :loading="loading" :error="error" :empty="!signals.data.value?.length" />

    <div v-if="signals.data.value && !loading && !error" class="stack">
      <section class="panel">
        <div class="filters">
          <label>
            Status
            <select v-model="status">
              <option value="all">All</option>
              <option v-for="item in statuses" :key="item" :value="item">{{ item }}</option>
            </select>
          </label>
          <label>
            Horizon
            <select v-model="horizon">
              <option value="all">All</option>
              <option v-for="item in horizons" :key="item" :value="item">{{ item }}</option>
            </select>
          </label>
          <label>
            Asset Class
            <select v-model="assetClass">
              <option value="all">All</option>
              <option v-for="item in assetClasses" :key="item" :value="item">{{ item }}</option>
            </select>
          </label>
        </div>
      </section>

      <section class="panel">
        <h3>{{ rows.length }} Candidates</h3>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Signal</th>
                <th>Asset</th>
                <th>Class</th>
                <th>Direction</th>
                <th>Horizon</th>
                <th>Status</th>
                <th>Hash</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in rows.slice(0, 80)" :key="row.signal_id">
                <td>{{ row.signal_id }}</td>
                <td>{{ assetById[row.asset_id]?.display_name ?? row.asset_id }}</td>
                <td>{{ assetById[row.asset_id]?.asset_class ?? "unknown" }}</td>
                <td>{{ row.direction }}</td>
                <td>{{ row.horizon }}</td>
                <td>{{ row.status }}</td>
                <td>{{ shortHash(row.payload_hash) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="notice">
        Package validation checks file hashes, content hash, schema version, synthetic-data flags,
        and the absence of prohibited broker/action fields.
      </section>
    </div>
  </section>
</template>
