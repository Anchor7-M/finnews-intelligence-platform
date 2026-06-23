import { createRouter, createWebHistory } from "vue-router";

import ArticleExplorer from "../pages/ArticleExplorer.vue";
import AssetExplorer from "../pages/AssetExplorer.vue";
import CompanyDetail from "../pages/CompanyDetail.vue";
import CrossAssetOverview from "../pages/CrossAssetOverview.vue";
import DailyDigest from "../pages/DailyDigest.vue";
import EventImpact from "../pages/EventImpact.vue";
import IntegrationReadiness from "../pages/IntegrationReadiness.vue";
import Methodology from "../pages/Methodology.vue";
import NlpEvaluation from "../pages/NlpEvaluation.vue";
import OverviewPage from "../pages/OverviewPage.vue";
import ResearchExport from "../pages/ResearchExport.vue";
import SignalCandidates from "../pages/SignalCandidates.vue";
import SourceHealth from "../pages/SourceHealth.vue";

export const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: "/", name: "overview", component: OverviewPage },
    { path: "/cross-asset", name: "cross-asset", component: CrossAssetOverview },
    { path: "/assets", name: "assets", component: AssetExplorer },
    { path: "/assets/:assetId", name: "asset-detail", component: AssetExplorer },
    { path: "/event-impact", name: "event-impact", component: EventImpact },
    { path: "/signals", name: "signal-candidates", component: SignalCandidates },
    {
      path: "/integration-readiness",
      name: "integration-readiness",
      component: IntegrationReadiness,
    },
    { path: "/articles", name: "articles", component: ArticleExplorer },
    { path: "/companies/:ticker?", name: "companies", component: CompanyDetail },
    { path: "/digest", name: "digest", component: DailyDigest },
    { path: "/sources", name: "sources", component: SourceHealth },
    { path: "/nlp-evaluation", name: "nlp-evaluation", component: NlpEvaluation },
    { path: "/research-export", redirect: "/optional-integrations/research-export" },
    {
      path: "/optional-integrations/research-export",
      name: "research-export",
      component: ResearchExport,
    },
    { path: "/methodology", name: "methodology", component: Methodology },
  ],
});
