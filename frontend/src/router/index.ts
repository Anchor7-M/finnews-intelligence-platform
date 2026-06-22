import { createRouter, createWebHistory } from "vue-router";

import ArticleExplorer from "../pages/ArticleExplorer.vue";
import CompanyDetail from "../pages/CompanyDetail.vue";
import DailyDigest from "../pages/DailyDigest.vue";
import Methodology from "../pages/Methodology.vue";
import OverviewPage from "../pages/OverviewPage.vue";
import SourceHealth from "../pages/SourceHealth.vue";

export const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: "/", name: "overview", component: OverviewPage },
    { path: "/articles", name: "articles", component: ArticleExplorer },
    { path: "/companies/:ticker?", name: "companies", component: CompanyDetail },
    { path: "/digest", name: "digest", component: DailyDigest },
    { path: "/sources", name: "sources", component: SourceHealth },
    { path: "/methodology", name: "methodology", component: Methodology },
  ],
});
