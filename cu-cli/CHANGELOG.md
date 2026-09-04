# Release History

## 0.1.0b1 (2026-09-04)

### Features Added

- Initial release of CU CLI for using Azure Content Understanding from the terminal.
- Added `cu infra generate` to generate an azd/Bicep project used to provision a new or existing Microsoft Foundry resource, optionally deploy supported models, and configure Content Understanding defaults.
- Added `cu profile` to manage named profiles, resource endpoints, authentication, API versions, and model mappings.
- Added `cu doctor` to diagnose authentication, resource connectivity, and model readiness.
- Added `cu env-var` to document supported environment variables and inspect currently configured values with sensitive values redacted.
- Added `cu analyze` to process documents, images, audio, and video individually or in concurrent batches using prebuilt or custom analyzers, with Markdown or service JSON output.
- Added `cu analyzer` to list, inspect, create, copy, test, and delete analyzers, and to generate and validate local analyzer schemas.
- Added `cu defaults` to view and configure model-to-deployment mappings.
- Added `cu upgrade` to check for and explicitly install newer CU CLI releases; upgrades are never automatic.
- Added support for the `2025-11-01` GA API and the `2026-06-01-preview` API.
