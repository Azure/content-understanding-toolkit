**Analyzer ID:** `prebuilt-documentFieldSchema`

**Description:** Analyzes documents to propose an appropriate field schema.

This utility analyzer inspects a sample document and returns a proposed Content Understanding field schema in the `schema` field. Use it as a starting point when no domain-specific prebuilt analyzer fits. Review and refine the proposed field names, types, methods, and descriptions before creating a custom analyzer.

With the Content Understanding CLI, use `cu analyzer schema create --from-sample` to generate a proposed schema, then use `cu analyzer create --schema` to create a custom analyzer from the reviewed schema.

For current behavior and field-schema examples, see [Utility analyzers](https://learn.microsoft.com/azure/ai-services/content-understanding/concepts/prebuilt-analyzers#utility-analyzers) and [Create a custom analyzer](https://learn.microsoft.com/azure/ai-services/content-understanding/tutorial/create-custom-analyzer) in the [Content Understanding documentation](https://aka.ms/cu-doc).

| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`schema`|`json`||Proposed field schema based on the underlying document to support structured extraction and generation||