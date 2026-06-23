<script setup lang="ts">
import { computed, ref } from "vue";

import { loadAssets, loadCrossAssetEvents, loadEventImpacts } from "../api/client";
import StateBlock from "../components/StateBlock.vue";
import { useAsyncData } from "../composables/useAsyncData";

const impacts = useAsyncData(loadEventImpacts);
const assets = useAsyncData(loadAssets);
const events = useAsyncData(loadCrossAssetEvents);
const eventFamily = ref("all");
const direction = ref("all");
const horizon = ref("all");

const loading = computed(
  () => impacts.loading.value || assets.loading.value || events.loading.value,
);
const error = computed(() => impacts.error.value || assets.error.value || events.error.value);
const assetById = computed(() =>
  Object.fromEntries((assets.data.value ?? []).map((asset) => [asset.asset_id, asset])),
);
const eventById = computed(() =>
  Object.fromEntries((events.data.value ?? []).map((event) => [event.event_id, event])),
);
const families = computed(() =>
  Array.from(new Set((events.data.value ?? []).map((event) => event.event_family))).sort(),
);
const directions = computed(() =>
  Array.from(new Set((impacts.data.value ?? []).map((impact) => impact.direction))).sort(),
);
const horizons = computed(() =>
  Array.from(new Set((impacts.data.value ?? []).map((impact) => impact.horizon))).sort(),
);
const rows = computed(() =>
  (impacts.data.value ?? []).filter((impact) => {
    const event = eventById.value[impact.event_id];
    const familyMatch = eventFamily.value === "all" || event?.event_family === eventFamily.value;
    const directionMatch = direction.value === "all" || impact.direction === direction.value;
    const horizonMatch = horizon.value === "all" || impact.horizon === horizon.value;
    return familyMatch && directionMatch && horizonMatch;
  }),
);
</script>

<template>
  <section class="page-stack">
    <div class="section-heading">
      <p class="eyebrow">Event-to-asset hypotheses</p>
      <h2>Event Impact Matrix</h2>
      <p class="muted">Rows are deterministic research hypotheses, not investment instructions.</p>
    </div>

    <StateBlock :loading="loading" :error="error" :empty="!impacts.data.value?.length" />

    <div v-if="impacts.data.value && !loading && !error" class="stack">
      <section class="panel">
        <div class="filters">
          <label>
            Event Family
            <select v-model="eventFamily">
              <option value="all">All</option>
              <option v-for="item in families" :key="item" :value="item">{{ item }}</option>
            </select>
          </label>
          <label>
            Direction
            <select v-model="direction">
              <option value="all">All</option>
              <option v-for="item in directions" :key="item" :value="item">{{ item }}</option>
            </select>
          </label>
          <label>
            Horizon
            <select v-model="horizon">
              <option value="all">All</option>
              <option v-for="item in horizons" :key="item" :value="item">{{ item }}</option>
            </select>
          </label>
        </div>
      </section>

      <section class="panel">
        <h3>{{ rows.length }} Matching Hypotheses</h3>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Event</th>
                <th>Asset</th>
                <th>Family</th>
                <th>Direction</th>
                <th>Horizon</th>
                <th>Status</th>
                <th>Evidence</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in rows.slice(0, 80)" :key="row.impact_id">
                <td>{{ row.event_id }}</td>
                <td>{{ assetById[row.asset_id]?.display_name ?? row.asset_id }}</td>
                <td>{{ eventById[row.event_id]?.event_family ?? "unknown" }}</td>
                <td>{{ row.direction }}</td>
                <td>{{ row.horizon }}</td>
                <td>{{ row.status }}</td>
                <td>{{ row.evidence_codes.slice(0, 2).join(", ") }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  </section>
</template>
