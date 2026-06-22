<script setup lang="ts">
import { computed, ref } from "vue";

import {
  getDataMode,
  loadSourceFetchAttempts,
  loadSourceHealth,
  loadSourceReviews,
} from "../api/client";
import StateBlock from "../components/StateBlock.vue";
import { useAsyncData } from "../composables/useAsyncData";

const selectedHealth = ref("");
const selectedDecision = ref("");
const mode = getDataMode();
const health = useAsyncData(loadSourceHealth);
const attempts = useAsyncData(loadSourceFetchAttempts);
const reviews = useAsyncData(loadSourceReviews);

const reviewBySource = computed(() => {
  const result = new Map<string, NonNullable<(typeof reviews.data.value)>[number]>();
  for (const review of reviews.data.value ?? []) {
    result.set(review.source_id, review);
  }
  return result;
});

const filteredHealth = computed(() => {
  const rows = health.data.value ?? [];
  return rows.filter((row) => {
    const review = reviewBySource.value.get(row.source_id);
    if (selectedHealth.value && row.health !== selectedHealth.value) {
      return false;
    }
    if (selectedDecision.value && review?.review_decision !== selectedDecision.value) {
      return false;
    }
    return true;
  });
});

const outcomes = computed(() => attempts.data.value?.slice(0, 6) ?? []);
const reviewMetrics = computed(() => {
  const rows = reviews.data.value ?? [];
  return {
    total: rows.length,
    approved: rows.filter((row) => row.review_decision === "approved").length,
    smokePassed: rows.filter((row) => row.live_smoke_status === "passed").length,
  };
});
</script>

<template>
  <section class="page-stack">
    <div class="section-heading">
      <p class="eyebrow">Synthetic source-health demo / not investment advice</p>
      <h2>Source Catalog</h2>
      <p>
        {{ mode === "api" ? "FastAPI profile" : "Static demo profile" }}. No browser-side request is
        made to external feeds.
      </p>
    </div>

    <div class="metric-grid">
      <article>
        <span>Reviewed Sources</span>
        <strong>{{ reviewMetrics.total }}</strong>
      </article>
      <article>
        <span>Engineering Approved</span>
        <strong>{{ reviewMetrics.approved }}</strong>
      </article>
      <article>
        <span>Live Smoke Passed</span>
        <strong>{{ reviewMetrics.smokePassed }}</strong>
      </article>
    </div>

    <div class="filters">
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
      <label class="filter-label">
        Review
        <select v-model="selectedDecision">
          <option value="">All review decisions</option>
          <option value="approved">Approved</option>
          <option value="needs_review">Needs review</option>
          <option value="rejected">Rejected</option>
          <option value="suspended">Suspended</option>
        </select>
      </label>
    </div>

    <StateBlock
      :loading="health.loading.value || reviews.loading.value"
      :error="health.error.value || reviews.error.value"
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
          <p class="eyebrow">
            {{ source.source_type }} / {{ reviewBySource.get(source.source_id)?.review_decision ?? source.approval_status }}
          </p>
          <h3>{{ source.display_name }}</h3>
          <p>{{ reviewBySource.get(source.source_id)?.official_owner ?? source.source_id }}</p>
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
            <dt>Review</dt>
            <dd>{{ reviewBySource.get(source.source_id)?.review_decision ?? source.approval_status }}</dd>
          </div>
          <div>
            <dt>Access</dt>
            <dd>{{ reviewBySource.get(source.source_id)?.access_cost ?? "n/a" }}</dd>
          </div>
          <div>
            <dt>Auth</dt>
            <dd>{{ reviewBySource.get(source.source_id)?.authentication_requirement ?? "n/a" }}</dd>
          </div>
          <div>
            <dt>Live smoke</dt>
            <dd>{{ reviewBySource.get(source.source_id)?.live_smoke_status ?? "not_run" }}</dd>
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
            <dt>Items</dt>
            <dd>{{ source.last_item_count }}</dd>
          </div>
          <div>
            <dt>Bytes</dt>
            <dd>{{ source.last_response_byte_count }}</dd>
          </div>
          <div>
            <dt>ETag</dt>
            <dd>{{ source.etag_available ? "available" : "absent" }}</dd>
          </div>
          <div>
            <dt>Last-Modified</dt>
            <dd>{{ source.last_modified_available ? "available" : "absent" }}</dd>
          </div>
        </dl>
        <p class="source-note">Disabled by default. Engineering review is not production readiness.</p>
        <p v-if="reviewBySource.get(source.source_id)?.known_limitations.length" class="source-note">
          {{ reviewBySource.get(source.source_id)?.known_limitations.join("; ") }}
        </p>
        <p v-if="reviewBySource.get(source.source_id)" class="source-links">
          <a :href="reviewBySource.get(source.source_id)?.documentation_url">Documentation</a>
          <a :href="reviewBySource.get(source.source_id)?.terms_or_policy_url">Terms / policy</a>
        </p>
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
