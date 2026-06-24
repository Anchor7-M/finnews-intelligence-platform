import type {
  Article,
  Asset,
  AssetAlias,
  AssetRelationship,
  Company,
  CrossAssetEvent,
  CrossAssetOverview,
  DataMode,
  Digest,
  EventImpact,
  MarketSignalCandidate,
  MarketDataBar,
  MarketDataPackage,
  MarketReactionErrorCase,
  MarketReactionLabel,
  MarketReactionMetric,
  MarketReactionOverview,
  MarketReactionScenario,
  MarketReactionStudy,
  Mt5ReadonlyOverview,
  Mt5ReadonlyReadiness,
  Mt5ReadonlySymbolMapSchema,
  Mt5Readiness,
  NlpErrorAnalysis,
  NlpEvaluationSummary,
  NlpModelSummary,
  NlpOverview,
  OfficialDataOverview,
  OfficialDataset,
  OfficialObservation,
  OfficialRegulatoryDocument,
  OfficialReleaseEvent,
  OfficialSeriesAssetAssociation,
  OfficialSeriesProfile,
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

export async function loadCrossAssetOverview(
  mode: DataMode = getDataMode(),
): Promise<CrossAssetOverview> {
  if (mode === "api") {
    return getJson<CrossAssetOverview>(`${API_BASE}/api/v1/cross-asset/overview`);
  }
  return getJson<CrossAssetOverview>("/demo-data/cross-asset-overview.json");
}

export async function loadAssets(mode: DataMode = getDataMode()): Promise<Asset[]> {
  if (mode === "api") {
    const data = await getJson<{ items: Asset[] }>(`${API_BASE}/api/v1/assets?limit=100`);
    return data.items;
  }
  return getJson<Asset[]>("/demo-data/assets.json");
}

export async function loadAssetAliases(mode: DataMode = getDataMode()): Promise<AssetAlias[]> {
  if (mode === "api") {
    const assets = await loadAssets(mode);
    const rows = await Promise.all(
      assets.map((asset) =>
        getJson<AssetAlias[]>(`${API_BASE}/api/v1/assets/${asset.asset_id}/aliases`),
      ),
    );
    return rows.flat();
  }
  return getJson<AssetAlias[]>("/demo-data/asset-aliases.json");
}

export async function loadAssetRelationships(
  mode: DataMode = getDataMode(),
): Promise<AssetRelationship[]> {
  if (mode === "api") {
    return getJson<AssetRelationship[]>(`${API_BASE}/api/v1/asset-relationships`);
  }
  return getJson<AssetRelationship[]>("/demo-data/asset-relationships.json");
}

export async function loadCrossAssetEvents(
  mode: DataMode = getDataMode(),
): Promise<CrossAssetEvent[]> {
  if (mode === "api") {
    return getJson<CrossAssetEvent[]>(`${API_BASE}/api/v1/cross-asset/events`);
  }
  return getJson<CrossAssetEvent[]>("/demo-data/cross-asset-events.json");
}

export async function loadEventImpacts(mode: DataMode = getDataMode()): Promise<EventImpact[]> {
  if (mode === "api") {
    const data = await getJson<{ items: EventImpact[] }>(
      `${API_BASE}/api/v1/event-impacts?limit=200`,
    );
    return data.items;
  }
  return getJson<EventImpact[]>("/demo-data/event-impacts.json");
}

export async function loadMarketSignalCandidates(
  mode: DataMode = getDataMode(),
): Promise<MarketSignalCandidate[]> {
  if (mode === "api") {
    const data = await getJson<{ items: MarketSignalCandidate[] }>(
      `${API_BASE}/api/v1/signals?limit=100`,
    );
    return data.items;
  }
  return getJson<MarketSignalCandidate[]>("/demo-data/market-signals.json");
}

export async function loadMt5Readiness(mode: DataMode = getDataMode()): Promise<Mt5Readiness> {
  if (mode === "api") {
    return getJson<Mt5Readiness>(`${API_BASE}/api/v1/integrations/mt5/readiness`);
  }
  return getJson<Mt5Readiness>("/demo-data/mt5-readiness.json");
}

export async function loadMt5ReadonlyOverview(
  mode: DataMode = getDataMode(),
): Promise<Mt5ReadonlyOverview> {
  if (mode === "api") {
    return getJson<Mt5ReadonlyOverview>(`${API_BASE}/api/v1/integrations/mt5/readonly/overview`);
  }
  return getJson<Mt5ReadonlyOverview>("/demo-data/mt5-readonly-overview.json");
}

export async function loadMt5ReadonlyReadiness(
  mode: DataMode = getDataMode(),
): Promise<Mt5ReadonlyReadiness> {
  if (mode === "api") {
    return getJson<Mt5ReadonlyReadiness>(`${API_BASE}/api/v1/integrations/mt5/readonly/readiness`);
  }
  return getJson<Mt5ReadonlyReadiness>("/demo-data/mt5-readonly-readiness.json");
}

export async function loadMt5ReadonlySymbolMapSchema(
  mode: DataMode = getDataMode(),
): Promise<Mt5ReadonlySymbolMapSchema> {
  if (mode === "api") {
    return getJson<Mt5ReadonlySymbolMapSchema>(
      `${API_BASE}/api/v1/integrations/mt5/readonly/symbol-map/schema`,
    );
  }
  return getJson<Mt5ReadonlySymbolMapSchema>("/demo-data/mt5-readonly-symbol-map-schema.json");
}

export async function loadMarketReactionOverview(
  mode: DataMode = getDataMode(),
): Promise<MarketReactionOverview> {
  if (mode === "api") {
    return getJson<MarketReactionOverview>(`${API_BASE}/api/v1/market-reaction/overview`);
  }
  return getJson<MarketReactionOverview>("/demo-data/market-reaction-overview.json");
}

export async function loadMarketReactionScenarios(
  mode: DataMode = getDataMode(),
): Promise<MarketReactionScenario[]> {
  if (mode === "api") {
    return getJson<MarketReactionScenario[]>(`${API_BASE}/api/v1/market-reaction/scenarios`);
  }
  return getJson<MarketReactionScenario[]>("/demo-data/market-reaction-scenarios.json");
}

export async function loadMarketReactionStudies(
  mode: DataMode = getDataMode(),
): Promise<MarketReactionStudy[]> {
  if (mode === "api") {
    const data = await getJson<{ items: MarketReactionStudy[] }>(
      `${API_BASE}/api/v1/market-reaction/studies?limit=200`,
    );
    return data.items;
  }
  return getJson<MarketReactionStudy[]>("/demo-data/market-reaction-studies.json");
}

export async function loadMarketReactionLabels(
  mode: DataMode = getDataMode(),
): Promise<MarketReactionLabel[]> {
  if (mode === "api") {
    const data = await getJson<{ items: MarketReactionLabel[] }>(
      `${API_BASE}/api/v1/market-reaction/labels?limit=200`,
    );
    return data.items;
  }
  return getJson<MarketReactionLabel[]>("/demo-data/market-reaction-labels-sample.json");
}

export async function loadMarketReactionMetrics(
  mode: DataMode = getDataMode(),
): Promise<MarketReactionMetric[]> {
  if (mode === "api") {
    const data = await getJson<{ items: MarketReactionMetric[] }>(
      `${API_BASE}/api/v1/market-reaction/metrics?limit=200`,
    );
    return data.items;
  }
  return getJson<MarketReactionMetric[]>("/demo-data/market-reaction-metrics.json");
}

export async function loadMarketReactionErrorAnalysis(
  mode: DataMode = getDataMode(),
): Promise<MarketReactionErrorCase[]> {
  if (mode === "api") {
    const data = await getJson<{ items: MarketReactionErrorCase[] }>(
      `${API_BASE}/api/v1/market-reaction/error-analysis?limit=200`,
    );
    return data.items;
  }
  return getJson<MarketReactionErrorCase[]>("/demo-data/market-reaction-error-analysis.json");
}

export async function loadMarketDataPackages(
  mode: DataMode = getDataMode(),
): Promise<MarketDataPackage[]> {
  if (mode === "api") {
    const data = await getJson<{ items: MarketDataPackage[] }>(
      `${API_BASE}/api/v1/market-data/packages`,
    );
    return data.items;
  }
  return getJson<MarketDataPackage[]>("/demo-data/market-data-packages.json");
}

export async function loadMarketDataBars(mode: DataMode = getDataMode()): Promise<MarketDataBar[]> {
  if (mode === "api") {
    const data = await getJson<{ items: MarketDataBar[] }>(
      `${API_BASE}/api/v1/market-data/bars?limit=200`,
    );
    return data.items;
  }
  return getJson<MarketDataBar[]>("/demo-data/market-data-bars-sample.json");
}

export async function loadOfficialDataOverview(
  mode: DataMode = getDataMode(),
): Promise<OfficialDataOverview> {
  if (mode === "api") {
    return getJson<OfficialDataOverview>(`${API_BASE}/api/v1/official-data/overview`);
  }
  return getJson<OfficialDataOverview>("/demo-data/official-data-overview.json");
}

export async function loadOfficialDatasets(
  mode: DataMode = getDataMode(),
): Promise<OfficialDataset[]> {
  if (mode === "api") {
    const data = await getJson<{ items: OfficialDataset[] }>(
      `${API_BASE}/api/v1/official-data/datasets`,
    );
    return data.items;
  }
  return getJson<OfficialDataset[]>("/demo-data/official-datasets.json");
}

export async function loadOfficialSeries(
  mode: DataMode = getDataMode(),
): Promise<OfficialSeriesProfile[]> {
  if (mode === "api") {
    const data = await getJson<{ items: OfficialSeriesProfile[] }>(
      `${API_BASE}/api/v1/official-data/series`,
    );
    return data.items;
  }
  return getJson<OfficialSeriesProfile[]>("/demo-data/official-series.json");
}

export async function loadOfficialObservations(
  mode: DataMode = getDataMode(),
): Promise<OfficialObservation[]> {
  if (mode === "api") {
    const data = await getJson<{ items: OfficialObservation[] }>(
      `${API_BASE}/api/v1/official-data/observations?limit=200`,
    );
    return data.items;
  }
  return getJson<OfficialObservation[]>("/demo-data/official-observations.json");
}

export async function loadOfficialRegulatoryDocuments(
  mode: DataMode = getDataMode(),
): Promise<OfficialRegulatoryDocument[]> {
  if (mode === "api") {
    const data = await getJson<{ items: OfficialRegulatoryDocument[] }>(
      `${API_BASE}/api/v1/official-data/regulatory-documents`,
    );
    return data.items;
  }
  return getJson<OfficialRegulatoryDocument[]>("/demo-data/official-regulatory-documents.json");
}

export async function loadOfficialSeriesAssetAssociations(
  mode: DataMode = getDataMode(),
): Promise<OfficialSeriesAssetAssociation[]> {
  if (mode === "api") {
    const data = await getJson<{ items: OfficialSeriesAssetAssociation[] }>(
      `${API_BASE}/api/v1/official-data/series-asset-associations?limit=200`,
    );
    return data.items;
  }
  return getJson<OfficialSeriesAssetAssociation[]>(
    "/demo-data/official-series-asset-associations.json",
  );
}

export async function loadOfficialReleaseEvents(
  mode: DataMode = getDataMode(),
): Promise<OfficialReleaseEvent[]> {
  if (mode === "api") {
    const data = await getJson<{ items: OfficialReleaseEvent[] }>(
      `${API_BASE}/api/v1/official-data/release-events?limit=200`,
    );
    return data.items;
  }
  return getJson<OfficialReleaseEvent[]>("/demo-data/official-release-events.json");
}
