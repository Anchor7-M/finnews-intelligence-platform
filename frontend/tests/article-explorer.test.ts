import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import ArticleExplorer from "../src/pages/ArticleExplorer.vue";

vi.mock("../src/api/client", () => ({
  loadArticles: async () => [
    {
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
    },
  ],
}));

describe("ArticleExplorer", () => {
  it("renders synthetic article filters and results", async () => {
    const wrapper = mount(ArticleExplorer);
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(wrapper.text()).toContain("Alpine Robotics earnings");
    expect(wrapper.text()).toContain("earnings");
  });
});
