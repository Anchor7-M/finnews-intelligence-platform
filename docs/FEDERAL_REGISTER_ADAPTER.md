# Federal Register Adapter

Source ID: `federal-register-api`

The Federal Register adapter parses API document metadata and source-provided
abstracts into `RegulatoryDocument` rows.

Storage policy:

- store document number, title, source-provided abstract, publication date,
  type, agencies, CFR/RIN metadata, and official URLs;
- keep official PDF/govinfo links as metadata;
- do not download PDFs;
- do not store full document bodies.

FederalRegister.gov is informational and not the official legal edition.
