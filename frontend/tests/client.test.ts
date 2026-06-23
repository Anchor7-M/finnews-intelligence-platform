import { describe, expect, it, vi } from "vitest";

import {
  loadArticles,
  loadCrossAssetOverview,
  loadMarketSignalCandidates,
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
          : { dataset_count: 4, revision_count: 28 },
    }));
    vi.stubGlobal("fetch", fetchMock);
    await expect(loadOfficialDataOverview("static-demo")).resolves.toMatchObject({
      dataset_count: 4,
    });
    await expect(loadOfficialObservations("api")).resolves.toHaveLength(1);
  });
});
