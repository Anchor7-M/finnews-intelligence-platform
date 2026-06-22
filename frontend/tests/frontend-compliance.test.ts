import { mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "../src/App.vue";
import StateBlock from "../src/components/StateBlock.vue";
import ArticleExplorer from "../src/pages/ArticleExplorer.vue";
import CompanyDetail from "../src/pages/CompanyDetail.vue";
import DailyDigest from "../src/pages/DailyDigest.vue";
import OverviewPage from "../src/pages/OverviewPage.vue";

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
}));

describe("frontend compliance", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders overview metrics", async () => {
    const wrapper = mount(OverviewPage);
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(wrapper.text()).toContain("Canonical Articles");
    expect(wrapper.text()).toContain("46");
    expect(wrapper.text()).toContain("Raw Observations");
    expect(wrapper.text()).toContain("68");
    expect(wrapper.text()).toContain("exact 8 / near 10");
    expect(wrapper.text()).toContain("12");
    expect(wrapper.text()).toContain("earnings");
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

  it("shows persistent synthetic and not-investment-advice notice with routes", async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: "/", component: OverviewPage },
        { path: "/articles", component: ArticleExplorer },
        { path: "/companies/:ticker?", component: CompanyDetail },
        { path: "/digest", component: DailyDigest },
        { path: "/methodology", component: OverviewPage },
      ],
    });
    router.push("/");
    await router.isReady();
    const wrapper = mount(App, { global: { plugins: [router] } });
    expect(wrapper.text()).toContain("Synthetic demo data / not investment advice");
    await router.push("/articles");
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain("Article Explorer");
  });
});
