import { describe, expect, it, vi } from "vitest";

import { loadArticles, loadOverview } from "../src/api/client";

describe("data client", () => {
  it("loads static overview data", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        json: async () => ({ synthetic: true, not_investment_advice: true, article_count: 2 }),
      })),
    );
    await expect(loadOverview("static-demo")).resolves.toMatchObject({ synthetic: true });
  });

  it("transforms API article list envelope", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        json: async () => ({ items: [{ id: "a", title: "Demo", tickers: ["ALP"] }] }),
      })),
    );
    await expect(loadArticles("api")).resolves.toHaveLength(1);
  });
});
