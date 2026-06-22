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
