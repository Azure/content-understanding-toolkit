# Migrate schema-only custom analyzers to `2026-06-01-preview`

CU CLI is a new, open-source, cross-platform command-line tool for Azure
Content Understanding. See the [CU CLI overview](https://aka.ms/cu-cli) for
more information; this guide includes everything required for this migration.

This guide shows how to export a custom analyzer created with the
`2025-11-01` API and create a corresponding analyzer registration with the
`2026-06-01-preview` API by using CU CLI. It applies to schema-only analyzers
whose definitions don't include `knowledgeSources`, so they have no labeled
training data or other attached knowledge. The guide applies to Windows and
Linux, with Windows commands shown first.

> [!IMPORTANT]
> `2026-06-01-preview` is a public preview API. Preview features are provided
> without a service-level agreement and aren't recommended for production
> workloads. Validate your analyzers and downstream applications before
> changing production traffic.

## Summary

CU CLI supports both `2025-11-01` and `2026-06-01-preview`. For schema-only
custom analyzers, CU CLI can retrieve the live analyzer definition through the
GA API and use that service definition to create a corresponding registration
through the preview API.

If the `2025-11-01` resource uses `gpt-4.1` as its completion model, upgrade its
completion deployment and Content Understanding default to `gpt-5.2` before
creating the preview analyzer. See the
[supported generative models](https://learn.microsoft.com/azure/ai-services/content-understanding/service-limits#supported-generative-models)
in the Content Understanding documentation.

The essential commands are:

```powershell
# Export the live analyzer definition through the GA API.
cu analyzer show SOURCE_ANALYZER_ID --api-version 2025-11-01 > analyzer-service-2025.json

# Confirm that the service definition is valid for the preview API.
cu analyzer validate analyzer-service-2025.json --api-version 2026-06-01-preview

# After confirming that the preview ID is available, create the analyzer.
cu analyzer create PREVIEW_ANALYZER_ID --schema analyzer-service-2025.json --api-version 2026-06-01-preview
```

Analyzer registrations are isolated by API version. The same resource can
contain a `2025-11-01` analyzer and a `2026-06-01-preview` analyzer with the
same ID. Creating the preview analyzer doesn't require deleting the GA
analyzer, so both can remain available during validation.

## Prerequisites

- Python 3.10 or later.
- [PowerShell 7](https://aka.ms/powershell) on Windows for the Windows examples.
- Bash on Linux.
- [Azure CLI](https://aka.ms/azcli).
- A Microsoft Foundry resource in a supported region.
- `Cognitive Services User` access to the resource when using Microsoft Entra
  ID authentication.
- Supported completion and embedding model deployments with Content
  Understanding defaults configured.
- [`jq`](https://jqlang.github.io/jq/) for the optional automated checks and
  comparison commands in this guide.

Install CU CLI in a virtual environment to keep its dependencies separate from
other Python packages. On Windows using PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade cu-cli
cu --version
cu --help
```

On Linux using Bash:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade cu-cli
cu --version
cu --help
```

Activate the virtual environment again in each new shell before running `cu`.
CU CLI also installs a `cu` executable. On macOS, use `cu-cli` because macOS
includes an unrelated system command named `cu`.

### Shell conventions

PowerShell 7 on Windows is the primary shell for this guide. Linux users can
run the same one-line commands in Bash. Where the PowerShell syntax doesn't
work in Bash, the guide provides a separate Linux block immediately after the
Windows block.

The examples don't target Windows Command Prompt (`cmd.exe`) or Windows
PowerShell 5.1, whose quoting or file-encoding behavior differs. The guide
provides separate Windows and Linux blocks for commands that aren't portable.

Replace these uppercase placeholders before running a command:

- `RESOURCE_NAME`: Microsoft Foundry resource name.
- `SOURCE_ANALYZER_ID`: existing `2025-11-01` analyzer ID.
- `PREVIEW_ANALYZER_ID`: ID to create under `2026-06-01-preview`.
- `sample.pdf`: representative local input file.

Use the source ID as `PREVIEW_ANALYZER_ID` to keep the same name across API
versions. You can use a new custom analyzer ID for an isolated test, but it
isn't required.

You can use the toolkit's
[sample invoice](https://github.com/Azure/content-understanding-toolkit/blob/main/cu-cli/sample_files/sample_invoice.pdf)
if you don't have a representative file. On Windows using PowerShell 7,
download it as `sample.pdf` with:

```powershell
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/Azure/content-understanding-toolkit/main/cu-cli/sample_files/sample_invoice.pdf" -OutFile "sample.pdf"
```

On Linux Bash, use `curl`:

```bash
curl --fail --show-error --location "https://raw.githubusercontent.com/Azure/content-understanding-toolkit/main/cu-cli/sample_files/sample_invoice.pdf" --output sample.pdf
```

## Configure a CU CLI profile

This guide assumes that you already have a working Microsoft Foundry resource
in a [supported Content Understanding region](https://learn.microsoft.com/azure/ai-services/content-understanding/language-region-support).
It also assumes that the resource has completion and embedding model
deployments supported by both API versions and that the corresponding Content
Understanding defaults are configured. See
[supported generative models](https://learn.microsoft.com/azure/ai-services/content-understanding/service-limits#supported-generative-models)
and [Appendix: Troubleshoot model deployments and defaults](#appendix-troubleshoot-model-deployments-and-defaults)
if the readiness checks fail.

A CU CLI profile is local CU CLI configuration, not an Azure or Content
Understanding service resource. It saves values such as the endpoint,
authentication mode, API version, default analyzer, and model deployment
mappings so you don't need to repeat them on every command.

If you already have a working profile for the intended resource, continue using
it and skip the first-time configuration commands below. Confirm the active
profile with `cu profile show` and its readiness with `cu doctor`. To use an
existing named profile, select it with `cu profile set-active PROFILE_NAME`
before running the migration. Service commands also accept a
`--profile PROFILE_NAME` override without changing the active profile.

For first-time CU CLI users, configure the built-in `default` profile:

```powershell
az login

cu profile set endpoint https://RESOURCE_NAME.services.ai.azure.com/
cu profile set auth_mode login
cu profile set api_version 2025-11-01

cu profile show
cu defaults show
cu doctor
```

Model mappings shown by `cu profile show` are local profile settings. Run
`cu defaults show` and `cu doctor` to verify that the selected resource
also has the required deployments and resource-level defaults.

Command-line options override the selected profile for one invocation. For
example, this command doesn't change the saved profile:

```powershell
cu analyzer list --endpoint https://RESOURCE_NAME.services.ai.azure.com/ --auth-mode login --api-version 2026-06-01-preview
```

You can similarly use `--api-key`, `--profile`, and other command-specific
options. The migration commands below pass `--api-version` explicitly so it is
always clear which analyzer registration is being accessed.

## Migrate an existing analyzer

Analyzer registrations are API-version-specific. A GA analyzer and a preview
analyzer can use the same ID in the same resource. They are selected by the
`api-version` used for the create, list, show, analyze, and delete operations.

### 1. Save a GA baseline

For a manual check, list the GA custom analyzers. Find
`SOURCE_ANALYZER_ID` in the output and confirm that its status is `ready`:

```powershell
cu analyzer list --kind custom --api-version 2025-11-01
```

To automate the check with `jq`, run:

```powershell
cu analyzer list --kind custom --json --api-version 2025-11-01 | jq -e --arg id "SOURCE_ANALYZER_ID" 'any(.[]; .analyzerId == $id and .status == "ready")'
```

Analyze a representative file and save the complete GA result:

CU CLI doesn't overwrite an existing result file by default. If
`result-2025.json` already exists, archive or delete it, choose a new output
filename, or add `--on-existing reanalyze` to submit and bill a new analysis.
Don't use `--on-existing skip` when you need a fresh migration baseline. The
same behavior applies to the preview and rollback result files later in this
guide.

```powershell
cu analyze sample.pdf --analyzer SOURCE_ANALYZER_ID --json --output-file result-2025.json --api-version 2025-11-01
```

### 2. Export the live definition

Export the analyzer directly from the service. Do not substitute an older
local schema file:

```powershell
cu analyzer show SOURCE_ANALYZER_ID --api-version 2025-11-01 > analyzer-service-2025.json
```

Keep an unchanged copy of this service export as the GA backup.

### 3. Inspect the schema and model readiness

Open `analyzer-service-2025.json` and confirm that it describes the intended
analyzer. This guide applies only when the definition doesn't contain
`knowledgeSources`. Review the field names, types, methods, descriptions, and
enums under `fieldSchema.fields`.

Also inspect `models.completion` and `models.embedding`, which identify the
models selected by the analyzer. The abbreviated example below shows where to
look; the actual export contains the complete field schema and other service
properties:

```jsonc
{
  "analyzerId": "SOURCE_ANALYZER_ID",
  "fieldSchema": {
    "fields": {
      "invoiceTotal": {
        "type": "number",
        "method": "extract",
        "description": "Total amount due on the invoice."
      }
    }
  },
  "models": {
    // Check current model support and retirement dates. Migrate gpt-4.1 to a
    // supported model such as gpt-5.2 before creating the preview analyzer.
    "completion": "gpt-4.1",
    "embedding": "text-embedding-3-large"
  }
}
```

Model availability and retirement dates change over time. Check the
[supported generative models](https://learn.microsoft.com/azure/ai-services/content-understanding/service-limits#supported-generative-models)
and linked model retirement schedule rather than relying only on this example.
If the export selects `gpt-4.1`, deploy a supported replacement such as
`gpt-5.2`,
configure it as a Content Understanding default, and then change
`models.completion` in the migration file to `gpt-5.2`.

Content Understanding defaults are resource-level mappings from model names and
service aliases to deployment names. They let analyzers use the configured
models without requiring every API call to specify deployment names. The model
must be deployed before its default can be configured. Verify both API versions
before continuing:

```powershell
cu defaults show --api-version 2025-11-01
cu defaults show --api-version 2026-06-01-preview
cu doctor --api-version 2025-11-01
cu doctor --api-version 2026-06-01-preview
```

If the replacement deployment or defaults are missing, follow
[Troubleshoot model deployments and defaults](#appendix-troubleshoot-model-deployments-and-defaults)
to inspect deployments and configure mappings. Do not create the preview
analyzer until `cu doctor` succeeds for both API versions.

After completing the inspection and any required model update, validate the
migration file for the preview API:

```powershell
cu analyzer validate analyzer-service-2025.json --api-version 2026-06-01-preview
```

### 4. Verify that the preview ID is available

For a manual check, list the preview custom analyzers and confirm that
`PREVIEW_ANALYZER_ID` doesn't appear:

```powershell
cu analyzer list --kind custom --api-version 2026-06-01-preview
```

To automate the availability check with `jq`, run:

```powershell
cu analyzer list --kind custom --json --api-version 2026-06-01-preview | jq -e --arg id "PREVIEW_ANALYZER_ID" 'all(.[]; .analyzerId != $id)'
```

The command prints `true` and exits with status `0` when the ID is available.
If it prints `false` and exits with status `1`, stop before creating. Inspect
the existing preview analyzer, choose a new test ID, or intentionally delete
only that preview registration before retrying.

### 5. Create the preview registration

Create the preview analyzer from the live GA service export. Do not delete the
GA analyzer. Use the inspected and validated migration file from the previous
steps.

```powershell
cu analyzer create PREVIEW_ANALYZER_ID --schema analyzer-service-2025.json --api-version 2026-06-01-preview
```

### 6. Confirm both registrations

For a manual check, list the preview custom analyzers. Find
`PREVIEW_ANALYZER_ID` and confirm that its status is `ready`:

```powershell
cu analyzer list --kind custom --api-version 2026-06-01-preview
```

Then list the GA custom analyzers. Find `SOURCE_ANALYZER_ID` and confirm that
it remains `ready`:

```powershell
cu analyzer list --kind custom --api-version 2025-11-01
```

To automate both checks with `jq`, run:

```powershell
cu analyzer list --kind custom --json --api-version 2026-06-01-preview | jq -e --arg id "PREVIEW_ANALYZER_ID" 'any(.[]; .analyzerId == $id and .status == "ready")'
cu analyzer list --kind custom --json --api-version 2025-11-01 | jq -e --arg id "SOURCE_ANALYZER_ID" 'any(.[]; .analyzerId == $id and .status == "ready")'
```

The API version isn't returned as an analyzer property. The explicit
`--api-version` selects the corresponding analyzer registration.

### 7. Analyze with the preview registration

You can pass the preview API version per command without changing the default
profile:

```powershell
cu analyze sample.pdf --analyzer PREVIEW_ANALYZER_ID --json --output-file result-2026.json --api-version 2026-06-01-preview
```

## Compare the results

A byte-for-byte comparison of the complete responses is not expected to pass.
The responses contain operation IDs, timestamps, API versions, preview
diagnostic information, confidence values, and grounding. The preview service
also resolves `config.workflow` to a versioned value such as
`standard.2026-06-01-preview`.

First, manually open `result-2025.json` and `result-2026.json` in a text editor.
Confirm that each top-level `status` is `Succeeded`. Then compare
`result.contents` in both files, focusing on Markdown, field names, field
types, and field values while disregarding the expected metadata differences
described above.

To automate the success checks with `jq`, run:

```powershell
jq -e '.status == "Succeeded"' result-2025.json
jq -e '.status == "Succeeded"' result-2026.json
```

To automate the content comparison with `jq`, normalize confidence and
grounding while retaining Markdown, field structure, types, and values:

```powershell
jq -S '[.result.contents[] | {path, markdown, fields: (.fields | walk(if type == "object" then del(.confidence, .source, .spans) else . end))}]' result-2025.json > normalized-2025.json
jq -S '[.result.contents[] | {path, markdown, fields: (.fields | walk(if type == "object" then del(.confidence, .source, .spans) else . end))}]' result-2026.json > normalized-2026.json
jq -s -e '.[0] == .[1]' normalized-2025.json normalized-2026.json
```

The last command prints `true` and exits with status `0` when the Markdown,
field structure, field types, and field values are identical after removing
confidence and grounding. It prints `false` and exits with status `1` when
differences remain. In that case:

1. Confirm that the same input file and live service-exported analyzer
   definition were used.
2. Separate changes in extracted business values from changes in confidence,
   grounding, timestamps, diagnostics, and API metadata.
3. Re-run ambiguous or generative fields to distinguish normal model variation
   from an API-version behavior change.
4. Test a representative document set before moving production traffic.

After comparing the results, you can optionally make preview the default for
subsequent CU CLI commands. This changes the selected profile until you change
it again:

```powershell
cu profile set api_version 2026-06-01-preview
cu profile show
cu doctor
```

When you finish preview testing, restore the profile's previous API version.
For the profile configured in this guide, run:

```powershell
cu profile set api_version 2025-11-01
```

## Roll back

Because the GA analyzer remains registered separately, switching analysis back
to the GA API doesn't require recreating the analyzer:

```powershell
cu analyze sample.pdf --analyzer SOURCE_ANALYZER_ID --json --output-file rollback-check.json --api-version 2025-11-01
```

Compare the rollback check with the saved GA baseline before restoring
production traffic.

After validation, you can remove only the preview registration without
affecting the GA registration:

```powershell
cu analyzer delete PREVIEW_ANALYZER_ID --yes --api-version 2026-06-01-preview
```

If you changed the selected profile to the preview API, restore its previous
API version as described above. If an application was switched to the preview
API, restore its API-version configuration before returning production traffic
to the GA analyzer.

Keep the original service export as a backup in case the GA registration is
changed or deleted separately.

## Related documentation

- [CU CLI README](../../README.md)
- [Create a custom analyzer](https://learn.microsoft.com/azure/ai-services/content-understanding/tutorial/create-custom-analyzer)
- [What's new in Content Understanding](https://learn.microsoft.com/azure/ai-services/content-understanding/whats-new)
- [Content Understanding service limits](https://learn.microsoft.com/azure/ai-services/content-understanding/service-limits)

## Appendix: Troubleshoot model deployments and defaults

The migration steps assume that custom analyzers already work with both API
versions. If creation, schema suggestion, or analysis fails, use CU CLI to
separate profile, authentication, service-default, and deployment problems.

### 1. Verify the selected resource and authentication

```powershell
cu profile show
cu doctor --api-version 2025-11-01
cu doctor --api-version 2026-06-01-preview
```

Confirm that:

- `endpoint` is the intended Microsoft Foundry resource.
- `auth_mode` is `login`, or a valid API key is configured.
- Both API versions are supported by the installed CU CLI.
- The signed-in identity has `Cognitive Services User` access.

Run `az login` again if Microsoft Entra authentication has expired.

### 2. Compare local mappings with resource defaults

```powershell
# Local mappings saved in the default CU CLI profile.
cu profile show

# Resource-level Content Understanding defaults.
cu defaults show --api-version 2025-11-01
cu defaults show --api-version 2026-06-01-preview
```

Mappings displayed by `profile show` are local configuration. They don't prove
that the selected resource contains those deployments or resource-level
defaults. `defaults show` reads the selected resource directly.

### 3. Configure missing resource defaults

If the supported completion and embedding deployments already exist, map each
model name to its deployment name:

```powershell
cu defaults set --model COMPLETION_MODEL=COMPLETION_DEPLOYMENT --model EMBEDDING_MODEL=EMBEDDING_DEPLOYMENT --api-version 2025-11-01
cu profile sync-defaults
cu doctor --api-version 2025-11-01
cu doctor --api-version 2026-06-01-preview
```

For example, if the deployments use descriptive names:

```powershell
cu defaults set --model gpt-5.2=my-gpt-5.2-deployment --model text-embedding-3-large=my-text-embedding-3-large-deployment --api-version 2025-11-01
```

CU CLI derives the required prebuilt analyzer aliases from supported model
mappings. Run `cu defaults show` afterward to confirm the aliases and
deployments.

If the correct mappings are already saved locally, review them with
`cu profile show`, then use:

```powershell
cu doctor --fix-defaults --api-version 2025-11-01
```

### 4. Diagnose missing or unavailable deployments

`cu doctor` reports when custom analyzers need a completion model, an
embedding model, or Content Understanding defaults. If the deployments
themselves are missing, unavailable in the resource's region, or out of quota,
deploy supported models before retrying the defaults commands.

For provisioning and repair guidance, see:

- [CU CLI Microsoft Foundry provisioning guide](../provisioning.md)
- [Content Understanding supported generative models](https://learn.microsoft.com/azure/ai-services/content-understanding/service-limits#supported-generative-models)
- [Connect analyzers to Foundry model deployments](https://learn.microsoft.com/azure/ai-services/content-understanding/concepts/models-deployments)
- [Content Understanding region support](https://learn.microsoft.com/azure/ai-services/content-understanding/language-region-support)

## Appendix: What was verified

The documented migration was tested end to end with CU CLI `0.1.0b3` by using
two schema-only analyzers:

1. An analyzer generated from the CU CLI starter template.
2. An analyzer whose schema was suggested from a representative invoice PDF.

For each analyzer, the verification:

1. Created the analyzer through `2025-11-01`.
2. Confirmed that it was listed as `ready` through the GA API.
3. Analyzed the same PDF and saved the complete result.
4. Exported the live definition with `cu analyzer show`.
5. Validated that service export for `2026-06-01-preview`.
6. Created the same analyzer ID through the preview API without deleting the
   GA registration.
7. Confirmed that the ID was listed as `ready` through both API versions.
8. Analyzed the same PDF through the preview API.
9. Deleted only the preview registration and confirmed that the GA registration
   remained ready.

The preview creation was also repeated with a different test ID from the GA
analyzer. Both naming approaches succeeded.

The live GA service exports were accepted directly as preview create inputs. No
properties had to be removed or rewritten.

The suggested-schema analyzer returned identical Markdown, field names, field
types, and field values after confidence and grounding were removed from the
comparison. The generic starter template returned identical Markdown and field
names, but some generated values changed because its fields intentionally
contain ambiguous `TODO` descriptions. Confidence values can also change
between runs.

These results demonstrate the migration mechanics, not analyzer accuracy.
Use production field descriptions and a representative document set when
validating a customer analyzer.
