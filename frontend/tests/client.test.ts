import { describe, expect, it, vi } from "vitest";

import {
  loadArticles,
  loadCrossAssetOverview,
  loadMarketDataBars,
  loadMarketSignalCandidates,
  loadMarketReactionLabels,
  loadMarketReactionOverview,
  loadOfficialDataOverview,
  loadOfficialObservations,
  loadOverview,
} from "../src/api/client";

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

  it("loads cross-asset static and API data", async () => {
    const fetchMock = vi.fn(async (url: string) => ({
      ok: true,
      json: async () =>
        url.includes("/api/v1/signals")
          ? { items: [{ signal_id: "SIGNAL-1", status: "research" }] }
          : { asset_count: 40, signal_candidate_count: 80 },
    }));
    vi.stubGlobal("fetch", fetchMock);
    await expect(loadCrossAssetOverview("static-demo")).resolves.toMatchObject({
      asset_count: 40,
    });
    await expect(loadMarketSignalCandidates("api")).resolves.toHaveLength(1);
  });

  it("loads official data static and API envelopes", async () => {
    const fetchMock = vi.fn(async (url: string) => ({
      ok: true,
      json: async () =>
        url.includes("/api/v1/official-data/observations")
          ? { items: [{ observation_key: "obs-1", current_revision: 2 }] }
          : { dataset_count: 4, revision_count: 168, changed_value_revision_count: 24 },
    }));
    vi.stubGlobal("fetch", fetchMock);
    await expect(loadOfficialDataOverview("static-demo")).resolves.toMatchObject({
      dataset_count: 4,
    });
    await expect(loadOfficialObservations("api")).resolves.toHaveLength(1);
  });

  it("loads market reaction static and API envelopes", async () => {
    const fetchMock = vi.fn(async (url: string) => ({
      ok: true,
      json: async () =>
        url.includes("/api/v1/market-reaction/labels") || url.includes("/api/v1/market-data/bars")
          ? { items: [{ label_id: "label-1", scenario_id: "synthetic-planted-reaction-v1" }] }
          : { scenario_count: 3, total_bar_count: 6480, no_live_market_data: true },
    }));
    vi.stubGlobal("fetch", fetchMock);
    await expect(loadMarketReactionOverview("static-demo")).resolves.toMatchObject({
      scenario_count: 3,
    });
    await expect(loadMarketReactionLabels("api")).resolves.toHaveLength(1);
    await expect(loadMarketDataBars("api")).resolves.toHaveLength(1);
  });
});
