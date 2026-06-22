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
        <RouterLink to="/articles">Articles</RouterLink>
        <RouterLink to="/companies">Companies</RouterLink>
        <RouterLink to="/digest">Digest</RouterLink>
        <RouterLink to="/sources">Sources</RouterLink>
        <RouterLink to="/nlp-evaluation">NLP</RouterLink>
        <RouterLink to="/methodology">Methodology</RouterLink>
      </nav>
    </header>
    <main>
      <RouterView />
    </main>
  </div>
</template>
