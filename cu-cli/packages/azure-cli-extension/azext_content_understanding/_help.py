# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Help text for the Content Understanding extension."""

from knack.help_files import helps

helps["cu"] = """
    type: group
    short-summary: Manage and use Azure Content Understanding.
"""

helps["cu analyzer"] = """
    type: group
    short-summary: Manage Content Understanding analyzers.
"""

helps["cu analyzer list"] = """
    type: command
    short-summary: List analyzers in a Microsoft Foundry resource.
    examples:
      - name: List all analyzers by using an explicit endpoint.
        text: az cu analyzer list --endpoint https://contoso.services.ai.azure.com/
      - name: List prebuilt analyzers using the endpoint from the active CU profile.
        text: az cu analyzer list --kind prebuilt --output table
      - name: Select an analyzer with a JMESPath query.
        text: az cu analyzer list --query "[?analyzerId=='prebuilt-layout']"
"""

helps["cu analyzer show"] = """
    type: command
    short-summary: Show an analyzer definition.
    examples:
      - name: Show an analyzer.
        text: az cu analyzer show --name prebuilt-layout --endpoint https://contoso.services.ai.azure.com/
      - name: Return only the analyzer description.
        text: az cu analyzer show --name prebuilt-layout --query description --output tsv
"""

helps["cu analyzer create"] = """
    type: command
    short-summary: Create an analyzer from a local JSON schema.
    examples:
      - name: Create a custom analyzer.
        text: az cu analyzer create --name ContosoInvoice --schema analyzer.json --endpoint https://contoso.services.ai.azure.com/
"""

helps["cu analyzer delete"] = """
    type: command
    short-summary: Delete an analyzer.
    examples:
      - name: Confirm and delete an analyzer.
        text: az cu analyzer delete --name ContosoInvoice
      - name: Delete an analyzer without prompting.
        text: az cu analyzer delete --name ContosoInvoice --yes
"""

helps["cu analyze"] = """
    type: command
    short-summary: Analyze local files, directories, or HTTPS URLs with Content Understanding.
    examples:
      - name: Analyze an invoice with an explicit analyzer and endpoint.
        text: az cu analyze --file invoice.pdf --analyzer prebuilt-invoice --endpoint https://contoso.services.ai.azure.com/
      - name: Analyze a file using defaults from the active CU profile.
        text: az cu analyze --file invoice.pdf
      - name: Select extracted fields using JMESPath.
        text: az cu analyze --file invoice.pdf --query "contents[0].fields"
      - name: Analyze an HTTPS or Azure Blob SAS URL.
        text: az cu analyze --url "https://storage.example/container/invoice.pdf?<sas>" --analyzer prebuilt-invoice
      - name: Analyze a directory recursively and write results under one directory.
        text: az cu analyze --source documents --recursive --output-dir results --analyzer prebuilt-document --yes
"""

helps["cu defaults"] = """
    type: group
    short-summary: Manage Content Understanding model-deployment defaults.
"""

helps["cu defaults show"] = """
    type: command
    short-summary: Show Content Understanding model-deployment defaults.
    examples:
      - name: Show defaults as JSON.
        text: az cu defaults show --endpoint https://contoso.services.ai.azure.com/
      - name: Show defaults as a table.
        text: az cu defaults show --output table
"""

helps["cu defaults set"] = """
    type: command
    short-summary: Configure Content Understanding model-deployment defaults.
    examples:
      - name: Add or update model deployment mappings.
        text: az cu defaults set --model gpt-5.2=gpt52 --model text-embedding-3-large=embedding3
      - name: Replace all model deployment mappings.
        text: az cu defaults set --model gpt-5.2=gpt52 --replace
"""

helps["cu analyzer validate"] = """
    type: command
    short-summary: Validate a local analyzer schema.
    examples:
      - name: Validate curated rules and the bundled service contract.
        text: az cu analyzer validate --schema analyzer.json --spec --strict
"""

helps["cu analyzer schema"] = """
    type: group
    short-summary: Author Content Understanding analyzer schemas.
"""

helps["cu analyzer schema create"] = """
    type: command
    short-summary: Create a starter schema or derive one from a document sample.
    examples:
      - name: Write an extraction starter schema.
        text: az cu analyzer schema create --name ContosoInvoice --output-file analyzer.json
      - name: Derive a schema from one document sample.
        text: az cu analyzer schema create --name ContosoInvoice --from-sample invoice.pdf --output-file analyzer.json
"""

helps["cu analyzer test"] = """
    type: command
    short-summary: Run an analyzer over local samples and return a structured report.
    examples:
      - name: Test all PDF files under a directory.
        text: az cu analyzer test --name ContosoInvoice --source samples --pattern "*.pdf" --output-file report.json --yes
"""

helps["cu analyzer copy"] = """
    type: command
    short-summary: Copy an analyzer within or across Microsoft Foundry resources.
    examples:
      - name: Copy within the resource selected by the active profile.
        text: az cu analyzer copy --source ContosoInvoice --destination ContosoInvoice_v2
      - name: Copy between resources using ARM IDs or account names.
        text: az cu analyzer copy --source ContosoInvoice --destination ContosoInvoice --source-resource source-account --destination-resource target-account
"""

helps["cu profile"] = """
    type: group
    short-summary: Manage CU profiles stored atomically in Azure CLI configuration.
"""

for _name, _summary in {
    "show": "Show an effective CU profile with secrets redacted.",
    "list": "List CU profiles and identify the active profile.",
    "get": "Get one saved CU profile setting.",
    "set": "Set one saved CU profile setting.",
    "unset": "Remove one explicitly saved CU profile setting.",
    "create": "Create an empty named CU profile.",
    "delete": "Delete an inactive named CU profile.",
    "copy": "Copy a CU profile.",
    "rename": "Rename a CU profile.",
    "set-active": "Select the active CU profile.",
    "sync-defaults": "Refresh profile model mappings from service defaults.",
}.items():
    helps[f"cu profile {_name}"] = f"""
        type: command
        short-summary: {_summary}
    """

helps["cu doctor"] = """
    type: command
    short-summary: Return structured Content Understanding readiness checks.
    examples:
      - name: Check the active profile and resource defaults.
        text: az cu doctor --output table
"""

helps["cu env-var"] = """
    type: group
    short-summary: Inspect recognized CU environment-variable names safely.
"""

helps["cu env-var list"] = """
    type: command
    short-summary: List set CU environment variables with secret values redacted.
"""

helps["cu infra"] = """
    type: group
    short-summary: Generate infrastructure-as-code for Content Understanding.
"""

helps["cu infra generate"] = """
    type: command
    short-summary: Generate an azd/Bicep project for Content Understanding.
    long-summary: |
      Writes a self-contained project and returns a structured summary. This
      command does not provision resources or run azd. On a terminal it offers
      subscription, resource, region, and model choices; use --yes for scripts.
    examples:
      - name: Interactively generate a project.
        text: az cu infra generate
      - name: Generate a deterministic project for a new resource.
        text: az cu infra generate --yes --location eastus2 --models recommended --output-dir provision
      - name: Generate a project targeting an existing Foundry resource.
        text: az cu infra generate --foundry-endpoint https://contoso.services.ai.azure.com/ --models none
"""
