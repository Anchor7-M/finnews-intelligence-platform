import { mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "../src/App.vue";
import StateBlock from "../src/components/StateBlock.vue";
import ArticleExplorer from "../src/pages/ArticleExplorer.vue";
import AssetExplorer from "../src/pages/AssetExplorer.vue";
import CompanyDetail from "../src/pages/CompanyDetail.vue";
import CrossAssetOverview from "../src/pages/CrossAssetOverview.vue";
import DailyDigest from "../src/pages/DailyDigest.vue";
import EventImpact from "../src/pages/EventImpact.vue";
import IntegrationReadiness from "../src/pages/IntegrationReadiness.vue";
import NlpEvaluation from "../src/pages/NlpEvaluation.vue";
import OverviewPage from "../src/pages/OverviewPage.vue";
import ResearchExport from "../src/pages/ResearchExport.vue";
import SignalCandidates from "../src/pages/SignalCandidates.vue";
import SourceHealth from "../src/pages/SourceHealth.vue";

const article = {
  id: "1",
  title: "Alpine Robotics earnings",
  summary: "Improved margins",
  language: "en",
  published_at: "2026-06-20T01:10:00Z",
  market_date: "2026-06-20",
  url: "https://demo.local/a",
  source_key: "fixture",
  source_name: "Fixture",
  processing_state: "processed",
  tickers: ["ALP"],
  event: "earnings",
  sentiment: "positive",
};

vi.mock("../src/api/client", () => ({
  getDataMode: () => "static-demo",
  loadOverview: async () => ({
    synthetic: true,
    not_investment_advice: true,
    article_count: 46,
    canonical_article_count: 46,
    company_count: 12,
    deduplication: {
      raw_observation_count: 68,
      rejected_observation_count: 4,
      valid_observation_count: 64,
      canonical_article_count: 46,
      exact_duplicate_observation_count: 8,
      near_duplicate_observation_count: 10,
      duplicate_observation_count: 18,
      exact_duplicate_pair_count: 8,
      near_duplicate_pair_count: 10,
      duplicate_cluster_count: 18,
    },
    event_distribution: { earnings: 5 },
    sentiment_distribution: { positive: 8 },
  }),
  loadCrossAssetOverview: async () => ({
    product_positioning:
      "FinNews Intelligence Platform is a local-first cross-asset financial information and event-intelligence platform.",
    synthetic_data: true,
    not_investment_advice: true,
    no_execution: true,
    mt5_terminal_connection: "not_implemented",
    order_execution: "disabled",
    asset_count: 40,
    event_count: 100,
    impact_hypothesis_count: 240,
    signal_candidate_count: 80,
    asset_class_counts: { us_equity: 8, fx: 5 },
    event_family_counts: { monetary_policy: 6 },
    impact_direction_counts: { positive: 59, negative: 59 },
    impact_horizon_counts: { intraday: 60, one_day: 60 },
    signal_status_counts: { research: 16, informational: 16 },
    active_signal_count: 64,
    expired_signal_count: 16,
    contract_name: "finnews-market-signal-v1",
    contract_version: "1.0.0",
    fixture_version: "cross-asset-demo-v1",
    live_prices: false,
    official_market_data: false,
    optional_integrations: ["A-share point-in-time feature export"],
  }),
  loadAssets: async () => [
    {
      id: "a1",
      asset_id: "US-EQ-ALPHA",
      display_name: "Alpha Robotics Synthetic Corp",
      asset_class: "us_equity",
      canonical_symbol: "ALPR",
      home_venue: "XNYS",
      country_region: "US",
      base_currency: "USD",
      quote_currency: null,
      parent_asset_id: null,
      expiry: null,
      contract_metadata: {},
      status: "active",
      synthetic: true,
      provenance: {},
      schema_version: "cross-asset-v1",
    },
    {
      id: "a2",
      asset_id: "FX-EURUSD",
      display_name: "EUR/USD Synthetic FX Pair",
      asset_class: "fx",
      canonical_symbol: "EURUSD",
      home_venue: null,
      country_region: "Global",
      base_currency: "EUR",
      quote_currency: "USD",
      parent_asset_id: null,
      expiry: null,
      contract_metadata: {},
      status: "active",
      synthetic: true,
      provenance: {},
      schema_version: "cross-asset-v1",
    },
  ],
  loadAssetAliases: async () => [
    {
      id: "alias-1",
      asset_id: "US-EQ-ALPHA",
      namespace: "canonical",
      symbol: "US-EQ-ALPHA",
      normalized_symbol: "US-EQ-ALPHA",
      provider: "synthetic_alias_registry",
      provider_version: "1",
      active: true,
      confidence: 1,
      provenance: {},
      valid_from: null,
      valid_to: null,
    },
  ],
  loadAssetRelationships: async () => [
    {
      id: "rel-1",
      relationship_id: "REL-001",
      source_asset_id: "US-EQ-ALPHA",
      target_asset_id: "FX-EURUSD",
      relationship_type: "macro_proxy",
      direction: "association",
      confidence: 0.7,
      active: true,
      provenance: {},
      synthetic: true,
    },
  ],
  loadCrossAssetEvents: async () => [
    {
      id: "event-1",
      event_id: "XAE-001",
      event_family: "monetary_policy",
      event_subtype: "demo",
      description: "Synthetic policy event",
      information_available_at: "2026-06-18T20:00:00Z",
      affected_region: "Global",
      relevant_currency: "USD",
      source_provenance: {},
      provider: "ml_demo_event_mapper",
      provider_version: "1",
      confidence: null,
      uncertainty_flags: ["missing_confidence"],
      duplicate_of_event_id: null,
      synthetic: true,
    },
  ],
  loadEventImpacts: async () => [
    {
      id: "impact-1",
      impact_id: "IMPACT-0001",
      event_id: "XAE-001",
      asset_id: "US-EQ-ALPHA",
      relationship_type: "direct_issuer",
      direction: "positive",
      impact_strength: 0.2,
      confidence: null,
      horizon: "intraday",
      evidence_codes: ["RULE_MONETARY_POLICY"],
      provider: "ml_demo_impact_ranker",
      provider_version: "1",
      information_cutoff_at: "2026-06-18T20:00:00Z",
      created_at: "2026-06-18T20:02:00Z",
      expires_at: "2026-07-18T20:00:00Z",
      status: "active",
      rejection_reason: null,
      uncertainty_reason: "ambiguous_or_missing_confidence",
      synthetic: true,
    },
  ],
  loadMarketSignalCandidates: async () => [
    {
      id: "signal-1",
      signal_id: "SIGNAL-0001",
      impact_id: "IMPACT-0001",
      event_id: "XAE-001",
      asset_id: "US-EQ-ALPHA",
      direction: "positive",
      horizon: "intraday",
      status: "research",
      confidence: null,
      score: null,
      information_cutoff_at: "2026-06-18T20:00:00Z",
      generated_at: "2026-06-18T20:03:00Z",
      expires_at: "2026-07-18T20:00:00Z",
      provider: "deterministic_signal_candidate_generator",
      provider_version: "1",
      evidence_codes: ["RULE_MONETARY_POLICY"],
      quality_tags: ["synthetic"],
      risk_tags: ["not_investment_advice"],
      payload_hash: "a".repeat(64),
      idempotency_key: "b".repeat(64),
      synthetic: true,
    },
  ],
  loadMt5Readiness: async () => ({
    signal_contract_status: "ready",
    symbol_map_schema_status: "ready_offline",
    canonical_mapping_coverage: { mapped_assets: 0, total_assets: 40 },
    utc_policy: "required_for_future_tick_bar_normalization",
    terminal_adapter_status: "not_implemented",
    mt5_terminal_connection: "not implemented",
    execution_status: "disabled",
    order_execution: "disabled",
    credentials_accepted: false,
    account_data_access: false,
    order_routes: false,
    notes: ["Future bridge must be local and read-only before any demo execution milestone."],
  }),
  loadArticles: async () => [
    article,
    {
      ...article,
      id: "2",
      title: "BrightRiver policy",
      language: "zh",
      tickers: ["BRC"],
      event: "policy_regulation",
      sentiment: "neutral",
    },
  ],
  loadCompanies: async () => [
    {
      id: "c1",
      ticker: "ALP",
      exchange: "SYN",
      legal_name: "Alpine Robotics Holdings Ltd.",
      short_name: "Alpine Robotics",
      sector: "Industrial Automation",
      active: true,
    },
  ],
  loadDigests: async () => [
    {
      digest_date: "2026-06-20",
      timezone: "Asia/Shanghai",
      article_count: 2,
      company_count: 1,
      event_counts: { earnings: 1 },
      sentiment_counts: { positive: 1 },
      payload: { synthetic: true, groups: [] },
    },
  ],
  loadSignals: async () => [
    {
      signal_date: "2026-06-20",
      ticker: "ALP",
      article_count: 1,
      unique_source_count: 1,
      weighted_sentiment_score: 0.5,
      negative_event_count: 0,
      event_distribution: { earnings: 1 },
      novelty_score: 0.25,
      source_diversity_score: 0.33,
      schema_version: "demo-v1",
    },
  ],
  loadSourceHealth: async () => [
    {
      source_id: "example-rss-feed",
      display_name: "Example Publisher RSS Feed",
      source_type: "rss",
      approval_status: "unreviewed",
      enabled: false,
      health: "disabled",
      last_attempted_at: null,
      last_successful_at: null,
      last_outcome: "not_run",
      last_http_status: null,
      last_item_count: 0,
      last_response_byte_count: 0,
      consecutive_failure_count: 0,
      etag_available: false,
      last_modified_available: false,
      last_error_category: "none",
      synthetic: true,
    },
    {
      source_id: "mock-approved-rss",
      display_name: "Mock Approved RSS",
      source_type: "rss",
      approval_status: "approved",
      enabled: true,
      health: "healthy",
      last_attempted_at: "2026-06-22T00:00:00Z",
      last_successful_at: "2026-06-22T00:00:00Z",
      last_outcome: "success",
      last_http_status: 200,
      last_item_count: 2,
      last_response_byte_count: 800,
      consecutive_failure_count: 0,
      etag_available: true,
      last_modified_available: true,
      last_error_category: "none",
      synthetic: true,
    },
  ],
  loadSourceReviews: async () => [
    {
      source_id: "example-rss-feed",
      official_owner: "Example Owner",
      official_source: "Example RSS",
      review_decision: "needs_review",
      reviewed_at: "2026-06-22",
      access_cost: "unknown",
      authentication_requirement: "none",
      content_storage_policy: "metadata_only",
      documentation_url: "https://example.local/docs",
      terms_or_policy_url: "https://example.local/terms",
      enabled: false,
      live_smoke_status: "not_run",
      live_smoke_checked_at: null,
      known_limitations: ["example only"],
    },
    {
      source_id: "mock-approved-rss",
      official_owner: "Mock Owner",
      official_source: "Mock RSS",
      review_decision: "approved",
      reviewed_at: "2026-06-22",
      access_cost: "free",
      authentication_requirement: "none",
      content_storage_policy: "metadata_only",
      documentation_url: "https://mock.local/docs",
      terms_or_policy_url: "https://mock.local/terms",
      enabled: true,
      live_smoke_status: "passed",
      live_smoke_checked_at: "2026-06-22",
      known_limitations: ["not production ready"],
    },
  ],
  loadSourceFetchAttempts: async () => [
    {
      id: "attempt-1",
      source_id: "mock-approved-rss",
      outcome: "success",
      started_at: "2026-06-22T00:00:00Z",
      finished_at: "2026-06-22T00:00:01Z",
      http_status: 200,
      item_count: 2,
      new_count: 2,
      duplicate_count: 0,
      rejected_count: 0,
      response_byte_count: 800,
      retry_count: 0,
      error_category: "none",
      error_summary: "",
      etag_available: true,
      last_modified_available: true,
      dry_run: false,
    },
  ],
  loadNlpOverview: async () => ({
    disclaimer:
      "Synthetic benchmark only; generator-defined labels; no live or copyrighted news; not investment advice; real-world licensed evaluation is deferred to Milestone 2B.",
    dataset: {
      dataset_id: "synthetic-finnews-nlp-v1",
      dataset_version: "1.0.0",
      dataset_sha256: "abc",
      split_hashes: { train: "t", validation: "v", test: "x" },
      synthetic_only: true,
    },
    record_count: 1296,
    split_counts: { train: 648, validation: 324, test: 324 },
    language_counts: { zh: 864, en: 432 },
    selected_models: {
      event: "m2a-event-word_char_tfidf_logreg",
      sentiment: "m2a-sentiment-word_char_tfidf_logreg",
    },
    benchmark_claim: "synthetic benchmark only, not real-world accuracy",
    not_investment_advice: true,
  }),
  loadNlpModels: async () => [
    {
      model_id: "m2a-event-word_char_tfidf_logreg",
      task: "event",
      provider: "scikit_learn",
      model_kind: "word_char_tfidf_logreg",
      status: "demo_candidate",
      artifact_sha256: "abc",
      artifact_size_bytes: 1000,
      dataset_sha256: "abc",
      dataset_version: "1.0.0",
      selected_candidate: "word_char_tfidf_logreg",
      promotion_policy: { status: "demo_candidate", checks: { no_live_content: true } },
      calibration: { status: "validation_alpha_improved_ece", alpha: 1.5, test_ece: 0.1 },
      abstention: { threshold: 0.5 },
    },
  ],
  loadNlpEvaluations: async () => [
    {
      evaluation_id: "m2a-event-word_char_tfidf_logreg-test",
      model_id: "m2a-event-word_char_tfidf_logreg",
      task: "event",
      split: "test",
      test_metrics: {
        dummy_most_frequent: { macro_f1: 0.02 },
        rule_baseline: { macro_f1: 0.5 },
        selected_ml: { macro_f1: 1.0, accuracy: 1.0 },
      },
      slices: {
        language: [{ name: "zh", record_count: 216, macro_f1: 1.0 }],
        challenge_flag: [{ name: "negation", record_count: 9, macro_f1: 1.0 }],
      },
      calibration: { status: "validation_alpha_improved_ece" },
      disclaimer: "synthetic only",
    },
  ],
  loadNlpErrorAnalysis: async () => [
    {
      task: "event",
      confusion_pairs: [],
      highest_confidence_false_predictions: [],
      lowest_confidence_correct_predictions: [{ record_id: "m2a-1" }],
      errors_by_language: {},
      errors_by_challenge_flag: {},
    },
  ],
  loadResearchOverview: async () => ({
    contract_name: "finnews-research-export-v1",
    contract_version: "1.0.0",
    export_id: "synthetic-news-factor-demo-v1",
    calendar_id: "synthetic-ashare-demo-calendar",
    calendar_version: "2026-demo-v1",
    calendar_hash: "a".repeat(64),
    cutoff_policy: "pre_open_15m",
    windows: [1, 3, 5, 10],
    package_content_hash: "b".repeat(64),
    counts: {
      session_count: 60,
      company_count: 12,
      feature_row_count: 2880,
      rows_with_news: 349,
      rows_without_news: 2531,
      lineage_row_count: 874,
    },
    synthetic_data: true,
    official_market_calendar: false,
    not_investment_advice: true,
  }),
  loadResearchCalendars: async () => [
    {
      calendar_id: "synthetic-ashare-demo-calendar",
      calendar_version: "2026-demo-v1",
      timezone: "Asia/Shanghai",
      calendar_hash: "a".repeat(64),
      session_count: 60,
      synthetic_data: true,
      official_market_calendar: false,
    },
  ],
  loadResearchExports: async () => [
    {
      export_id: "synthetic-news-factor-demo-v1",
      contract_version: "1.0.0",
      package_content_hash: "b".repeat(64),
      file_hashes: {},
      counts: { feature_row_count: 2880 },
      leakage_status: "passed",
    },
  ],
  loadResearchFeatureCatalog: async () => ({
    contract_name: "finnews-research-export-v1",
    contract_version: "1.0.0",
    feature_schema_version: "news-factor-v1",
    windows: [1, 3, 5, 10],
    null_policy: "null means undefined",
    no_market_data: true,
    features: [{ name: "news_count" }, { name: "mean_sentiment_score" }],
  }),
  loadResearchFeatureSample: async () => [
    {
      contract_version: "1.0.0",
      calendar_id: "synthetic-ashare-demo-calendar",
      calendar_version: "2026-demo-v1",
      session_date: "2026-06-18",
      decision_cutoff_at: "2026-06-18T09:15:00+08:00",
      ticker: "ALP",
      company_id: "company-1",
      window_sessions: 1,
      feature_schema_version: "news-factor-v1",
      news_count: 1,
      has_news: true,
      mean_sentiment_score: 0.5,
      event_entropy: 0,
      source_diversity_ratio: 1,
      hours_since_latest_news: 1,
      lineage_row_id: "lineage-1",
    },
  ],
  loadResearchLineageSample: async () => [
    {
      lineage_row_id: "lineage-1",
      feature_row_key: "key",
      canonical_article_id: "article-1",
      source_id: "synthetic-source",
      company_id: "company-1",
      source_published_at: "2026-06-18T00:00:00Z",
      first_seen_at: "2026-06-18T00:10:00Z",
      processed_at: "2026-06-18T00:11:00Z",
      information_available_at: "2026-06-18T00:10:00Z",
      decision_cutoff_at: "2026-06-18T09:15:00+08:00",
      event_label: "earnings",
      sentiment_label: "positive",
      inclusion_reason: "included",
    },
  ],
}));

describe("frontend compliance", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders overview metrics", async () => {
    const wrapper = mount(OverviewPage);
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(wrapper.text()).toContain("Canonical Articles");
    expect(wrapper.text()).toContain("Cross-Asset Assets");
    expect(wrapper.text()).toContain("Signal Candidates");
    expect(wrapper.text()).toContain("46");
    expect(wrapper.text()).toContain("Raw Observations");
    expect(wrapper.text()).toContain("68");
    expect(wrapper.text()).toContain("exact 8 / near 10");
    expect(wrapper.text()).toContain("12");
    expect(wrapper.text()).toContain("earnings");
  });

  it("renders cross-asset overview, assets, impacts, signals, and readiness", async () => {
    const overview = mount(CrossAssetOverview);
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(overview.text()).toContain("Cross-Asset Overview");
    expect(overview.text()).toContain("40");
    expect(overview.text()).toContain("execution disabled");

    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: "/assets/:assetId?", component: AssetExplorer }],
    });
    router.push("/assets/US-EQ-ALPHA");
    await router.isReady();
    const asset = mount(AssetExplorer, { global: { plugins: [router] } });
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(asset.text()).toContain("Alpha Robotics Synthetic Corp");
    expect(asset.text()).toContain("US-EQ-ALPHA");

    const impacts = mount(EventImpact);
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(impacts.text()).toContain("Event Impact Matrix");
    expect(impacts.text()).toContain("monetary_policy");

    const signals = mount(SignalCandidates);
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(signals.text()).toContain("Signal Candidates");
    expect(signals.text()).toContain("SIGNAL-0001");
    expect(signals.text()).not.toContain("buy signal");

    const readiness = mount(IntegrationReadiness);
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(readiness.text()).toContain("Integration Readiness");
    expect(readiness.text()).toContain("not_implemented");
    expect(readiness.text()).toContain("disabled");
  });

  it("filters articles by text, event, sentiment, and language", async () => {
    const wrapper = mount(ArticleExplorer);
    await new Promise((resolve) => setTimeout(resolve, 0));
    await wrapper.find("input[type='search']").setValue("BrightRiver");
    expect(wrapper.text()).toContain("BrightRiver policy");
    expect(wrapper.text()).not.toContain("Alpine Robotics earnings");
    const selects = wrapper.findAll("select");
    const eventSelect = selects[1];
    const sentimentSelect = selects[2];
    const languageSelect = selects[3];
    expect(eventSelect).toBeDefined();
    expect(sentimentSelect).toBeDefined();
    expect(languageSelect).toBeDefined();
    await eventSelect!.setValue("policy_regulation");
    await sentimentSelect!.setValue("neutral");
    await languageSelect!.setValue("zh");
    expect(wrapper.text()).toContain("BrightRiver policy");
  });

  it("renders loading empty and error states", () => {
    expect(mount(StateBlock, { props: { loading: true } }).text()).toContain("Loading");
    expect(mount(StateBlock, { props: { empty: true } }).text()).toContain("No matching");
    expect(mount(StateBlock, { props: { error: "boom" } }).text()).toContain("boom");
  });

  it("renders company detail and digest", async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: "/companies/:ticker?", component: CompanyDetail }],
    });
    router.push("/companies/ALP");
    await router.isReady();
    const company = mount(CompanyDetail, {
      global: { plugins: [router] },
    });
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(company.text()).toContain("Alpine Robotics");
    expect(company.text()).toContain("sentiment 0.5");
    const digest = mount(DailyDigest);
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(digest.text()).toContain("Synthetic demo data only");
    expect(digest.text()).toContain("2026-06-20");
  });

  it("renders source health and filters by health state", async () => {
    const wrapper = mount(SourceHealth);
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(wrapper.text()).toContain("Source Catalog");
    expect(wrapper.text()).toContain("Reviewed Sources");
    expect(wrapper.text()).toContain("Engineering Approved");
    expect(wrapper.text()).toContain("Example Publisher RSS Feed");
    expect(wrapper.text()).toContain("Mock Approved RSS");
    expect(wrapper.text()).toContain("available");
    expect(wrapper.text()).toContain("Disabled by default");
    expect(wrapper.text()).toContain("not production ready");
    expect(wrapper.text()).not.toContain("FINNEWS_SEC_CONTACT");
    await wrapper.findAll("select")[0]!.setValue("healthy");
    expect(wrapper.text()).toContain("Mock Approved RSS");
    expect(wrapper.text()).not.toContain("Example Publisher RSS Feed");
    await wrapper.findAll("select")[1]!.setValue("approved");
    expect(wrapper.text()).toContain("Mock Approved RSS");
  });

  it("renders nlp evaluation dashboard without artifact paths", async () => {
    const wrapper = mount(NlpEvaluation);
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(wrapper.text()).toContain("NLP Evaluation Lab");
    expect(wrapper.text()).toContain("1296");
    expect(wrapper.text()).toContain("Model Comparison");
    expect(wrapper.text()).toContain("word_char_tfidf_logreg");
    expect(wrapper.text()).toContain("not real-world accuracy");
    expect(wrapper.text()).not.toContain("model.joblib");
    expect(wrapper.text()).not.toContain("C:\\Users");
  });

  it("renders research export dashboard with safe handoff language", async () => {
    const wrapper = mount(ResearchExport);
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(wrapper.text()).toContain("Research Export");
    expect(wrapper.text()).toContain("2880");
    expect(wrapper.text()).toContain("synthetic calendar");
    expect(wrapper.text()).toContain("No official");
    expect(wrapper.text()).toContain("does not calculate returns");
    expect(wrapper.text()).not.toContain("article title");
    expect(wrapper.text()).not.toContain("buy signal");
  });

  it("shows persistent synthetic and not-investment-advice notice with routes", async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: "/", component: OverviewPage },
        { path: "/cross-asset", component: CrossAssetOverview },
        { path: "/assets/:assetId?", component: AssetExplorer },
        { path: "/event-impact", component: EventImpact },
        { path: "/signals", component: SignalCandidates },
        { path: "/integration-readiness", component: IntegrationReadiness },
        { path: "/articles", component: ArticleExplorer },
        { path: "/companies/:ticker?", component: CompanyDetail },
        { path: "/digest", component: DailyDigest },
        { path: "/sources", component: SourceHealth },
        { path: "/nlp-evaluation", component: NlpEvaluation },
        { path: "/optional-integrations/research-export", component: ResearchExport },
        { path: "/methodology", component: OverviewPage },
      ],
    });
    router.push("/");
    await router.isReady();
    const wrapper = mount(App, { global: { plugins: [router] } });
    expect(wrapper.text()).toContain("Synthetic demo data / not investment advice");
    await router.push("/cross-asset");
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain("Cross-Asset Overview");
    await router.push("/articles");
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain("Article Explorer");
    await router.push("/sources");
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain("Source Catalog");
    await router.push("/nlp-evaluation");
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain("NLP Evaluation Lab");
  });
});
