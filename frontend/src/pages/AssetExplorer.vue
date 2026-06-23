<script setup lang="ts">
import { computed, ref } from "vue";
import { useRoute } from "vue-router";

import {
  loadAssetAliases,
  loadAssetRelationships,
  loadAssets,
  loadEventImpacts,
} from "../api/client";
import StateBlock from "../components/StateBlock.vue";
import { useAsyncData } from "../composables/useAsyncData";

const route = useRoute();
const assets = useAsyncData(loadAssets);
const aliases = useAsyncData(loadAssetAliases);
const relationships = useAsyncData(loadAssetRelationships);
const impacts = useAsyncData(loadEventImpacts);
const query = ref("");
const assetClass = ref("all");
const region = ref("all");

const loading = computed(
  () =>
    assets.loading.value ||
    aliases.loading.value ||
    relationships.loading.value ||
    impacts.loading.value,
);
const error = computed(
  () =>
    assets.error.value || aliases.error.value || relationships.error.value || impacts.error.value,
);
const selectedAssetId = computed(() => String(route.params.assetId ?? ""));
const classes = computed(() =>
  Array.from(new Set((assets.data.value ?? []).map((asset) => asset.asset_class))).sort(),
);
const regions = computed(() =>
  Array.from(new Set((assets.data.value ?? []).map((asset) => asset.country_region))).sort(),
);
const filteredAssets = computed(() =>
  (assets.data.value ?? []).filter((asset) => {
    const text = `${asset.asset_id} ${asset.display_name} ${asset.canonical_symbol ?? ""}`;
    const queryMatch = !query.value || text.toLowerCase().includes(query.value.toLowerCase());
    const classMatch = assetClass.value === "all" || asset.asset_class === assetClass.value;
    const regionMatch = region.value === "all" || asset.country_region === region.value;
    return queryMatch && classMatch && regionMatch;
  }),
);
const selectedAsset = computed(() =>
  (assets.data.value ?? []).find((asset) => asset.asset_id === selectedAssetId.value),
);
const selectedAliases = computed(() =>
  (aliases.data.value ?? []).filter((alias) => alias.asset_id === selectedAssetId.value),
);
const selectedRelationships = computed(() =>
  (relationships.data.value ?? []).filter(
    (row) =>
      row.source_asset_id === selectedAssetId.value ||
      row.target_asset_id === selectedAssetId.value,
  ),
);
const selectedImpacts = computed(() =>
  (impacts.data.value ?? []).filter((row) => row.asset_id === selectedAssetId.value).slice(0, 12),
);
</script>

<template>
  <section class="page-stack">
    <div class="section-heading">
      <p class="eyebrow">Canonical asset identity</p>
      <h2>Asset Explorer</h2>
    </div>

    <StateBlock :loading="loading" :error="error" :empty="!assets.data.value?.length" />

    <div v-if="assets.data.value && !loading && !error" class="stack">
      <section class="panel">
        <div class="filters">
          <label>
            Search
            <input v-model="query" type="search" placeholder="US-EQ, FX, gold" />
          </label>
          <label>
            Class
            <select v-model="assetClass">
              <option value="all">All</option>
              <option v-for="item in classes" :key="item" :value="item">{{ item }}</option>
            </select>
          </label>
          <label>
            Region
            <select v-model="region">
              <option value="all">All</option>
              <option v-for="item in regions" :key="item" :value="item">{{ item }}</option>
            </select>
          </label>
        </div>
      </section>

      <section class="panel">
        <h3>Registry</h3>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Asset</th>
                <th>Class</th>
                <th>Symbol</th>
                <th>Venue</th>
                <th>Currency</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="asset in filteredAssets.slice(0, 80)"
                :key="asset.asset_id"
                :class="{ selected: asset.asset_id === selectedAssetId }"
              >
                <td>
                  <RouterLink :to="`/assets/${asset.asset_id}`">
                    {{ asset.display_name }}
                  </RouterLink>
                  <span class="label">{{ asset.asset_id }}</span>
                </td>
                <td>{{ asset.asset_class }}</td>
                <td>{{ asset.canonical_symbol ?? "n/a" }}</td>
                <td>{{ asset.home_venue ?? "n/a" }}</td>
                <td>{{ asset.base_currency ?? "" }}{{ asset.quote_currency ?? "" }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section v-if="selectedAsset" class="panel">
        <h3>{{ selectedAsset.display_name }}</h3>
        <div class="metric-grid">
          <div>
            <span class="label">Asset ID</span>
            <strong>{{ selectedAsset.asset_id }}</strong>
          </div>
          <div>
            <span class="label">Aliases</span>
            <strong>{{ selectedAliases.length }}</strong>
          </div>
          <div>
            <span class="label">Relationships</span>
            <strong>{{ selectedRelationships.length }}</strong>
          </div>
          <div>
            <span class="label">Recent Impacts</span>
            <strong>{{ selectedImpacts.length }}</strong>
          </div>
        </div>
        <h4>Aliases</h4>
        <div class="chip-row">
          <span v-for="alias in selectedAliases.slice(0, 24)" :key="alias.id" class="chip">
            {{ alias.namespace }}: {{ alias.symbol }}
          </span>
        </div>
        <h4>Impact Sample</h4>
        <p v-for="impact in selectedImpacts" :key="impact.impact_id" class="muted">
          {{ impact.event_id }} / {{ impact.direction }} / {{ impact.horizon }} /
          {{ impact.status }}
        </p>
      </section>
    </div>
  </section>
</template>
