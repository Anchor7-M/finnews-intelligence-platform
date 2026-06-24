export type DataMode = "static-demo" | "api";

export interface Overview {
  synthetic: boolean;
  not_investment_advice: boolean;
  article_count: number;
  canonical_article_count: number;
  company_count: number;
  deduplication: {
    raw_observation_count: number;
    rejected_observation_count: number;
    valid_observation_count: number;
    canonical_article_count: number;
    exact_duplicate_observation_count: number;
    near_duplicate_observation_count: number;
    duplicate_observation_count: number;
    exact_duplicate_pair_count: number;
    near_duplicate_pair_count: number;
    duplicate_cluster_count: number;
  };
  deduplication_groups?: Record<string, string[]>;
  event_distribution: Record<string, number>;
  sentiment_distribution: Record<string, number>;
}

export interface Article {
  id: string;
  title: string;
  summary: string;
  language: string;
  published_at: string;
  market_date: string;
  url: string;
  source_key: string;
  source_name: string;
  processing_state: string;
  tickers: string[];
  event: string;
  sentiment: string;
}

export interface Company {
  id: string;
  ticker: string;
  exchange: string;
  legal_name: string;
  short_name: string;
  sector: string;
  active: boolean;
}

export interface Digest {
  digest_date: string;
  timezone: string;
  article_count: number;
  company_count: number;
  event_counts: Record<string, number>;
  sentiment_counts: Record<string, number>;
  payload: { groups?: Array<Record<string, unknown>>; synthetic?: boolean };
}

export interface Signal {
  signal_date: string;
  ticker: string;
  article_count: number;
  unique_source_count: number;
  weighted_sentiment_score: number;
  negative_event_count: number;
  event_distribution: Record<string, number>;
  novelty_score: number;
  source_diversity_score: number;
  schema_version: string;
}

export interface SourceSummary {
  source_id: string;
  display_name: string;
  source_type: string;
  approval_status: string;
  enabled: boolean;
  health?: string;
  terms_url?: string;
  documentation_url?: string;
  content_storage_policy?: string;
  language?: string;
  timezone?: string;
  risk_classification?: string;
  approved_host_count?: number;
  synthetic?: boolean;
  review?: SourceReview | null;
}

export interface SourceReview {
  source_id: string;
  official_owner: string;
  official_source: string;
  review_decision: string;
  reviewed_at: string;
  access_cost: string;
  authentication_requirement: string;
  content_storage_policy: string;
  documentation_url: string;
  terms_or_policy_url: string;
  enabled: boolean | null;
  live_smoke_status: string;
  live_smoke_checked_at: string | null;
  known_limitations: string[];
}

export interface SourceHealth {
  source_id: string;
  display_name: string;
  source_type: string;
  approval_status: string;
  enabled: boolean;
  health: string;
  last_attempted_at: string | null;
  last_successful_at: string | null;
  last_outcome: string;
  last_http_status: number | null;
  last_item_count: number;
  last_response_byte_count: number;
  consecutive_failure_count: number;
  etag_available: boolean;
  last_modified_available: boolean;
  last_error_category: string;
  synthetic: boolean;
}

export interface SourceFetchAttempt {
  id: string;
  source_id: string;
  outcome: string;
  started_at: string;
  finished_at: string;
  http_status: number | null;
  item_count: number;
  new_count: number;
  duplicate_count: number;
  rejected_count: number;
  response_byte_count: number;
  retry_count: number;
  error_category: string;
  error_summary: string;
  etag_available: boolean;
  last_modified_available: boolean;
  dry_run: boolean;
}

export interface NlpOverview {
  disclaimer: string;
  dataset: {
    dataset_id: string;
    dataset_version: string;
    dataset_sha256: string;
    split_hashes: Record<string, string>;
    synthetic_only: boolean;
  };
  record_count: number;
  split_counts: Record<string, number>;
  language_counts: Record<string, number>;
  selected_models: Record<string, string>;
  benchmark_claim: string;
  not_investment_advice: boolean;
}

export interface NlpModelSummary {
  model_id: string;
  task: string;
  provider: string;
  model_kind: string;
  status: string;
  artifact_sha256: string;
  artifact_size_bytes: number;
  dataset_sha256: string;
  dataset_version: string;
  selected_candidate: string;
  promotion_policy: { status: string; checks: Record<string, boolean> };
  calibration: Record<string, unknown>;
  abstention: Record<string, unknown>;
}

export interface NlpEvaluationSummary {
  evaluation_id: string;
  model_id: string;
  task: string;
  split: string;
  test_metrics: Record<string, Record<string, unknown>>;
  slices: Record<string, Array<Record<string, unknown>>>;
  calibration: Record<string, unknown>;
  disclaimer: string;
}

