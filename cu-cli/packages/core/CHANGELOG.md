# Release History

## Unreleased

### Bugs Fixed

- Fixed replacement of service defaults to read existing mappings and send
  explicit merge-patch deletions for mappings outside the replacement set.

## 0.1.0b4 (2026-09-17)

### Bugs Fixed

- Replaced SHA-1 with SHA-256 for deterministic output filename collision
  suffixes.

## 0.1.0b3 (2026-09-14)

### Features Added

- Added shared LLM-ready analysis result rendering for official Content
  Understanding command-line frontends.

## 0.1.0b2 (2026-09-11)

### Features Added

- Added shared command and argument specifications for official Content
  Understanding command-line frontends.
- Added shared infrastructure project generation and packaged canonical azd and
  Bicep templates.
- Added shared model selection and postprovision operations.
- Added shared analysis report serialization and diagnostic readiness checks.

### Bugs Fixed

- Improved redaction of credentials and sensitive URL query values in
  diagnostic failures.

## 0.1.0b1 (2026-09-04)

### Features Added

- Initial release of the framework-neutral operations and contracts shared by
  official Azure Content Understanding command-line frontends.