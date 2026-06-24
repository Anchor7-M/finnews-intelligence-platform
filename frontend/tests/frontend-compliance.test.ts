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
import MarketReactionLab from "../src/pages/MarketReactionLab.vue";
import NlpEvaluation from "../src/pages/NlpEvaluation.vue";
import OfficialDataMonitor from "../src/pages/OfficialDataMonitor.vue";
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
    mt5_terminal_connection: "not attempted",
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
    terminal_adapter_status: "optional_readonly_cli_only",
    mt5_terminal_connection: "not attempted",
    execution_status: "disabled",
    order_execution: "disabled",
    credentials_accepted: false,
    account_data_access: "not supported",
    order_routes: false,
    notes: ["Read-only bridge access is local CLI-only and disabled by default."],
  }),
  loadMt5ReadonlyOverview: async () => ({
    feature_status: "implemented_optional_local_cli_only",
    bridge_purpose: "read-only terminal readiness, symbol metadata, and historical bar export",
    package_required_for_ci: false,
    terminal_connection: "not attempted",
    order_execution: "disabled",
    account_access: "not supported",
    public_api_trigger: "disabled",
    local_cli_only: true,
    not_investment_advice: true,
    deferred: ["M4B demo execution", "M4C live execution review"],
  }),
  loadMt5ReadonlyReadiness: async () => ({
    bridge_feature_status: "available_optional_local_cli_only",
    package_available: false,
    package_status: "not_checked",
    terminal_access_status: "not_attempted",
    local_symbol_map_status: "not_supplied",
    mapped_asset_count: 0,
    unmapped_asset_count: 40,
    duplicate_symbol_count: 0,
    last_local_readonly_run: null,
    execution_status: "disabled",
    order_support: "not_implemented",
    account_access: "not_supported",
    public_api_trigger: "disabled",
    mt5_terminal_connection: "not attempted",
    order_execution: "disabled",
    not_investment_advice: true,
  }),
  loadMt5ReadonlySymbolMapSchema: async () => ({
    schema_version: "mt5-readonly-symbol-map-v1",
    allowed_fields: ["profile_id", "canonical_asset_id", "mt5_symbol", "enabled"],
    forbidden_fields: ["password", "order_type"],
    ignored_local_path: "config/integrations/mt5-symbol-map.local.yaml",
    tracked_example_path: "config/integrations/mt5-symbol-map.example.yaml",
    terminal_contacted_by_validation: false,
    credentials_allowed: false,
    order_fields_allowed: false,
  }),
  loadMarketReactionOverview: async () => ({
    synthetic_data: true,
    not_investment_advice: true,
    no_live_market_data: true,
    no_execution: true,
    mt5_connection: "not_implemented",
    contract_name: "finnews-market-bars-v1",
    contract_version: "1.0.0",
    scenario_count: 3,
    scenario_ids: [
      "synthetic-null-reaction-v1",
      "synthetic-planted-reaction-v1",
      "synthetic-regime-shift-v1",
    ],
    asset_count_per_scenario: 24,
    session_count_per_scenario: 90,
    bar_count_per_scenario: 2160,
    total_bar_count: 6480,
    study_count: 645,
    label_count: 645,
    evaluated_label_count: 645,
    metric_row_count: 132,
    error_case_count: 72,
    market_state_distribution: { calm: 1296 },
    label_distribution: { muted: 314 },
    horizon_windows: { one_week: [0, 5] },
    benchmark_modes: ["asset_class_equal_weight"],
    label_threshold: "0.0015",
    threshold_version: "m3c-label-threshold-v1",
    disclaimer:
      "Synthetic market scenarios are not real prices. Market-reaction labels are research labels, not allocation instructions, and event studies do not prove causality.",
  }),
  loadMarketReactionScenarios: async () => [
    {
      scenario_id: "synthetic-planted-reaction-v1",
      scenario_version: "market-reaction-synthetic-v1",
      description: "Weak synthetic lagged relation after selected research signals.",
      asset_count: 24,
      session_count: 90,
      bar_count: 2160,
      synthetic_data: true,
      official_calendar: false,
      no_live_market_data: true,
    },
  ],
  loadMarketReactionStudies: async () => [
    {
      study_id: "study-1",
      signal_id: "SIGNAL-0001",
      impact_id: "IMPACT-0001",
      asset_id: "US-EQ-ALPHA",
      asset_class: "us_equity",
      event_id: "XAE-001",
      event_family: "monetary_policy",
      event_timestamp: "2026-06-18T20:00:00Z",
      decision_time: "2026-06-19T00:00:00Z",
      reaction_window: "one_week",
      bar_coverage: 6,
      control_bar_coverage: 5,
      raw_return: "0.010000",
      benchmark_return: "0.001000",
      scenario_benchmark_return: "0.002000",
      pre_event_mean_return: "0.000200",
      abnormal_return: "0.009000",
      standardized_abnormal_return: "1.200000",
      magnitude_bucket: "medium",
      quality_flags: [],
      excluded_reason: null,
      synthetic_scenario_id: "synthetic-planted-reaction-v1",
      provider: "finnews-synthetic-market-reaction",
      provider_version: "market-reaction-synthetic-v1",
      synthetic_data: true,
    },
  ],
  loadMarketReactionLabels: async () => [
    {
      label_id: "label-1",
      study_id: "study-1",
      signal_id: "SIGNAL-0001",
      impact_id: "IMPACT-0001",
      asset_id: "US-EQ-ALPHA",
      asset_class: "us_equity",
      event_family: "monetary_policy",
      horizon: "one_week",
      scenario_id: "synthetic-planted-reaction-v1",
      signal_direction: "positive",
      signal_status: "research",
      confidence: null,
      strength: null,
      signed_score: "0.300000",
      raw_return: "0.010000",
      benchmark_return: "0.001000",
      abnormal_return: "0.009000",
      label: "consistent_positive",
      threshold: "0.0015",
      threshold_version: "m3c-label-threshold-v1",
      coverage: 6,
      quality_flags: [],
      unavailable_reason: null,
      point_in_time_evidence: { bar_available_after_decision: true },
      market_state: "risk_off",
      synthetic_data: true,
      not_investment_advice: true,
    },
  ],
  loadMarketReactionMetrics: async () => [
    {
      metric_id: "metric-1",
      scenario_id: "synthetic-planted-reaction-v1",
      slice_type: "horizon",
      slice_value: "one_week",
      evaluated_signal_count: 40,
      unavailable_count: 0,
      coverage: "1.000000",
      directional_consistency_rate: "0.650000",
      opposite_rate: "0.050000",
      muted_rate: "0.300000",
      mean_raw_return: "0.010000",
      mean_abnormal_return: "0.006000",
      median_abnormal_return: "0.005000",
      abnormal_return_volatility: "0.010000",
      hit_rate_by_direction: { positive: "0.700000" },
      information_coefficient: "0.120000",
      spearman_rank_ic: "0.110000",
      false_positive_count: 2,
      false_negative_count: 3,
      high_confidence_wrong_count: 0,
      low_confidence_right_count: 1,
      missing_confidence_count: 10,
      synthetic_data: true,
      not_investment_advice: true,
    },
  ],
  loadMarketReactionErrorAnalysis: async () => [
    {
      error_case_id: "error-1",
      synthetic_signal_id: "SIGNAL-0001",
      asset_id: "US-EQ-ALPHA",
      asset_class: "us_equity",
      event_family: "monetary_policy",
      expected_direction: "positive",
      observed_label: "consistent_positive",
      abnormal_return: "0.009000",
      confidence: null,
      strength: null,
      horizon: "one_week",
      regime: "risk_off",
      scenario_id: "synthetic-planted-reaction-v1",
      error_category: "diagnostic",
      synthetic_data: true,
      overclaim_guardrail: "diagnostic category only; no causal explanation",
    },
  ],
  loadMarketDataPackages: async () => [
    {
      package_id: "package-1",
      scenario_id: "synthetic-planted-reaction-v1",
      provider: "finnews-synthetic-market-reaction",
      provider_version: "market-reaction-synthetic-v1",
      contract_name: "finnews-market-bars-v1",
      contract_version: "1.0.0",
      asset_count: 24,
      bar_count: 2160,
      session_count: 90,
      first_session_date: "2026-05-01",
      last_session_date: "2026-09-03",
      package_hash: "a".repeat(64),
      generated_at: "2026-06-24T00:00:00+00:00",
      synthetic_data: true,
      no_live_market_data: true,
    },
  ],
  loadMarketDataBars: async () => [
    {
      bar_id: "bar-1",
      scenario_id: "synthetic-planted-reaction-v1",
      asset_id: "US-EQ-ALPHA",
      asset_class: "us_equity",
      provider_symbol: "ALPHA.DEMO",
      session_date: "2026-05-01",
      bar_start_at: "2026-05-01T00:00:00+00:00",
      bar_end_at: "2026-05-01T23:55:00+00:00",
      timezone: "UTC",
      open: "100.000000",
      high: "101.000000",
      low: "99.000000",
      close: "100.500000",
      volume: "100000.000000",
      quote_volume: "10050000.000000",
      market_state: "risk_off",
      source_profile: "synthetic-daily-bars",
      first_seen_at: "2026-05-02T00:00:00+00:00",
      available_at: "2026-05-02T00:00:00+00:00",
      synthetic_data: true,
      schema_version: "finnews-market-bars-v1",
      provider: "finnews-synthetic-market-reaction",
      provider_version: "market-reaction-synthetic-v1",
    },
  ],
  loadOfficialDataOverview: async () => ({
    synthetic_data: true,
    not_investment_advice: true,
    live_data_persisted: false,
    fixture_version: "official-data-synthetic-v1",
    generated_at: "2026-06-24T00:00:00+00:00",
    dataset_count: 4,
    series_profile_count: 16,
    definition_count_total: 16,
    observation_count: 144,
    revision_count: 168,
    physical_revision_row_count: 168,
    changed_value_revision_count: 24,
    revised_observation_count: 24,
    regulatory_document_count: 32,
    series_asset_association_count: 80,
    official_release_event_count: 48,
    source_counts: { "bls-public-data": 1 },
    revision_policy: "append_only_point_in_time",
    body_storage: "metadata_and_source_abstracts_only",
  }),
  loadOfficialDatasets: async () => [
    {
      id: "dataset-1",
      dataset_id: "bls-ces",
      source_id: "bls-public-data",
      display_name: "BLS Current Employment Statistics",
      category: "labor_market",
      description: "Selected synthetic payroll observations.",
      documentation_url: "https://www.bls.gov/developers/",
      revision_policy: "append_only_when_value_changes",
      frequency: "monthly",
      unit: "varies",
      synthetic: true,
    },
  ],
  loadOfficialSeries: async () => [
    {
      id: "series-1",
      profile_id: "bls-ces-total-nonfarm",
      dataset_id: "bls-ces",
      source_id: "bls-public-data",
      display_name: "Total nonfarm payrolls",
      query: { series_id: "CES0000000001" },
      dimensions: { measure: "employment" },
      unit: "thousands_of_persons",
      frequency: "monthly",
      seasonal_adjustment: "seasonally_adjusted",
      synthetic: true,
    },
  ],
  loadOfficialObservations: async () => [
    {
      id: "obs-1",
      observation_key: "obs-key-1",
      source_id: "bls-public-data",
      dataset_id: "bls-ces",
      profile_id: "bls-ces-total-nonfarm",
      period_start: "2026-01-01",
      period_end: "2026-01-01",
      dimensions: { measure: "employment" },
      current_revision: 2,
      current_value: "155001.500000",
      first_seen_at: "2026-06-01T00:00:00+00:00",
      information_available_at: "2026-06-08T00:00:00+00:00",
      synthetic: true,
    },
  ],
  loadOfficialRegulatoryDocuments: async () => [
    {
      id: "doc-1",
      document_id: "FR-SYN-0001",
      source_id: "federal-register-api",
      title: "Synthetic energy regulatory document",
      abstract: "Source-provided synthetic abstract.",
      publication_date: "2026-03-01",
      document_type: "Notice",
      agencies: ["Department of Energy"],
      cfr_references: ["10 CFR 430"],
      rin: ["1904-AF01"],
      html_url: "https://www.federalregister.gov/documents/demo",
      pdf_url: "https://www.govinfo.gov/demo.pdf",
      information_available_at: "2026-03-01T12:00:00+00:00",
      synthetic: true,
    },
  ],
  loadOfficialSeriesAssetAssociations: async () => [
    {
      id: "assoc-1",
      association_id: "ODA-ASSOC-001",
      profile_id: "bls-ces-total-nonfarm",
      asset_id: "US-EQ-ALPHA",
      relationship_type: "macro_relevance_hypothesis",
      rationale: "Synthetic mapping for research navigation only.",
      confidence: 0.75,
      active: true,
      synthetic: true,
    },
  ],
  loadOfficialReleaseEvents: async () => [
    {
      id: "event-1",
      event_id: "ODE-OBS-001",
      source_id: "bls-public-data",
      dataset_id: "bls-ces",
      profile_id: "bls-ces-total-nonfarm",
      document_id: null,
      event_family: "labor_market",
      description: "Synthetic official release",
      information_available_at: "2026-06-08T00:00:00+00:00",
      revision_number: null,
      synthetic: true,
    },
  ],
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
    expect(readiness.text()).toContain("MT5 Read-Only Readiness");
    expect(readiness.text()).toContain("not attempted");
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

  it("renders official data monitor with point-in-time language", async () => {
    const wrapper = mount(OfficialDataMonitor);
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(wrapper.text()).toContain("Official Data Monitor");
    expect(wrapper.text()).toContain("Synthetic official-data demo");
    expect(wrapper.text()).toContain("Datasets");
    expect(wrapper.text()).toContain("168");
    expect(wrapper.text()).toContain("Total nonfarm payrolls");
    expect(wrapper.text()).toContain("155001.500000");
    expect(wrapper.text()).toContain("Regulatory Metadata");
    expect(wrapper.text()).toContain("Synthetic energy regulatory document");
    expect(wrapper.text()).toContain("Series To Asset Associations");
    expect(wrapper.text()).not.toContain("FINNEWS_EIA_API_KEY");
  });

  it("renders market reaction lab with local synthetic validation language", async () => {
    const wrapper = mount(MarketReactionLab);
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(wrapper.text()).toContain("Market Reaction Lab");
    expect(wrapper.text()).toContain("Synthetic market-reaction demo");
    expect(wrapper.text()).toContain("6480");
    expect(wrapper.text()).toContain("Signal Quality Snapshot");
    expect(wrapper.text()).toContain("65.0%");
    expect(wrapper.text()).toContain("Reaction Labels");
    expect(wrapper.text()).toContain("consistent_positive");
    expect(wrapper.text()).toContain("Bar Sample");
    expect(wrapper.text()).toContain("US-EQ-ALPHA");
    expect(wrapper.text()).not.toContain("account_id");
    expect(wrapper.text()).not.toContain("order_type");
    expect(wrapper.text()).not.toContain("Connect MT5");
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
        { path: "/market-reaction", component: MarketReactionLab },
        { path: "/signals", component: SignalCandidates },
        { path: "/integration-readiness", component: IntegrationReadiness },
        { path: "/articles", component: ArticleExplorer },
        { path: "/companies/:ticker?", component: CompanyDetail },
        { path: "/digest", component: DailyDigest },
        { path: "/sources", component: SourceHealth },
        { path: "/official-data", component: OfficialDataMonitor },
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
    await router.push("/official-data");
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain("Official Data Monitor");
    await router.push("/market-reaction");
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain("Market Reaction Lab");
    await router.push("/nlp-evaluation");
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain("NLP Evaluation Lab");
  });
});
