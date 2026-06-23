<script setup lang="ts">
import { computed, ref } from "vue";

import {
  getDataMode,
  loadOfficialDataOverview,
  loadOfficialDatasets,
  loadOfficialObservations,
  loadOfficialRegulatoryDocuments,
  loadOfficialReleaseEvents,
  loadOfficialSeries,
  loadOfficialSeriesAssetAssociations,
} from "../api/client";
import StateBlock from "../components/StateBlock.vue";
import { useAsyncData } from "../composables/useAsyncData";

const mode = getDataMode();
const selectedSource = ref("");
const selectedDataset = ref("");

const overview = useAsyncData(loadOfficialDataOverview);
const datasets = useAsyncData(loadOfficialDatasets);
const series = useAsyncData(loadOfficialSeries);
const observations = useAsyncData(loadOfficialObservations);
const documents = useAsyncData(loadOfficialRegulatoryDocuments);
const associations = useAsyncData(loadOfficialSeriesAssetAssociations);
const events = useAsyncData(loadOfficialReleaseEvents);

const filteredSeries = computed(() =>
  (series.data.value ?? []).filter(
    (row) =>
      (!selectedSource.value || row.source_id === selectedSource.value) &&
      (!selectedDataset.value || row.dataset_id === selectedDataset.value),
  ),
);

const filteredObservations = computed(() =>
  (observations.data.value ?? []).filter(
    (row) =>
      (!selectedSource.value || row.source_id === selectedSource.value) &&
      (!selectedDataset.value || row.dataset_id === selectedDataset.value),
  ),
);

const sourceOptions = computed(() =>
  Array.from(new Set((datasets.data.value ?? []).map((row) => row.source_id))).sort(),
);

const datasetOptions = computed(() =>
  Array.from(new Set((datasets.data.value ?? []).map((row) => row.dataset_id))).sort(),
);

const latestDocuments = computed(() => (documents.data.value ?? []).slice(0, 5));
const latestEvents = computed(() => (events.data.value ?? []).slice(0, 6));
const topAssociations = computed(() => (associations.data.value ?? []).slice(0, 8));
</script>

<template>
  <section class="page-stack">
    <div class="section-heading">
      <p class="eyebrow">Synthetic official-data demo / not investment advice</p>
      <h2>Official Data Monitor</h2>
      <p>
        {{ mode === "api" ? "FastAPI profile" : "Static demo profile" }}. External official sources
        are not called from the browser.
      </p>
    </div>

    <StateBlock
      :loading="overview.loading.value"
      :error="overview.error.value"
      :empty="!overview.data.value"
    />

    <div v-if="overview.data.value" class="metric-grid">
      <article>
        <span>Datasets</span>
        <strong>{{ overview.data.value.dataset_count }}</strong>
      </article>
      <article>
        <span>Series Profiles</span>
        <strong>{{ overview.data.value.series_profile_count }}</strong>
      </article>
      <article>
        <span>Observations</span>
        <strong>{{ overview.data.value.observation_count }}</strong>
      </article>
      <article>
        <span>Revisions</span>
        <strong>{{ overview.data.value.revision_count }}</strong>
      </article>
      <article>
        <span>Documents</span>
        <strong>{{ overview.data.value.regulatory_document_count }}</strong>
      </article>
      <article>
        <span>Asset Links</span>
        <strong>{{ overview.data.value.series_asset_association_count }}</strong>
      </article>
    </div>

    <div class="filters">
      <label class="filter-label">
        Source
        <select v-model="selectedSource">
          <option value="">All sources</option>
          <option v-for="source in sourceOptions" :key="source" :value="source">
            {{ source }}
          </option>
        </select>
      </label>
      <label class="filter-label">
        Dataset
        <select v-model="selectedDataset">
          <option value="">All datasets</option>
          <option v-for="dataset in datasetOptions" :key="dataset" :value="dataset">
            {{ dataset }}
          </option>
        </select>
      </label>
    </div>

    <section class="panel">
      <h3>Datasets And Series</h3>
      <StateBlock
        :loading="datasets.loading.value || series.loading.value"
        :error="datasets.error.value || series.error.value"
        :empty="filteredSeries.length === 0"
      />
      <table v-if="filteredSeries.length">
        <thead>
          <tr>
            <th>Profile</th>
            <th>Dataset</th>
            <th>Source</th>
            <th>Frequency</th>
            <th>Unit</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in filteredSeries" :key="row.profile_id" tabindex="0">
            <td>{{ row.display_name }}</td>
            <td>{{ row.dataset_id }}</td>
            <td>{{ row.source_id }}</td>
            <td>{{ row.frequency }}</td>
            <td>{{ row.unit ?? "metadata" }}</td>
          </tr>
        </tbody>
      </table>
    </section>

    <section class="panel">
      <h3>Current Observations</h3>
      <StateBlock
        :loading="observations.loading.value"
        :error="observations.error.value"
        :empty="filteredObservations.length === 0"
      />
      <table v-if="filteredObservations.length">
        <thead>
          <tr>
            <th>Profile</th>
            <th>Period</th>
            <th>Value</th>
            <th>Revision</th>
            <th>Available At</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in filteredObservations.slice(0, 12)" :key="row.observation_key">
            <td>{{ row.profile_id }}</td>
            <td>{{ row.period_start }}</td>
            <td>{{ row.current_value }}</td>
            <td>{{ row.current_revision }}</td>
            <td>{{ row.information_available_at }}</td>
          </tr>
        </tbody>
      </table>
    </section>

    <div class="two-column">
      <section class="panel">
        <h3>Regulatory Metadata</h3>
        <StateBlock
          :loading="documents.loading.value"
          :error="documents.error.value"
          :empty="latestDocuments.length === 0"
        />
        <article
          v-for="doc in latestDocuments"
          :key="doc.document_id"
          class="source-card compact-card"
          tabindex="0"
        >
          <p class="eyebrow">{{ doc.document_type }} / {{ doc.publication_date }}</p>
          <h4>{{ doc.title }}</h4>
          <p>{{ doc.abstract }}</p>
          <p class="source-note">{{ doc.agencies.join(", ") }}</p>
        </article>
      </section>

      <section class="panel">
        <h3>Derived Release Events</h3>
        <StateBlock
          :loading="events.loading.value"
          :error="events.error.value"
          :empty="latestEvents.length === 0"
        />
        <table v-if="latestEvents.length">
          <thead>
            <tr>
              <th>Event</th>
              <th>Family</th>
              <th>Source</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="event in latestEvents" :key="event.event_id">
              <td>{{ event.event_id }}</td>
              <td>{{ event.event_family }}</td>
              <td>{{ event.source_id }}</td>
            </tr>
          </tbody>
        </table>
      </section>
    </div>

    <section class="panel">
      <h3>Series To Asset Associations</h3>
      <StateBlock
        :loading="associations.loading.value"
        :error="associations.error.value"
        :empty="topAssociations.length === 0"
      />
      <table v-if="topAssociations.length">
        <thead>
          <tr>
            <th>Profile</th>
            <th>Asset</th>
            <th>Confidence</th>
            <th>Relationship</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in topAssociations" :key="row.association_id">
            <td>{{ row.profile_id }}</td>
            <td>{{ row.asset_id }}</td>
            <td>{{ row.confidence.toFixed(2) }}</td>
            <td>{{ row.relationship_type }}</td>
          </tr>
        </tbody>
      </table>
    </section>
  </section>
</template>
