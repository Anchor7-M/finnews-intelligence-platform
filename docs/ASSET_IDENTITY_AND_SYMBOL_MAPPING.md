# Asset Identity And Symbol Mapping

Revised Milestone 3A introduces a canonical asset registry so news, model output, research exports, and future local integrations can refer to the same asset without assuming provider-specific symbols.

## Identifiers

- `asset_id`: stable canonical identifier such as `US-EQ-ALPHA` or `FX-EURUSD`.
- `asset_class`: one of the supported cross-asset classes.
- `canonical_symbol`: optional display or research symbol.
- `home_venue`: optional exchange or venue code.
- `base_currency` and `quote_currency`: explicit for FX and other quoted assets.
- `parent_asset_id` and `expiry`: used for futures-root and futures-contract relationships.

## Namespaces

- `canonical`: FinNews-owned asset IDs.
- `news_source`: aliases observed in synthetic source metadata.
- `sec_cik_or_issuer`: issuer-style aliases for future official-source matching.
- `market_data`: provider-neutral market-data aliases.
- `research`: package-facing research symbols.
- `mt5_broker_local`: local broker-specific mapping namespace.

## Local Broker Mapping

`config/integrations/mt5-symbol-map.example.yaml` documents the offline schema. A real mapping file must remain local and ignored as `config/integrations/mt5-symbol-map.local.yaml`.

The schema accepts only:

- `broker_profile_id`
- `canonical_asset_id`
- `mt5_symbol`
- `enabled`
- `local_note`

It rejects credentials, account fields, sizing fields, protective levels, and action fields. FinNews does not infer broker-specific names, contract sizes, volume rules, filling modes, or trading permissions.
