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
        <h3>Asset Identity</h3>
        <p>
          Canonical asset IDs plus namespace-specific aliases for news, research, and local maps.
        </p>
      </article>
      <article class="card">
        <h3>Event Impact</h3>
        <p>Deterministic event-family mapping creates directional hypotheses by horizon.</p>
      </article>
      <article class="card">
        <h3>Signal Contract</h3>
        <p>
          Research candidates are hashable, versioned, synthetic, and explicitly non-executable.
        </p>
      </article>
      <article class="card">
        <h3>Optional Integrations</h3>
        <p>
          MT5 readiness is offline only; credentials, account access, and execution are disabled.
        </p>
      </article>
      <article class="card">
        <h3>Limitations</h3>
        <p>No live prices, no official market data, no full article bodies, no recommendations.</p>
      </article>
    </div>
  </section>
</template>
