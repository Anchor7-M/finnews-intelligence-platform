# Source Configuration

Source definitions live under `config/sources/*.yaml`. They are repository-owned
and validated before use.

Required fields include:

- `source_id`
- `display_name`
- `source_type`
- `approved_hostnames`
- `terms_url`
- `documentation_url` for network sources
- `review_status`
- `enabled`
- `content_storage_policy`
- timeout, response-size, retry, rate-limit, user-agent, language, timezone, and
  provenance fields
- `field_mapping` for documented JSON APIs and user JSON/CSV exports

Supported `source_type` values are `rss`, `atom`, `documented_json_api`,
`user_export_json`, and `user_export_csv`.

No secret fields are allowed in YAML. No committed source is enabled by default.
Unknown fields are rejected. Network examples are illustrative and not approved
production integrations.

Validate locally:

```text
python -m finnews.interfaces.cli.app source validate-config
```
