<template>
  <section>
    <h2>Methodology</h2>
    <div class="grid">
      <article class="card">
        <h3>Normalization</h3>
        <p>
          Unicode normalization, whitespace cleanup, URL tracking-parameter removal, UTC timestamps.
        </p>
      </article>
      <article class="card">
        <h3>Deduplication</h3>
        <p>SHA-256 exact hashes plus bounded TF-IDF cosine near-duplicate checks.</p>
      </article>
      <article class="card">
        <h3>Entity Linking</h3>
        <p>Deterministic alias matching against fictional companies and tickers.</p>
      </article>
      <article class="card">
        <h3>Baselines</h3>
        <p>Keyword event and sentiment rules for transparent synthetic demonstration.</p>
      </article>
      <article class="card">
        <h3>Limitations</h3>
        <p>No live feeds, no full article bodies, no model claims, no trade recommendations.</p>
      </article>
    </div>
  </section>
</template>
