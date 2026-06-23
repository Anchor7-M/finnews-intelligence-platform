<script setup lang="ts">
import { computed } from "vue";

import {
  loadNlpErrorAnalysis,
  loadNlpEvaluations,
  loadNlpModels,
  loadNlpOverview,
} from "../api/client";
import StateBlock from "../components/StateBlock.vue";
import { useAsyncData } from "../composables/useAsyncData";

const overview = useAsyncData(loadNlpOverview);
const models = useAsyncData(loadNlpModels);
const evaluations = useAsyncData(loadNlpEvaluations);
const errors = useAsyncData(loadNlpErrorAnalysis);

const loading = computed(
  () =>
    overview.loading.value ||
    models.loading.value ||
    evaluations.loading.value ||
    errors.loading.value,
);
const error = computed(
  () => overview.error.value || models.error.value || evaluations.error.value || errors.error.value,
);

function metricValue(metrics: Record<string, unknown>, key: string): string {
  const value = metrics[key];
  return typeof value === "number" ? value.toFixed(3) : String(value ?? "");
}

function selectedMetric(evaluation: Record<string, unknown>, system: string, key: string): string {
  const metrics = evaluation.test_metrics as Record<string, Record<string, unknown>>;
  return metricValue(metrics[system] ?? {}, key);
}

function selectedMl(evaluation: Record<string, unknown>): Record<string, unknown> {
  const metrics = evaluation.test_metrics as Record<string, Record<string, unknown>>;
  return metrics.selected_ml ?? {};
}

function perClassRows(
  evaluation: Record<string, unknown>,
): Array<[string, Record<string, unknown>]> {
  const rows = selectedMl(evaluation).per_class as Record<string, Record<string, unknown>>;
  return Object.entries(rows ?? {});
}

function confusionRows(evaluation: Record<string, unknown>): number[][] {
  const matrix =
    (selectedMl(evaluation).confusion_matrix as { matrix?: number[][] } | undefined) ?? {};
  return matrix.matrix ?? [];
}

function reliabilityRows(evaluation: Record<string, unknown>): Array<Record<string, unknown>> {
  return (selectedMl(evaluation).reliability_bins as Array<Record<string, unknown>>) ?? [];
}

function coverageRows(evaluation: Record<string, unknown>): Array<Record<string, unknown>> {
  return (selectedMl(evaluation).confidence_coverage as Array<Record<string, unknown>>) ?? [];
}

function shortHash(value: unknown): string {
  return typeof value === "string" ? value.slice(0, 12) : "";
}
</script>