export interface NlpErrorAnalysis {
  task: string;
  confusion_pairs: Array<Record<string, unknown>>;
  highest_confidence_false_predictions: Array<Record<string, unknown>>;
  lowest_confidence_correct_predictions: Array<Record<string, unknown>>;
  errors_by_language: Record<string, number>;
  errors_by_challenge_flag: Record<string, number>;
}

export interface ResearchOverview {
  contract_name: string;
  contract_version: string;
  export_id: string;
  calendar_id: string;
  calendar_version: string;
  calendar_hash: string;
  cutoff_policy: string;
  windows: number[];
  package_content_hash: string;
  counts: Record<string, number>;
  synthetic_data: boolean;
  official_market_calendar: boolean;
  not_investment_advice: boolean;
}

export interface ResearchCalendar {
  calendar_id: string;
  calendar_version: string;
  timezone: string;
  calendar_hash: string;
  session_count: number;
  synthetic_data: boolean;
  official_market_calendar: boolean;
}

export interface ResearchExportSummary {
  export_id: string;
  contract_version: string;
  package_content_hash: string;
  file_hashes: Record<string, string>;
  counts: Record<string, number>;
  leakage_status: string;
}

export interface ResearchFeatureCatalog {
  contract_name: string;
  contract_version: string;
  feature_schema_version: string;
  windows: number[];
  null_policy: string;
  no_market_data: boolean;
  features: Array<Record<string, unknown>>;
}

export interface ResearchFeatureRow {
  contract_version: string;
  calendar_id: string;
  calendar_version: string;
  session_date: string;
  decision_cutoff_at: string;
  ticker: string;
  company_id: string;
  window_sessions: number;
  feature_schema_version: string;
  news_count: number;
  has_news: boolean;
  mean_sentiment_score: number | null;
  event_entropy: number | null;
  source_diversity_ratio: number | null;
  hours_since_latest_news: number | null;
  lineage_row_id: string;
  [key: string]: string | number | boolean | null;
}

export interface ResearchLineageRow {
  lineage_row_id: string;
  feature_row_key: string;
  canonical_article_id: string | null;
  source_id: string | null;
  company_id: string | null;
  source_published_at: string | null;
  first_seen_at: string | null;
  processed_at: string | null;
  information_available_at: string | null;
  decision_cutoff_at: string | null;
  event_label: string | null;
  sentiment_label: string | null;
  inclusion_reason: string;
}

export interface CrossAssetOverview {
  product_positioning: string;
  synthetic_data: boolean;
  not_investment_advice: boolean;
  no_execution: boolean;
  mt5_terminal_connection: string;
  order_execution: string;
  asset_count: number;
  event_count: number;
  impact_hypothesis_count: number;
  signal_candidate_count: number;
  asset_class_counts: Record<string, number>;
  event_family_counts: Record<string, number>;
  impact_direction_counts: Record<string, number>;
  impact_horizon_counts: Record<string, number>;
  signal_status_counts: Record<string, number>;
  active_signal_count: number;
  expired_signal_count: number;
  contract_name: string;
  contract_version: string;
  fixture_version: string;
  live_prices: boolean;
  official_market_data: boolean;
  optional_integrations: string[];
}

export interface Asset {
  id: string;
  asset_id: string;
  display_name: string;
  asset_class: string;
  canonical_symbol: string | null;
  home_venue: string | null;
  country_region: string;
  base_currency: string | null;
  quote_currency: string | null;
  parent_asset_id: string | null;
  expiry: string | null;
  contract_metadata: Record<string, unknown>;
  status: string;
  synthetic: boolean;
  provenance: Record<string, unknown>;
  schema_version: string;
}

export interface AssetAlias {
  id: string;
  asset_id: string;
  namespace: string;
  symbol: string;
  normalized_symbol: string;
  provider: string;
  provider_version: string;
  active: boolean;
  confidence: number;
  provenance: Record<string, unknown>;
  valid_from: string | null;
  valid_to: string | null;
}

export interface AssetRelationship {
  id: string;
  relationship_id: string;
  source_asset_id: string;
  target_asset_id: string;
  relationship_type: string;
  direction: string;
  confidence: number;
  active: boolean;
  provenance: Record<string, unknown>;
  synthetic: boolean;
}

export interface CrossAssetEvent {
  id: string;
  event_id: string;
  event_family: string;
  event_subtype: string;
  description: string;
  information_available_at: string;
  affected_region: string;
  relevant_currency: string | null;
  source_provenance: Record<string, unknown>;
  provider: string;
  provider_version: string;
  confidence: number | null;
  uncertainty_flags: string[];
  duplicate_of_event_id: string | null;
  synthetic: boolean;
}

