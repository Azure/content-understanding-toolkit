# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Generate native Knack help from the shared CU command specifications."""

from textwrap import dedent, indent

from knack.help_files import helps

from .commands import azure_command_bindings


helps["cu"] = """
    type: group
    short-summary: Manage and use Azure Content Understanding.
"""

helps["cu analyzer"] = """
    type: group
    short-summary: Manage Content Understanding analyzers.
"""

helps["cu analyzer schema"] = """
    type: group
    short-summary: Author Content Understanding analyzer schemas.
"""

helps["cu defaults"] = """
    type: group
    short-summary: Manage Content Understanding model-deployment defaults.
"""

helps["cu profile"] = """
    type: group
    short-summary: Manage CU profiles stored atomically in Azure CLI configuration.
"""

helps["cu env-var"] = """
    type: group
    short-summary: Inspect recognized CU environment-variable names safely.
"""

helps["cu infra"] = """
    type: group
    short-summary: Generate infrastructure-as-code for Content Understanding.
"""

# Examples remain frontend-owned until shared example metadata is introduced.
_COMMAND_DETAILS: dict[tuple[str, ...], str] = {
    ("analyzer", "list"): """
examples:
  - name: List all analyzers by using an explicit endpoint.
    text: az cu analyzer list --endpoint https://contoso.services.ai.azure.com/
  - name: List prebuilt analyzers using the endpoint from the active CU profile.
    text: az cu analyzer list --kind prebuilt --output table
  - name: Select an analyzer with a JMESPath query.
    text: az cu analyzer list --query "[?analyzerId=='prebuilt-layout']"
""",
    ("analyzer", "show"): """
examples:
  - name: Show an analyzer.
    text: az cu analyzer show --name prebuilt-layout --endpoint https://contoso.services.ai.azure.com/
  - name: Return only the analyzer description.
    text: az cu analyzer show --name prebuilt-layout --query description --output tsv
""",
    ("analyzer", "create"): """
examples:
  - name: Create a custom analyzer.
    text: az cu analyzer create --name ContosoInvoice --schema analyzer.json --endpoint https://contoso.services.ai.azure.com/
""",
    ("analyzer", "delete"): """
examples:
  - name: Confirm and delete an analyzer.
    text: az cu analyzer delete --name ContosoInvoice
  - name: Delete an analyzer without prompting.
    text: az cu analyzer delete --name ContosoInvoice --yes
""",
    ("analyze",): """
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
""",
    ("defaults", "show"): """
examples:
  - name: Show defaults as JSON.
    text: az cu defaults show --endpoint https://contoso.services.ai.azure.com/
  - name: Show defaults as a table.
    text: az cu defaults show --output table
""",
    ("defaults", "set"): """
examples:
  - name: Add or update model deployment mappings.
    text: az cu defaults set --model gpt-5.2=gpt52 --model text-embedding-3-large=embedding3
  - name: Replace all model deployment mappings.
    text: az cu defaults set --model gpt-5.2=gpt52 --replace
""",
    ("analyzer", "validate"): """
examples:
  - name: Validate curated rules and the bundled service contract.
    text: az cu analyzer validate --schema analyzer.json --spec --strict
""",
    ("analyzer", "schema", "create"): """
examples:
  - name: Write an extraction starter schema.
    text: az cu analyzer schema create --name ContosoInvoice --output-file analyzer.json
  - name: Derive a schema from one document sample.
    text: az cu analyzer schema create --name ContosoInvoice --from-sample invoice.pdf --output-file analyzer.json
""",
    ("analyzer", "test"): """
examples:
  - name: Test all PDF files under a directory.
    text: az cu analyzer test --name ContosoInvoice --source samples --pattern "*.pdf" --output-file report.json --yes
""",
    ("analyzer", "copy"): """
examples:
  - name: Copy within the resource selected by the active profile.
    text: az cu analyzer copy --source ContosoInvoice --destination ContosoInvoice_v2
  - name: Copy between resources using ARM IDs or account names.
    text: az cu analyzer copy --source ContosoInvoice --destination ContosoInvoice --source-resource source-account --destination-resource target-account
""",
    ("doctor",): """
examples:
  - name: Check the active profile and resource defaults.
    text: az cu doctor --output table
""",
    ("infra", "generate"): """
long-summary: |
  Writes a self-contained project and returns a structured summary. This
  command does not provision resources or run azd. On a terminal it prompts
  only for choices not supplied as arguments.
examples:
  - name: Interactively generate a project.
    text: az cu infra generate
  - name: Generate a project for a new resource without role assignments.
    text: az cu infra generate --location eastus2 --models recommended --assign-roles false --output-dir provision
  - name: Generate a project targeting an existing Foundry resource.
    text: az cu infra generate --foundry-endpoint https://contoso.services.ai.azure.com/ --models none
""",
}


def command_help_key(path: tuple[str, ...]) -> str:
    """Build the native Azure CLI help key for a shared command path."""

    return "cu " + " ".join(path)


def load_command_help() -> None:
    """Register shared command summaries and Azure-specific details with Knack."""

    for spec, azure_path in azure_command_bindings():
        details = dedent(_COMMAND_DETAILS.get(spec.path, "")).strip()
        content = f"type: command\nshort-summary: {spec.help}"
        if details:
            content += "\n" + details
        helps[command_help_key(azure_path)] = "\n" + indent(content, "    ") + "\n"


load_command_help()
