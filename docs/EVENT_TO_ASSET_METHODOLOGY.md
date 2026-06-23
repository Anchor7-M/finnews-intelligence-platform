# Event-To-Asset Methodology

The event-to-asset layer turns normalized information events into transparent research hypotheses.

## Event Families

The revised foundation supports 18 event families, including monetary policy, inflation, labor market, growth, liquidity, fiscal policy, regulation, earnings, corporate actions, commodity supply, inventory demand, geopolitical risk, derivatives positioning, exchange infrastructure, crypto ecosystem, crypto regulation, company-specific events, and uncertain other events.

## Impact Hypotheses

Each `AssetImpactHypothesis` records:

- event and asset identifiers;
- relationship type;
- direction: positive, negative, mixed, or uncertain;
- horizon: intraday, one day, one week, or one month;
- strength, confidence, evidence codes, status, and expiry;
- information cutoff timestamp.

Hypotheses are deterministic synthetic research rows. They are not predictions, recommendations, or execution instructions.

## Signal Candidates

Signal candidates are a filtered, hashable research handoff surface built from impact hypotheses. Candidate statuses include research, informational, abstained, rejected, and expired. Rejected and abstained rows are retained to keep auditability and coverage accounting visible.
