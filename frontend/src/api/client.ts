import type {
  Article,
  Company,
  DataMode,
  Digest,
  Overview,
  Signal,
  SourceFetchAttempt,
  SourceHealth,
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
