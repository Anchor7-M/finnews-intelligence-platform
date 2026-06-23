import type {
  Article,
  Company,
  DataMode,
  Digest,
  NlpErrorAnalysis,
  NlpEvaluationSummary,
  NlpModelSummary,
  NlpOverview,
  Overview,
  ResearchCalendar,
  ResearchExportSummary,
  ResearchFeatureCatalog,
  ResearchFeatureRow,
  ResearchLineageRow,
  ResearchOverview,
  Signal,
  SourceFetchAttempt,
  SourceHealth,
  SourceReview,
  SourceSummary,
} from "../types/models";

const API_BASE = import.meta.env.VITE_FINNEWS_API_BASE ?? "http://127.0.0.1:8000";

async function getJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

export function getDataMode(): DataMode {
  const value = import.meta.env.VITE_FINNEWS_DATA_MODE;
  return value === "api" ? "api" : "static-demo";
}

export async function loadOverview(mode: DataMode = getDataMode()): Promise<Overview> {
  if (mode === "api") {
    return getJson<Overview>(`${API_BASE}/api/v1/stats/overview`);
  }
  return getJson<Overview>("/demo-data/overview.json");
}

export async function loadArticles(mode: DataMode = getDataMode()): Promise<Article[]> {
  if (mode === "api") {
    const data = await getJson<{ items: Article[] }>(`${API_BASE}/api/v1/articles?limit=100`);
    return data.items;
  }
  return getJson<Article[]>("/demo-data/articles.json");
}

export async function loadCompanies(mode: DataMode = getDataMode()): Promise<Company[]> {
  if (mode === "api") {
    return getJson<Company[]>(`${API_BASE}/api/v1/companies`);
  }
  return getJson<Company[]>("/demo-data/companies.json");
}

export async function loadDigests(mode: DataMode = getDataMode()): Promise<Digest[]> {
  if (mode === "api") {
    const overview = await loadOverview(mode);
    const today = Object.keys(overview.event_distribution).length ? "2026-06-20" : "2026-06-20";
    return [await getJson<Digest>(`${API_BASE}/api/v1/digests/${today}`)];
  }
  return getJson<Digest[]>("/demo-data/digests.json");
}

export async function loadSignals(mode: DataMode = getDataMode()): Promise<Signal[]> {
  if (mode === "api") {
    return getJson<Signal[]>(`${API_BASE}/api/v1/signals/daily`);
  }
  return getJson<Signal[]>("/demo-data/signals.json");
}

export async function loadSources(mode: DataMode = getDataMode()): Promise<SourceSummary[]> {
  if (mode === "api") {
    const data = await getJson<{ items: SourceSummary[] }>(`${API_BASE}/api/v1/sources`);
    return data.items;
  }
  return getJson<SourceSummary[]>("/demo-data/sources.json");
}

export async function loadSourceHealth(mode: DataMode = getDataMode()): Promise<SourceHealth[]> {
  if (mode === "api") {
    const sources = await loadSources(mode);
    return Promise.all(
      sources.map((source) =>
        getJson<SourceHealth>(`${API_BASE}/api/v1/sources/${source.source_id}/health`),
      ),
    );
  }
  return getJson<SourceHealth[]>("/demo-data/source-health.json");
}

export async function loadSourceFetchAttempts(
  mode: DataMode = getDataMode(),
): Promise<SourceFetchAttempt[]> {
  if (mode === "api") {
    const data = await getJson<{ items: SourceFetchAttempt[] }>(
      `${API_BASE}/api/v1/source-fetch-attempts`,
    );
    return data.items;
  }
  return getJson<SourceFetchAttempt[]>("/demo-data/source-fetch-attempts.json");
}

export async function loadSourceReviews(mode: DataMode = getDataMode()): Promise<SourceReview[]> {
  if (mode === "api") {
    const data = await getJson<{ items: SourceReview[] }>(`${API_BASE}/api/v1/source-reviews`);
    return data.items;
  }
  return getJson<SourceReview[]>("/demo-data/source-reviews.json");
}

