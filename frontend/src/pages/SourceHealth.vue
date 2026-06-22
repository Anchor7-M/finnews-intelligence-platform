<script setup lang="ts">
import { computed, ref } from "vue";

import { getDataMode, loadSourceFetchAttempts, loadSourceHealth } from "../api/client";
import StateBlock from "../components/StateBlock.vue";
import { useAsyncData } from "../composables/useAsyncData";

const selectedHealth = ref("");
const mode = getDataMode();
const health = useAsyncData(loadSourceHealth);
const attempts = useAsyncData(loadSourceFetchAttempts);

const filteredHealth = computed(() => {
  const rows = health.data.value ?? [];
  if (!selectedHealth.value) {
    return rows;
  }
  return rows.filter((row) => row.health === selectedHealth.value);
});

const outcomes = computed(() => attempts.data.value?.slice(0, 6) ?? []);
</script>

<template>
  <section class="page-stack">
    <div class="section-heading">
      <p class="eyebrow">Synthetic source-health demo / not investment advice</p>
      <h2>Source Health</h2>
      <p>
        {{ mode === "api" ? "FastAPI profile" : "Static demo profile" }}. No browser-side request is
        made to external feeds.
      </p>
    </div>

    <label class="filter-label">
      Health
      <select v-model="selectedHealth">
        <option value="">All health states</option>
        <option value="healthy">Healthy</option>
        <option value="disabled">Disabled</option>
        <option value="failing">Failing</option>
        <option value="blocked">Blocked</option>
      </select>
    </label>

    <StateBlock
      :loading="health.loading.value"
      :error="health.error.value"
      :empty="filteredHealth.length === 0"
    />

    <div v-if="filteredHealth.length" class="source-grid" role="list">
      <article
        v-for="source in filteredHealth"
        :key="source.source_id"
        class="source-card"
        role="listitem"
        tabindex="0"
      >
        <div>
          <p class="eyebrow">{{ source.source_type }} · {{ source.approval_status }}</p>
          <h3>{{ source.display_name }}</h3>
          <p>{{ source.source_id }}</p>
        </div>
        <dl>
          <div>
            <dt>Enabled</dt>
            <dd>{{ source.enabled ? "yes" : "no" }}</dd>
          </div>
          <div>
            <dt>Health</dt>
            <dd>{{ source.health }}</dd>
          </div>
          <div>
            <dt>Last attempt</dt>
            <dd>{{ source.last_attempted_at ?? "not run" }}</dd>
          </div>
          <div>
            <dt>Last success</dt>
            <dd>{{ source.last_successful_at ?? "not run" }}</dd>
          </div>
          <div>
            <dt>Outcome</dt>
            <dd>{{ source.last_outcome }}</dd>
          </div>
          <div>
            <dt>Items</dt>
            <dd>{{ source.last_item_count }}</dd>
          </div>
          <div>
            <dt>Bytes</dt>
            <dd>{{ source.last_response_byte_count }}</dd>
          </div>
          <div>
            <dt>Failures</dt>
            <dd>{{ source.consecutive_failure_count }}</dd>
          </div>
          <div>
            <dt>ETag</dt>
            <dd>{{ source.etag_available ? "available" : "absent" }}</dd>
          </div>
          <div>
            <dt>Last-Modified</dt>
            <dd>{{ source.last_modified_available ? "available" : "absent" }}</dd>
          </div>
          <div>
            <dt>Error</dt>
            <dd>{{ source.last_error_category }}</dd>
          </div>
        </dl>
      </article>
    </div>

    <section class="panel">
      <h3>Recent Fetch Attempts</h3>
      <StateBlock
        :loading="attempts.loading.value"
        :error="attempts.error.value"
        :empty="outcomes.length === 0"
      />
      <table v-if="outcomes.length">
        <thead>
          <tr>
            <th>Source</th>
            <th>Outcome</th>
            <th>Items</th>
            <th>Retries</th>
            <th>HTTP</th>
            <th>Error</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="attempt in outcomes" :key="attempt.id">
            <td>{{ attempt.source_id }}</td>
            <td>{{ attempt.outcome }}</td>
            <td>{{ attempt.item_count }}</td>
            <td>{{ attempt.retry_count }}</td>
            <td>{{ attempt.http_status ?? "n/a" }}</td>
            <td>{{ attempt.error_category }}</td>
          </tr>
        </tbody>
      </table>
    </section>
  </section>
</template>
