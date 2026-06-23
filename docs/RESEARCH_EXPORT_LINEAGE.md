# Research Export Lineage

Every non-empty feature row has lineage rows that reference IDs and timestamps only. Lineage may include canonical article ID, source ID, company ID, source publication time, first-seen time, processed time, information-available time, event label/provider/version, sentiment label/score/confidence/provider/version, assigned session, cutoff, and inclusion reason.

Lineage never includes article title, article summary, article body, source response bytes, headers, local paths, model binary paths, personal metadata, prices, returns, or advice text.

The quality report verifies dense-panel counts, rows with and without news, lineage counts, excluded-observation reasons, null rates, coverage range, and accounting invariants. PostgreSQL stores the same safe metadata and JSONB features; package file bytes are not stored in the database.
