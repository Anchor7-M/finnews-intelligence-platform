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