export async function loadNlpOverview(mode: DataMode = getDataMode()): Promise<NlpOverview> {
  if (mode === "api") {
    return getJson<NlpOverview>(`${API_BASE}/api/v1/nlp/overview`);
  }
  return getJson<NlpOverview>("/demo-data/nlp-overview.json");
}

export async function loadNlpModels(mode: DataMode = getDataMode()): Promise<NlpModelSummary[]> {
  if (mode === "api") {
    const data = await getJson<{ items: NlpModelSummary[] }>(`${API_BASE}/api/v1/nlp/models`);
    return data.items;
  }
  return getJson<NlpModelSummary[]>("/demo-data/nlp-models.json");
}

export async function loadNlpEvaluations(
  mode: DataMode = getDataMode(),
): Promise<NlpEvaluationSummary[]> {
  if (mode === "api") {
    const data = await getJson<{ items: NlpEvaluationSummary[] }>(
      `${API_BASE}/api/v1/nlp/evaluations`,
    );
    return data.items;
  }
  return getJson<NlpEvaluationSummary[]>("/demo-data/nlp-evaluations.json");
}

export async function loadNlpErrorAnalysis(
  mode: DataMode = getDataMode(),
): Promise<NlpErrorAnalysis[]> {
  if (mode === "api") {
    const data = await getJson<{ items: NlpErrorAnalysis[] }>(
      `${API_BASE}/api/v1/nlp/error-analysis`,
    );
    return data.items;
  }
  return getJson<NlpErrorAnalysis[]>("/demo-data/nlp-error-analysis.json");
}

export async function loadResearchOverview(
  mode: DataMode = getDataMode(),
): Promise<ResearchOverview> {
  if (mode === "api") {
    return getJson<ResearchOverview>(`${API_BASE}/api/v1/research/overview`);
  }
  return getJson<ResearchOverview>("/demo-data/research-overview.json");
}

export async function loadResearchCalendars(
  mode: DataMode = getDataMode(),
): Promise<ResearchCalendar[]> {
  if (mode === "api") {
    return getJson<ResearchCalendar[]>(`${API_BASE}/api/v1/research/calendars`);
  }
  return getJson<ResearchCalendar[]>("/demo-data/research-calendars.json");
}

export async function loadResearchExports(
  mode: DataMode = getDataMode(),
): Promise<ResearchExportSummary[]> {
  if (mode === "api") {
    const data = await getJson<{ items: ResearchExportSummary[] }>(
      `${API_BASE}/api/v1/research/exports`,
    );
    return data.items;
  }
  return getJson<ResearchExportSummary[]>("/demo-data/research-exports.json");
}

export async function loadResearchFeatureCatalog(
  mode: DataMode = getDataMode(),
): Promise<ResearchFeatureCatalog> {
  if (mode === "api") {
    return getJson<ResearchFeatureCatalog>(`${API_BASE}/api/v1/research/feature-catalog`);
  }
  return getJson<ResearchFeatureCatalog>("/demo-data/research-feature-catalog.json");
}

export async function loadResearchFeatureSample(
  mode: DataMode = getDataMode(),
): Promise<ResearchFeatureRow[]> {
  if (mode === "api") {
    const data = await getJson<{ items: ResearchFeatureRow[] }>(
      `${API_BASE}/api/v1/research/features?limit=50`,
    );
    return data.items;
  }
  return getJson<ResearchFeatureRow[]>("/demo-data/research-feature-sample.json");
}

export async function loadResearchLineageSample(
  mode: DataMode = getDataMode(),
): Promise<ResearchLineageRow[]> {
  if (mode === "api") {
    const rows = await loadResearchFeatureSample(mode);
    const first = rows.find((row) => row.lineage_row_id)?.lineage_row_id;
    return first
      ? [await getJson<ResearchLineageRow>(`${API_BASE}/api/v1/research/lineage/${first}`)]
      : [];
  }
  return getJson<ResearchLineageRow[]>("/demo-data/research-lineage-sample.json");
}