export interface EventImpact {
  id: string;
  impact_id: string;
  event_id: string;
  asset_id: string;
  relationship_type: string;
  direction: string;
  impact_strength: number;
  confidence: number | null;
  horizon: string;
  evidence_codes: string[];
  provider: string;
  provider_version: string;
  information_cutoff_at: string;
  created_at: string;
  expires_at: string;
  status: string;
  rejection_reason: string | null;
  uncertainty_reason: string | null;
  synthetic: boolean;
  asset_class?: string;
  event_family?: string;
}

export interface MarketSignalCandidate {
  id: string;
  signal_id: string;
  impact_id: string;
  event_id: string;
  asset_id: string;
  direction: string;
  horizon: string;
  status: string;
  confidence: number | null;
  score: number | null;
  information_cutoff_at: string;
  generated_at: string;
  expires_at: string;
  provider: string;
  provider_version: string;
  evidence_codes: string[];
  quality_tags: string[];
  risk_tags: string[];
  payload_hash: string;
  idempotency_key: string;
  synthetic: boolean;
  asset_class?: string;
}

export interface Mt5Readiness {
  signal_contract_status: string;
  symbol_map_schema_status: string;
  canonical_mapping_coverage: { mapped_assets: number; total_assets: number };
  utc_policy: string;
  terminal_adapter_status: string;
  mt5_terminal_connection: string;
  execution_status: string;
  order_execution: string;
  credentials_accepted: boolean;
  account_data_access: boolean | string;
  order_routes: boolean;
  notes: string[];
}

export interface Mt5ReadonlyOverview {
  feature_status: string;
  bridge_purpose: string;
  package_required_for_ci: boolean;
  terminal_connection: string;
  order_execution: string;
  account_access: string;
  public_api_trigger: string;
  local_cli_only: boolean;
  not_investment_advice: boolean;
  deferred: string[];
}

export interface Mt5ReadonlyReadiness {
  bridge_feature_status: string;
  package_available: boolean;
  package_status: string;
  terminal_access_status: string;
  local_symbol_map_status: string;
  mapped_asset_count: number;
  unmapped_asset_count: number;
  duplicate_symbol_count: number;
  last_local_readonly_run: Record<string, unknown> | null;
  execution_status: string;
  order_support: string;
  account_access: string;
  public_api_trigger: string;
  mt5_terminal_connection: string;
  order_execution: string;
  not_investment_advice: boolean;
}

export interface Mt5ReadonlySymbolMapSchema {
  schema_version: string;
  allowed_fields: string[];
  forbidden_fields: string[];
  ignored_local_path: string;
  tracked_example_path: string;
  terminal_contacted_by_validation: boolean;
  credentials_allowed: boolean;
  order_fields_allowed: boolean;
}

export interface MarketReactionOverview {
  synthetic_data: boolean;
  not_investment_advice: boolean;
  no_live_market_data: boolean;
  no_execution: boolean;
  mt5_connection: string;
  contract_name: string;
  contract_version: string;
  scenario_count: number;
  scenario_ids: string[];
  asset_count_per_scenario: number;
  session_count_per_scenario: number;
  bar_count_per_scenario: number;
  total_bar_count: number;
  study_count: number;
  label_count: number;
  evaluated_label_count: number;
  metric_row_count: number;
  error_case_count: number;
  market_state_distribution: Record<string, number>;
  label_distribution: Record<string, number>;
  horizon_windows: Record<string, number[]>;
  benchmark_modes: string[];
  label_threshold: string;
  threshold_version: string;
  disclaimer: string;
}

export interface MarketReactionScenario {
  scenario_id: string;
  scenario_version: string;
  description: string;
  asset_count: number;
  session_count: number;
  bar_count: number;
  synthetic_data: boolean;
  official_calendar: boolean;
  no_live_market_data: boolean;
}

export interface MarketReactionStudy {
  study_id: string;
  signal_id: string;
  impact_id: string;
  asset_id: string;
  asset_class: string;
  event_id: string;
  event_family: string;
  event_timestamp: string;
  decision_time: string;
  reaction_window: string;
  bar_coverage: number;
  control_bar_coverage: number;
  raw_return: string | null;
  benchmark_return: string | null;
  scenario_benchmark_return: string | null;
  pre_event_mean_return: string | null;
  abnormal_return: string | null;
  standardized_abnormal_return: string | null;
  magnitude_bucket: string;
  quality_flags: string[];
  excluded_reason: string | null;
  synthetic_scenario_id: string;
  provider: string;
  provider_version: string;
  synthetic_data: boolean;
}

export interface MarketReactionLabel {
  label_id: string;
  study_id: string;
  signal_id: string;
  impact_id: string;
  asset_id: string;
  asset_class: string;
  event_family: string;
  horizon: string;
  scenario_id: string;
  signal_direction: string;
  signal_status: string;
  confidence: number | null;
  strength: number | null;
  signed_score: string;
  raw_return: string | null;
  benchmark_return: string | null;
  abnormal_return: string | null;
  label: string;
  threshold: string;
  threshold_version: string;
  coverage: number;
  quality_flags: string[];
  unavailable_reason: string | null;
  point_in_time_evidence: Record<string, unknown>;
  market_state: string;
  synthetic_data: boolean;
  not_investment_advice: boolean;
}

