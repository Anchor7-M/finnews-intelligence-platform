# CFTC COT Adapter

Source ID: `cftc-cot-pre`

The CFTC adapter parses public COT PRE rows into revision-aware official
observations.

The adapter does not assume a universal source primary key. Logical identity is
constructed from source, dataset, profile, report date, market identifiers, and
normalized dimensions.

Only bounded public-profile rows are eligible. Automated tests are mocked and
offline.
