<script setup lang="ts">
import { RouterLink, RouterView } from "vue-router";
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <div>
        <p class="eyebrow">Synthetic demo data / not investment advice</p>
        <h1>Finnews Intelligence Platform</h1>
      </div>
      <nav aria-label="Primary navigation">
        <RouterLink to="/">Overview</RouterLink>
        <RouterLink to="/cross-asset">Cross-Asset</RouterLink>
        <RouterLink to="/assets">Assets</RouterLink>
        <RouterLink to="/event-impact">Impacts</RouterLink>
        <RouterLink to="/market-reaction">Reactions</RouterLink>
        <RouterLink to="/signals">Signals</RouterLink>
        <RouterLink to="/integration-readiness">Readiness</RouterLink>
        <RouterLink to="/articles">Articles</RouterLink>
        <RouterLink to="/companies">Companies</RouterLink>
        <RouterLink to="/optional-integrations/research-export">Optional Export</RouterLink>
        <RouterLink to="/official-data">Official Data</RouterLink>
        <RouterLink to="/methodology">Methodology</RouterLink>
      </nav>
    </header>
    <main>
      <RouterView />
    </main>
  </div>
</template>
