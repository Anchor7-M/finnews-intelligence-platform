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