export interface MarketReactionMetric {
  metric_id: string;
  scenario_id: string;
  slice_type: string;
  slice_value: string;
  evaluated_signal_count: number;
  unavailable_count: number;
  coverage: string;
  directional_consistency_rate: string;
  opposite_rate: string;
  muted_rate: string;
  mean_raw_return: string | null;
  mean_abnormal_return: string | null;
  median_abnormal_return: string | null;
  abnormal_return_volatility: string | null;
  hit_rate_by_direction: Record<string, string | null>;
  information_coefficient: string | null;
  spearman_rank_ic: string | null;
  false_positive_count: number;
  false_negative_count: number;
  high_confidence_wrong_count: number;
  low_confidence_right_count: number;
  missing_confidence_count: number;
  synthetic_data: boolean;
  not_investment_advice: boolean;
}

export interface MarketReactionErrorCase {
  error_case_id: string;
  synthetic_signal_id: string;
  asset_id: string;
  asset_class: string;
  event_family: string;
  expected_direction: string;
  observed_label: string;
  abnormal_return: string | null;
  confidence: number | null;
  strength: number | null;
  horizon: string;
  regime: string;
  scenario_id: string;
  error_category: string;
  synthetic_data: boolean;
  overclaim_guardrail: string;
}

export interface MarketDataPackage {
  package_id: string;
  scenario_id: string;
  provider: string;
  provider_version: string;
  contract_name: string;
  contract_version: string;
  asset_count: number;
  bar_count: number;
  session_count: number;
  first_session_date: string;
  last_session_date: string;
  package_hash: string;
  generated_at: string;
  synthetic_data: boolean;
  no_live_market_data: boolean;
}

export interface MarketDataBar {
  bar_id: string;
  scenario_id: string;
  asset_id: string;
  asset_class: string;
  provider_symbol: string;
  session_date: string;
  bar_start_at: string;
  bar_end_at: string;
  timezone: string;
  open: string;
  high: string;
  low: string;
  close: string;
  volume: string;
  quote_volume: string;
  market_state: string;
  source_profile: string;
  first_seen_at: string;
  available_at: string;
  synthetic_data: boolean;
  schema_version: string;
  provider: string;
  provider_version: string;
}

export interface OfficialDataOverview {
  synthetic_data: boolean;
  not_investment_advice: boolean;
  live_data_persisted: boolean;
  fixture_version: string;
  generated_at: string;
  dataset_count: number;
  series_profile_count: number;
  observation_count: number;
  revision_count: number;
  revised_observation_count: number;
  regulatory_document_count: number;
  series_asset_association_count: number;
  official_release_event_count: number;
  source_counts: Record<string, number>;
  revision_policy: string;
  body_storage: string;
}

export interface OfficialDataset {
  id: string;
  dataset_id: string;
  source_id: string;
  display_name: string;
  category: string;
  description: string;
  documentation_url: string;
  revision_policy: string;
  frequency: string;
  unit: string | null;
  synthetic: boolean;
}

export interface OfficialSeriesProfile {
  id: string;
  profile_id: string;
  dataset_id: string;
  source_id: string;
  display_name: string;
  query: Record<string, unknown>;
  dimensions: Record<string, string>;
  unit: string | null;
  frequency: string;
  seasonal_adjustment: string | null;
  synthetic: boolean;
}

export interface OfficialObservation {
  id: string;
  observation_key: string;
  source_id: string;
  dataset_id: string;
  profile_id: string;
  period_start: string;
  period_end: string;
  dimensions: Record<string, string>;
  current_revision: number;
  current_value: string;
  first_seen_at: string;
  information_available_at: string;
  synthetic: boolean;
}

export interface OfficialRegulatoryDocument {
  id: string;
  document_id: string;
  source_id: string;
  title: string;
  abstract: string;
  publication_date: string;
  document_type: string;
  agencies: string[];
  cfr_references: string[];
  rin: string[];
  html_url: string;
  pdf_url: string | null;
  information_available_at: string;
  synthetic: boolean;
}

export interface OfficialSeriesAssetAssociation {
  id: string;
  association_id: string;
  profile_id: string;
  asset_id: string;
  relationship_type: string;
  rationale: string;
  confidence: number;
  active: boolean;
  synthetic: boolean;
}

export interface OfficialReleaseEvent {
  id: string;
  event_id: string;
  source_id: string;
  dataset_id: string;
  profile_id: string | null;
  document_id: string | null;
  event_family: string;
  description: string;
  information_available_at: string;
  revision_number: number | null;
  synthetic: boolean;
}