<template>
  <section class="page">
    <div class="section-heading">
      <p class="eyebrow">Synthetic benchmark / not investment advice</p>
      <h2>NLP Evaluation Lab</h2>
      <p v-if="overview.data.value" class="muted">
        {{ overview.data.value.disclaimer }}
      </p>
    </div>

    <StateBlock :loading="loading" :error="error" :empty="!overview.data.value" />

    <div v-if="overview.data.value && !loading && !error" class="stack">
      <section class="panel">
        <h3>Benchmark</h3>
        <div class="metric-grid">
          <div>
            <span class="label">Records</span>
            <strong>{{ overview.data.value.record_count }}</strong>
          </div>
          <div v-for="(count, split) in overview.data.value.split_counts" :key="split">
            <span class="label">{{ split }}</span>
            <strong>{{ count }}</strong>
          </div>
          <div v-for="(count, language) in overview.data.value.language_counts" :key="language">
            <span class="label">{{ language }}</span>
            <strong>{{ count }}</strong>
          </div>
        </div>
        <p class="muted">{{ overview.data.value.benchmark_claim }}</p>
      </section>

      <section class="panel">
        <h3>Model Comparison</h3>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Task</th>
                <th>Model</th>
                <th>Status</th>
                <th>Dummy F1</th>
                <th>Rule F1</th>
                <th>ML F1</th>
                <th>Accuracy</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="evaluation in evaluations.data.value ?? []"
                :key="evaluation.evaluation_id"
              >
                <td>{{ evaluation.task }}</td>
                <td>{{ evaluation.model_id }}</td>
                <td>
                  {{
                    models.data.value?.find((model) => model.model_id === evaluation.model_id)
                      ?.status
                  }}
                </td>
                <td>{{ selectedMetric(evaluation, "dummy_most_frequent", "macro_f1") }}</td>
                <td>{{ selectedMetric(evaluation, "rule_baseline", "macro_f1") }}</td>
                <td>{{ selectedMetric(evaluation, "selected_ml", "macro_f1") }}</td>
                <td>{{ selectedMetric(evaluation, "selected_ml", "accuracy") }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="panel">
        <h3>Calibration And Coverage</h3>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Task</th>
                <th>Calibration</th>
                <th>Alpha</th>
                <th>Abstention</th>
                <th>ECE</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="model in models.data.value ?? []" :key="model.model_id">
                <td>{{ model.task }}</td>
                <td>{{ model.calibration.status }}</td>
                <td>{{ model.calibration.alpha }}</td>
                <td>{{ model.abstention.threshold }}</td>
                <td>{{ model.calibration.test_ece }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="panel">
        <h3>Per-Class Metrics</h3>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Task</th>
                <th>Class</th>
                <th>Support</th>
                <th>Precision</th>
                <th>Recall</th>
                <th>F1</th>
              </tr>
            </thead>
            <tbody>
              <template
                v-for="evaluation in evaluations.data.value ?? []"
                :key="`${evaluation.evaluation_id}-classes`"
              >
                <tr
                  v-for="[label, row] in perClassRows(evaluation)"
                  :key="`${evaluation.task}-${label}`"
                >
                  <td>{{ evaluation.task }}</td>
                  <td>{{ label }}</td>
                  <td>{{ row.support }}</td>
                  <td>{{ row.precision }}</td>
                  <td>{{ row.recall }}</td>
                  <td>{{ row.f1 }}</td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
      </section>

      <section class="panel">
        <h3>Confusion Matrix</h3>
        <div
          v-for="evaluation in evaluations.data.value ?? []"
          :key="`${evaluation.evaluation_id}-matrix`"
          class="source-note"
        >
          <strong>{{ evaluation.task }} locked test</strong>
          <div class="matrix-grid">
            <span v-for="(row, index) in confusionRows(evaluation)" :key="index">
              {{ row.join(" ") }}
            </span>
          </div>
        </div>
      </section>

      <section class="panel">
        <h3>Reliability And Coverage</h3>
        <div
          v-for="evaluation in evaluations.data.value ?? []"
          :key="`${evaluation.evaluation_id}-reliability`"
          class="source-note"
        >
          <strong>{{ evaluation.task }}</strong>
          <p class="muted">
            Reliability bins:
            {{
              reliabilityRows(evaluation)
                .map((row) => `${row.lower}-${row.upper}:${row.count}`)
                .join(" / ")
            }}
          </p>
          <p class="muted">
            Coverage:
            {{
              coverageRows(evaluation)
                .map((row) => `${row.threshold}:${row.covered_count}`)
                .join(" / ")
            }}
          </p>
        </div>
      </section>

      <section class="panel">
        <h3>Language And Challenge Slices</h3>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Task</th>
                <th>Slice</th>
                <th>Records</th>
                <th>Macro F1</th>
              </tr>
            </thead>
            <tbody>
              <template
                v-for="evaluation in evaluations.data.value ?? []"
                :key="evaluation.evaluation_id"
              >
                <tr
                  v-for="slice in [
                    ...(evaluation.slices.language ?? []),
                    ...(evaluation.slices.challenge_flag ?? []),
                  ]"
                  :key="`${evaluation.task}-${slice.name}`"
                >
                  <td>{{ evaluation.task }}</td>
                  <td>{{ slice.name }}</td>
                  <td>{{ slice.record_count }}</td>
                  <td>{{ slice.macro_f1 }}</td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
      </section>

      <section class="panel">
        <h3>Deterministic Error Examples</h3>
        <div
          v-for="taskErrors in errors.data.value ?? []"
          :key="taskErrors.task"
          class="source-note"
        >
          <strong>{{ taskErrors.task }}</strong>
          <p class="muted">
            False predictions: {{ taskErrors.highest_confidence_false_predictions.length }};
            low-confidence correct examples:
            {{ taskErrors.lowest_confidence_correct_predictions.length }}
          </p>
        </div>
      </section>

      <section class="panel">
        <h3>Artifacts And Limitations</h3>
        <div v-for="model in models.data.value ?? []" :key="`${model.model_id}-artifact`">
          <strong>{{ model.model_id }}</strong>
          <p class="muted">
            Status {{ model.status }}; artifact {{ shortHash(model.artifact_sha256) }};
            {{ model.artifact_size_bytes }} bytes; validation-selected candidate
            {{ model.selected_candidate }}.
          </p>
        </div>
        <p class="muted">
          Metrics are benchmark-only, synthetic generator-defined labels are not human annotations,
          no model is production ready, and Milestone 2B licensed or human-reviewed evaluation is
          deferred.
        </p>
      </section>
    </div>
  </section>
</template>
