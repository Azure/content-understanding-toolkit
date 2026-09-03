# Agent Guidance

## Analyzer selection

Start with [`prebuilt-schema/SUPPORTED_ANALYZERS.md`](prebuilt-schema/SUPPORTED_ANALYZERS.md). It is the canonical single-file lookup for supported analyzer IDs, descriptions, API-version availability, and links to exact field schemas.

1. Choose the target API version first.
2. Prefer the most specific analyzer for a known document type.
3. Use a composed family analyzer when the family is known but the subtype is not.
4. Follow the schema link to verify field names and types before writing integrations.
5. Use `prebuilt-documentFieldSchema` only when no prebuilt analyzer fits and a custom analyzer schema is needed.

Use [`prebuilt-schema/README.md`](prebuilt-schema/README.md) when category-oriented navigation or additional usage guidance is useful.

## Keep the inventory synchronized

When adding, removing, renaming, moving, or changing the description of an analyzer schema:

- Update `prebuilt-schema/SUPPORTED_ANALYZERS.md` in the same change.
- Keep one row per analyzer ID in each API-version table.
- Keep analyzer IDs and descriptions identical to the schema-page metadata.
- Keep schema links relative and verify that every link resolves.
- Preserve analyzer field tables unless the schema itself is intentionally changing.