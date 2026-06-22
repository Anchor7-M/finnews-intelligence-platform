# NLP Labeling Guidelines

Milestone 2A labels are generator-defined synthetic gold labels, not independent
human annotations.

## Event Labels

- `earnings`: synthetic results, margins, revenue, profit, or forecast updates.
- `merger_acquisition`: synthetic merger, acquisition, asset sale, or transaction updates.
- `policy_regulation`: synthetic policy, regulatory, compliance, or supervision updates.
- `operations_product`: synthetic product, platform, delivery, outage, or operational updates.
- `financing_capital`: synthetic financing, capital raise, credit, debt, or equity updates.
- `litigation_penalty`: synthetic lawsuit, dispute, penalty, fine, or enforcement updates.
- `governance_personnel`: synthetic board, executive, appointment, resignation, or governance updates.
- `macro_market`: synthetic macro, market, rates, inflation, demand, or sector-wide updates.
- `other`: synthetic items that do not primarily fit another event label.

Precedence: choose the most specific business event. Use `other` only after the
more specific labels fail.

## Sentiment Labels

- `positive`: synthetic text frames the item as beneficial or improving.
- `neutral`: synthetic text is balanced, procedural, or boilerplate.
- `negative`: synthetic text frames pressure, risk, loss, disruption, penalty, or deterioration.
- `uncertain`: synthetic text emphasizes ambiguity, plans, estimates, or unresolved outcomes.

`uncertain` is a sentiment label. Model abstention is separate and means the
model confidence is below a selected threshold.

## Ambiguity Rules

- Mixed-signal text keeps the generator-assigned dominant sentiment.
- Negation changes interpretation only when it reverses the main claim.
- Planned or hypothetical actions should not be treated as completed outcomes.
- Cross-sentence examples require using both sentences, not a single keyword.

All examples are fictional and synthetic. These guidelines do not define a
real-world annotation standard; that is deferred to Milestone 2B.
