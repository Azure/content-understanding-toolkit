# CU CLI usage guide

This guide covers the preview `cu` standalone CLI. On macOS, substitute
`cu-cli` because the operating system already provides an unrelated `cu`
command. If you're new to Content Understanding, start with the
[main README](../README.md#content-understanding-concepts) for definitions of
files, analyzers, analyzer results, and Microsoft Foundry resources. See also
the official [Content Understanding terminology](https://learn.microsoft.com/azure/ai-services/content-understanding/glossary).

For installation, sign-in requirements, and setup paths for new or existing
Azure resources, follow
[Provision and configure Azure resources](../README.md#provision-and-configure-azure-resources)
in the main README. This guide builds on that setup with detailed profile
precedence, environment overrides, batch processing, analyzer management,
Content Understanding defaults, and troubleshooting workflows.

Content Understanding API version. Known versions: 2025-11-01 (GA) and
2026-06-01-preview (preview); any YYYY-MM-DD-preview version is also accepted.

## CU CLI profiles

A CU CLI profile is local CLI configuration containing the settings used to
access Content Understanding through one Microsoft Foundry resource. A profile
is a CU CLI concept, not a Content Understanding or Azure resource. It can
contain:

- `endpoint`
- `auth_mode` (`login` or `key`)
- `api_key` for key authentication
- `api_version`
- `default_analyzer`
- `model_deployments.<model>` mappings used to configure Content Understanding
  defaults

CU CLI always provides a virtual `default` profile. A fresh installation does
not require `cu profile create`; the first `cu profile set` command materializes
that profile. Create named profiles only when you need separate settings for
resources such as development and production.

### Resolution precedence

For normal service commands, CU CLI resolves each setting independently from
the highest available layer:

1. Explicit command options, such as `--endpoint` or `--api-key`.
2. Supported environment variables.
3. The selected CU CLI profile: `--profile NAME`, otherwise the active profile.
4. Shared base values in the `[cu]` Azure CLI configuration section, retained
   for compatibility with configurations created before named profiles.
5. Built-in defaults.

The first layer containing a value wins; layers are not all-or-nothing. For
example, an environment endpoint can override the selected profile's endpoint
while the API version still comes from that profile. CU CLI doesn't write
command or environment overrides back to the profile.

Suppose `dev` is active and `prod` has a different endpoint. Create both
profiles first so the commands below can run in sequence:

```bash
# Create dev and prod, then set a distinct endpoint on each.
cu profile create dev
cu profile set endpoint https://<dev-resource>.services.ai.azure.com/ --name dev
cu profile create prod
cu profile set endpoint https://<prod-resource>.services.ai.azure.com/ --name prod
cu profile set-active dev

# Uses all effective settings from the active dev profile.
cu analyzer list --info

# Uses prod for this command only; dev remains active.
cu analyzer list --profile prod

# Uses prod's remaining settings, but this endpoint wins for this invocation.
CU_ENDPOINT=https://<temporary-resource>.services.ai.azure.com/ \
  cu analyzer list --profile prod --info

# The explicit option wins over both CU_ENDPOINT and the selected profile.
CU_ENDPOINT=https://<temporary-resource>.services.ai.azure.com/ \
  cu analyzer list \
  --profile prod \
  --endpoint https://<one-time-resource>.services.ai.azure.com/ \
  --info
```

`--info` prints the resolved non-secret runtime context to standard error before
the operation. Use it to verify precedence without exposing an API key.

For example, `cu analyzer list --info` output begins with:

```text
endpoint: https://my-foundry-resource.services.ai.azure.com/
auth mode: entra
api-version: 2025-11-01
CU CLI profile: default
settings: ~/.azure/config
```

Here, `~` represents the current user's home directory; the settings path is
printed as an absolute path at runtime. It resolves to `$AZURE_CONFIG_DIR/config`
when `AZURE_CONFIG_DIR` is set.

### Storage

CU CLI profiles are stored in the Azure CLI configuration file:

- `$AZURE_CONFIG_DIR/config` when `AZURE_CONFIG_DIR` is set.
- `~/.azure/config` otherwise.

CU CLI owns only the `[cu]` section. Writes are atomic, preserve unrelated
Azure CLI sections and their settings, and set new configuration files to mode
`0600`. Unknown `[cu]` keys are preserved for forward compatibility.

### CU CLI profile commands

```bash
# Show all effective values for the active profile.
cu profile show

# Print only the effective endpoint from the active profile.
cu profile get endpoint

# List saved profiles and identify the active profile.
cu profile list

# Save the endpoint on the active profile.
cu profile set endpoint https://<resource-name>.services.ai.azure.com/

# Create an empty dev profile.
cu profile create dev

# Show dev without changing the active profile.
cu profile show --name dev

# Save an API version on dev without changing the active profile.
cu profile set api_version 2026-06-01-preview --name dev

# Save a key on dev, then remove it so the next lower precedence layer applies.
cu profile set api_key <key> --name dev
cu profile unset api_key --name dev

# Create test as an independent copy of dev.
cu profile copy dev test

# Rename test and its saved values to prod.
cu profile rename test prod

# Make dev the profile used when --profile is omitted.
cu profile set-active dev

# Delete the inactive prod profile; this doesn't delete an Azure resource.
cu profile delete prod
```

`show --name` is view-only and never changes the active CU CLI profile. The
active profile cannot be deleted; activate another profile first. `copy`
creates a separate profile, `rename` moves the profile and its saved values, and
`set-active` changes which CU CLI profile commands use when `--profile` is
omitted.

Profile names contain 1-64 ASCII letters or numbers and may contain internal
hyphens or underscores. The names `default` and `model_deployments` are reserved.

`api_key` is never printed. `get` and `show` display a redacted value.

### Authentication

Login authentication is the recommended default:

```bash
# Sign in for the default login authentication mode.
az login

# Login authentication is already the default; this profile command is optional.
# cu profile set auth_mode login
```

`az login` authenticates Azure CLI and does not modify CU CLI profile settings.

To use a resource key:

```bash
# Save a resource key on the active profile and select key authentication.
cu profile set api_key <key>
```

Setting an API key also selects key authentication. Unsetting the key returns
the CU CLI profile to login authentication:

```bash
# Remove the saved key and return this profile to login authentication.
cu profile unset api_key
```

Run `cu profile set api_key --help` for the current key-setting syntax. Treat a
literal key in a command as sensitive because the shell can save it in history.
For automation, inject `CU_API_KEY` through the environment using your
platform's secret facility and remove it when the process finishes. Profile
display and `--info` output redact the key.

### Environment overrides

Use environment variables for temporary or automated overrides rather than
rewriting a saved profile. List the exact variables supported by the installed
version:

```bash
# List set, recognized environment overrides in a table.
cu env-var list

# Emit the same set of overrides as machine-readable JSON.
cu env-var list --json
```

The JSON form returns an array of objects with each variable's `name`, redacted
`value`, and `scope`. It is useful for scripts that need to inspect active
overrides without parsing a rendered table or exposing `CU_API_KEY`.

For example:

```bash
# Temporarily override only the endpoint; other values still resolve normally.
export CU_ENDPOINT=https://<temporary-resource>.services.ai.azure.com/

# Use dev's other settings and print the effective runtime context.
cu analyzer list --profile dev --info

# Remove the override when the task is complete.
unset CU_ENDPOINT
```

Environment syntax differs by shell; in PowerShell, use
`$env:CU_ENDPOINT = "..."` and remove it with
`Remove-Item Env:CU_ENDPOINT`. Avoid persisting `CU_API_KEY` in shell startup
files. `cu profile sync-defaults` intentionally uses the endpoint saved in the
selected profile rather than `CU_ENDPOINT`, because synchronization updates
that profile's model mappings.

### Content Understanding defaults

Content Understanding operations that use generative AI require Foundry model
deployments, including a large language model (LLM) for chat completion and an
embeddings model. Content Understanding defaults connect model names and
prebuilt analyzer model aliases to deployment names so each analyze request
doesn't need to provide the mappings.

Import Content Understanding defaults into a CU CLI profile:

```bash
# Import remote defaults into the active CU CLI profile.
cu profile sync-defaults

# Import remote defaults into prod without changing the active profile.
cu profile sync-defaults --name prod
```

Synchronization always uses the endpoint saved in the selected CU CLI profile.
`CU_ENDPOINT` cannot redirect it to a different resource. Authentication can
still be overridden with `--auth-mode` or `--api-key`.

Set mappings manually in a CU CLI profile and apply them as Content
Understanding defaults:

```bash
# Replace my-gpt-52-deployment with the completion deployment name on your resource.
cu profile set model_deployments.gpt-5.2 my-gpt-52-deployment

# Replace my-embedding-deployment with your embeddings deployment name.
cu profile set model_deployments.text-embedding-3-large my-embedding-deployment

# Apply the active profile's local mappings as remote Content Understanding defaults.
cu defaults set --from-profile
```

When a profile contains supported model mappings, CU CLI also derives the
service aliases used by prebuilt analyzers. For example,
`my-gpt-52-deployment` is also mapped to
`prebuilt-analyzer-completion` and
`prebuilt-analyzer-completion-mini`, while
`my-embedding-deployment` is mapped to `prebuilt-analyzer-embedding`. This lets
prebuilt analyzers find the same deployments without requiring you to enter
those alias mappings separately.

These two stores serve different purposes:

- `cu profile set model_deployments...` changes local CU CLI configuration.
- `cu defaults set` changes remote Content Understanding defaults on the
  Microsoft Foundry resource.
- `cu profile sync-defaults` copies the remote defaults into a local profile.

See [Model deployment options for Content Understanding analyzers](https://learn.microsoft.com/azure/ai-services/content-understanding/concepts/models-deployments)
for the service concepts behind these mappings.

## Provisioning

`cu infra generate` is separate from analyzer authoring. It generates a deployable
azd/Bicep directory that provisions the required Microsoft Foundry resource. It
can also deploy selected supported LLMs and embeddings models, configure Content
Understanding defaults, and configure the default CU CLI profile. It never
creates Azure resources itself and never creates local schema, sample, or
agent-instruction files. `azd up` performs the Azure deployment.

### Required access and sign-in

The generated Bicep deploys at subscription scope. The required Azure role
depends on what that deployment performs:

- For the complete new-resource path, use **Contributor** or **Owner** on the
  selected subscription, or a custom role with equivalent permissions. This
  creates the resource group, Microsoft Foundry resource and project, and
  selected model deployments.
- Contributor can create and manage resources but cannot create Azure role
  assignments. To let the generated template also assign data-plane roles, add
  **Role Based Access Control Administrator** or **User Access Administrator**
  on the subscription, or use **Owner**. If you have Contributor only, answer
  `n` to the role-assignment prompt; the generated hook uses resource-key
  authentication instead.
- The existing-resource path still runs a subscription-scope deployment. It
  also needs permission on the existing resource to create any selected model
  deployments. Contributor on the selected subscription satisfies both
  requirements; an organization can instead provide a narrower custom role
  containing the required deployment and resource actions.

These management-plane roles are separate from Content Understanding data-plane
access. With Entra authentication, **Cognitive Services User** on the Microsoft
Foundry resource permits CU CLI to configure defaults and create, manage, and
run analyzers. Owner and Contributor do not include that data-plane access.

See [Azure built-in roles for AI and machine learning](https://learn.microsoft.com/azure/role-based-access-control/built-in-roles/ai-machine-learning#cognitive-services-user)
and [Azure built-in privileged roles](https://learn.microsoft.com/azure/role-based-access-control/built-in-roles/privileged#contributor)
for the current role definitions. Your organization can use equivalent custom
roles.

Before generation, run both sign-in commands because Azure CLI and azd maintain
separate sessions:

```bash
# Sign in for subscription discovery and existing-resource validation.
az login

# Sign in for the deployment performed later by azd up.
azd auth login
```

### Provision a new Microsoft Foundry resource interactively

Start with the interactive wizard when you are learning the workflow:

```bash
# Generate an azd template and answer the setup prompts.
cu infra generate
```

The wizard resembles this abbreviated session:

```text
cu infra generate -> /work/provision
  Azure subscription: My Azure Subscription (00000000-0000-0000-0000-000000000000)

`cu infra generate` generates an azd template ...
Enter your environment name ... [dev]: yslin-selfhost

Content Understanding supported regions
...
Azure region (where the Foundry resource is created) [eastus2]: westus3

Microsoft Foundry resource naming ...
Optional Microsoft Foundry resource name prefix ...: my-cu

RBAC roles: required for Entra-based auth from `cu` ...
Assign RBAC roles to your user on the Microsoft Foundry resource? [y/N]: n

wrote /work/provision
...
Next:
  cd provision
  azd auth login        (one-time)
  azd up
```

The **azd environment name** identifies one deployment stack; it is not a CU
CLI profile. For `yslin-selfhost`, azd stores deployment configuration and
outputs under `provision/.azure/yslin-selfhost/`. The generated template uses
the name in resources such as resource group `rg-yslin-selfhost` and Foundry
project `proj-yslin-selfhost`. Distinct names such as `dev`, `test`, and `prod`
keep their deployment state separate.

When `--models` is omitted in an interactive terminal, the generated
post-provision step asks you to select from the live CU-supported model catalog
during `azd up`, after the Microsoft Foundry resource exists.

### Provision a new resource without model deployments

Start here when you need only content extraction and want to avoid optional
model deployment:

```bash
# Generate a new-resource template with no LLM or embeddings deployment.
cu infra generate --models none

# Enter the generated azd project.
cd provision

# Create the Microsoft Foundry resource and configure the default CU CLI profile.
azd up
```

The `prebuilt-digitalParse`, `prebuilt-read`, and `prebuilt-layout` content
extraction analyzers don't require an LLM or embeddings model. Other prebuilt
analyzers and custom analyzers require their supported chat completion and
embeddings deployments plus Content Understanding defaults.

### Provision a new resource noninteractively

Supply every choice to make template generation deterministic:

```bash
# Generate under ./provision for the dev deployment stack in West US 3.
# The post-provision hook selects recommended CU-supported models during azd up.
cu infra generate \
  --output-dir ./provision \
  --environment dev \
  --location westus3 \
  --models recommended

# Enter the generated azd project.
cd provision

# Create the Azure resources, deploy models, and configure Content Understanding.
azd up
```

Successful generation prints the files it created and the next `cd` and
`azd up` commands. Re-running generation into the same directory preserves
model selections and merges azd environment state. Use `--force` only when you
intend to regenerate managed files and permit post-provision updates to an
already populated default CU CLI profile.

Check [Content Understanding region and language support](https://learn.microsoft.com/azure/ai-services/content-understanding/language-region-support)
for the current list of supported regions. The interactive provisioning wizard
also displays this link when selecting a region.

### Control generated resource names

Use `--foundry-prefix` to make a new resource easier to identify:

```bash
# Generate a resource name such as my-cu-<unique-suffix>.
cu infra generate --foundry-prefix my-cu --models none
```

The suffix makes the Microsoft Foundry resource name globally unique because
the name is part of its public endpoint. Without `--foundry-prefix`, the
template uses `aif-<unique-suffix>`. The environment name still controls the
resource group and project names, such as `rg-dev` and `proj-dev`.

### Provision LLM and embeddings models on an existing Microsoft Foundry resource

Use this path when the Microsoft Foundry resource already exists but its
CU-supported model deployments or Content Understanding defaults are missing:

```bash
# Verify the endpoint through Azure CLI and select recommended supported models.
cu infra generate \
  --foundry-endpoint https://my-foundry-resource.services.ai.azure.com/ \
  --models recommended

# Enter the generated azd project.
cd provision

# Deploy selected models and configure defaults on the existing resource.
azd up
```

This does not create another Microsoft Foundry resource. To request exact model
names instead of the recommended pair:

```bash
# Validate these names against the live CU-supported catalog during azd up.
cu infra generate \
  --foundry-endpoint https://my-foundry-resource.services.ai.azure.com/ \
  --models gpt-5.2,text-embedding-3-large

# Enter the generated azd project.
cd provision

# Deploy the requested models and configure Content Understanding defaults.
azd up
```

`--foundry-endpoint` and `--foundry-prefix` are mutually exclusive because one
selects an existing resource and the other names a new resource.

### Generated post-provision behavior

After `azd up`, the generated hook:

1. Optionally deploys the selected supported LLM and embeddings models.
2. Configures Content Understanding defaults when model deployments exist.
3. Saves the endpoint, authentication, API version, default analyzer, and
   discovered model deployment mappings in the default CU CLI profile.
4. Prints the redacted result of `cu profile show --name default`.
5. Prints only workflows supported by the verified state.

An optional model deployment or default-mapping failure does not make the
Microsoft Foundry resource deployment itself unsuccessful. The hook still
configures the default CU CLI profile, keeps `prebuilt-digitalParse`,
`prebuilt-read`, and `prebuilt-layout` available, and prints the exact repair
action. Endpoint or authentication configuration failures are reported as
incomplete setup and return a nonzero status.

A successful model-free run ends with output similar to:

```text
================================================================
 Microsoft Foundry resource provisioned
================================================================
  Resource group : rg-dev
  Account        : my-cu-<unique-suffix>
  Project        : proj-dev
  Endpoint       : https://my-cu-<unique-suffix>.services.ai.azure.com/

No model deployments selected.
Available without a large language model (LLM) or embeddings model:
prebuilt-digitalParse, prebuilt-read, prebuilt-layout
...
Setup complete.
Default CU CLI profile configured:
view only; active CU CLI profile remains: default
CU CLI profile: default
profile            default
endpoint           https://my-cu-<unique-suffix>.services.ai.azure.com/
auth_mode          key
api_key            ***redacted***
api_version        2025-11-01
default_analyzer   prebuilt-layout
model_deployments  {}

  Verify setup with:
    cu doctor
  Content extraction sanity check:
    cu analyze <file> --analyzer prebuilt-layout
```

The exact profile display can include additional redacted settings. A run that
deploys both model types also prints model readiness and custom-analyzer
commands. If an optional deployment fails, the hook identifies what remains
usable and prints a focused repair command instead of claiming full readiness.

Default CU CLI profile setup is automatic. If the default profile already has
saved values, the post-provision hook preserves it unless the template was
generated with `cu infra generate --force`; the hook reports whether it configured
or preserved the profile. Set
`CU_DISABLE_AUTO_PROFILE_SETUP=true` before `azd up` only when you want to skip
profile setup entirely.

After provisioning, confirm the saved state and service readiness:

```bash
# The hook already prints this redacted profile; run it again at any time.
cu profile show --name default

# Verify endpoint, authentication, connectivity, and model defaults.
cu doctor --profile default
```

## Analyze

An analyzer defines how Content Understanding processes a file. Analyze one file
with the `prebuilt-layout` content extraction analyzer:

```bash
# Analyze is a billed service call. Markdown is written to standard output.
cu analyze ./document.pdf --analyzer prebuilt-layout
```

By default, CU CLI formats the analyzer result as Markdown with the Content
Understanding SDK's `to_llm_input()` helper. Use `--json` for the complete
analyzer result as JSON or `--llm-input` to select the default Markdown view
explicitly.

Use the CU CLI profile's default analyzer:

```bash
# Save the default analyzer on the active profile.
cu profile set default_analyzer prebuilt-layout

# Analyze one file using the saved default analyzer.
cu analyze ./document.pdf
```

Analyze immediate files in a directory:

```bash
# Analyze only matching files directly inside ./documents.
cu analyze --source ./documents --pattern "*.pdf" --output-dir ./results
```

Directory input selects immediate files only. Add `--recursive` to include
nested directories:

```bash
# Quote the pattern so CU CLI, rather than the shell, applies it.
cu analyze --source ./documents \
  --recursive \
  --pattern "*.pdf" \
  --analyzer prebuilt-layout \
  --output-dir ./results
```

With `--output-dir`, CU CLI preserves each input path relative to the selected
source directory. For example:

```text
./documents/2026/invoice-01.pdf
  -> ./results/2026/invoice-01.pdf.result.md
```

JSON results use `.result.json` instead. With one input, omit `--output-dir` to
write the result to standard output or use `--output-file` to choose one file.
`--output-file` is rejected when more than one input is selected.

These single-file examples show the terminal and file-output forms:

```bash
# Print human-readable Markdown to the terminal.
cu analyze ./invoice.pdf --analyzer prebuilt-layout

# Print the complete structured result as JSON to the terminal.
cu analyze ./invoice.pdf --analyzer prebuilt-layout --json

# Save Markdown instead of printing it; parent directories are created.
cu analyze ./invoice.pdf --analyzer prebuilt-layout \
  --output-file ./results/invoice.md

# Save structured JSON instead of printing it.
cu analyze ./invoice.pdf --analyzer prebuilt-layout \
  --json --output-file ./results/invoice.json
```

Markdown is the default output view. Use `--json` when you need the complete
service result. If analysis succeeds but the Markdown view has no displayable
content, CU CLI recommends `--json`.

### Preview and run a batch safely

Every non-dry-run analyze request is billed. Preview discovery, output paths,
and existing-file actions before a batch:

```bash
# Preview the discovered files and output mappings without service calls.
cu analyze --source ./documents \
  --recursive \
  --pattern "*.pdf" \
  --analyzer prebuilt-layout \
  --output-dir ./results \
  --dry-run
```

A dry run prints the selected file count, bytes and extensions, analyzer,
recursion mode, collision policy, and source-to-output mapping. It makes no
service calls and writes no result files. It cannot validate analyzer
existence, file contents, service-side format acceptance, usage, or cost.
Hidden files directly under a selected or visible directory are named and
counted as skipped. Files inside hidden directories and CU CLI's own
`*.result.md` and `*.result.json` files are excluded from discovery to avoid
infrastructure noise and accidental reanalysis.

After reviewing the selection, remove `--dry-run` to submit the files. For
noninteractive scripts, pass `--yes`; otherwise a large or costly batch can
request confirmation.

### Existing outputs and batch reports

`--on-existing` controls what happens when a result path already exists:

- `error` (default) reports the collision instead of replacing the result.
- `skip` leaves the existing result untouched and records it as skipped.
- `reanalyze` submits the input again and replaces the existing result.

Use `--report-file ./run-report.json` for a machine-readable record of each
input's status. A batch continues after an individual file failure, reports
successful, failed, and skipped inputs, and exits with status `1` if any input
failed. This lets automation keep good results while reporting files that need
attention.

```bash
# Analyze recursively, save one result per input, and record all statuses in JSON.
cu analyze ./documents \
  --recursive \
  --analyzer prebuilt-layout \
  --output-dir ./results \
  --report-file ./run-report.json \
  --yes
```

Useful options include:

- `--json` for the complete analyzer result as JSON.
- `--concurrency` or `-j` for the number of concurrent batch **jobs**. The
  default is `4`; the supported range is `1` through `32`.
- `--time` to print CU service and total command elapsed time.

For example:

```bash
# Process up to eight batch jobs concurrently instead of the default four.
cu analyze ./documents --analyzer prebuilt-layout --output-dir ./results -j 8

# Print service-call and total elapsed time after the analysis result.
cu analyze ./invoice.pdf --analyzer prebuilt-layout --time
```

`--time` output resembles:

```text
CU service calling time: 1.428s
Total command time: 1.612s
```

Timings vary by machine and request.

Run `cu analyze --help` for the complete input-selection and output contract.

## Analyzers

Prebuilt analyzers are ready-to-use analyzers supplied by Content Understanding.
A custom analyzer uses an analyzer schema to define processing and the
structured fields your application needs.

Custom analyzer IDs contain 1-64 ASCII letters, numbers, or underscores.
Hyphens are reserved for service-provided prebuilt analyzer IDs.

### Inspect and manage

```bash
# List analyzers available on the selected resource.
cu analyzer list

# Print one analyzer definition.
cu analyzer show invoice_v1

# Delete a custom analyzer after confirmation.
cu analyzer delete invoice_v1
```

### Create a schema

Generate a starter schema:

```bash
# Defaults to a document field-extraction schema.
cu analyzer schema create --output-file schema.json

# Generate an image field-extraction schema instead of the document default.
cu analyzer schema create --modality image --output-file image-schema.json

# Generate a classification schema instead of a field-extraction schema.
cu analyzer schema create \
  --type classification \
  --output-file classification-schema.json
```

Generate from a representative sample:

```bash
# Ask the service to draft a schema from one representative invoice.
cu analyzer schema create \
  --from-sample ./invoice.pdf \
  --output-file schema.json
```

Schema generation refuses to replace an existing output file. Choose another
path or pass `--force` when you intentionally want to overwrite it. Existing
outputs are checked before sample-derived generation calls the CU service.

Review generated schemas before deployment. Validate offline:

```bash
# Validate the local schema shape.
cu analyzer validate ./schema.json

# Also validate rules from the selected Content Understanding API specification.
cu analyzer validate ./schema.json --spec
```

A successful validation prints an `ok` result and makes no service call. Invalid
JSON, unsupported properties, and incompatible schema options return a nonzero
status with the failing location.

### Create and test

```bash
# Create a remote custom analyzer from the reviewed local schema.
cu analyzer create --name invoice_v1 --schema ./schema.json

# Test one sample and print the summary.
cu analyzer test invoice_v1 ./invoice.pdf

# Test every supported sample in a directory and save one aggregate JSON report.
cu analyzer test invoice_v1 ./samples \
  --json \
  --output-file ./test-report.json
```

Analyzer test reports preserve existing files by default and are checked before
any samples are sent to the CU service. Pass `--force` only when you
intentionally want to replace the selected report.

`cu analyzer test` summarizes whether fields and confidence values were
returned. It isn't an accuracy benchmark and doesn't compare results with
labeled ground truth. Use `cu analyze --analyzer invoice_v1 --json` when you
need the complete analyzer result.

### Copy across resources

Use CU CLI profile selectors for resources already configured in CU CLI:

```bash
# Copy one analyzer between resources represented by saved CU CLI profiles.
# --source is the existing analyzer ID on the dev resource.
# --destination is the analyzer ID to create on the prod resource.
# --source-profile supplies the source endpoint and authentication.
# --destination-profile supplies the destination endpoint and authentication.
cu analyzer copy \
  --source invoice_v1 \
  --destination invoice_v1 \
  --source-profile dev \
  --destination-profile prod
```

Use direct Azure resource selectors for discovery-based, login-authenticated
copy:

```bash
# Copy one analyzer using Azure resource discovery instead of saved profiles.
# --source is the existing analyzer ID on the source resource.
# --destination is the analyzer ID to create on the destination resource.
# --source-resource selects the source by name, endpoint, or ARM resource ID.
# --destination-resource selects the destination using the same identifier forms.
cu analyzer copy \
  --source invoice_v1 \
  --destination invoice_v1 \
  --source-resource <endpoint-resource-name-or-arm-id> \
  --destination-resource <endpoint-resource-name-or-arm-id>
```

Resource selectors support side-specific subscription and resource-group
options. For every copy, CU CLI resolves each effective endpoint through Azure
before making analyzer calls. `--source-subscription` and
`--destination-subscription` are authoritative when supplied; otherwise CU CLI
uses the active Azure CLI subscription. Discovery never searches other
subscriptions. Direct resource copy uses login authentication and does not
persist discovered endpoints into CU CLI profiles.

Azure resource discovery requires Reader access on each selected subscription
or resource group. Profile-backed data-plane calls continue to use the
CU CLI profile's configured authentication.

## Content Understanding defaults

```bash
# Show remote model-to-deployment mappings as JSON.
cu defaults show

# Show the same remote mappings as a human-readable table.
cu defaults show --table

# Replace my-gpt-52-deployment with a deployment name and set that mapping.
cu defaults set --model gpt-5.2=my-gpt-52-deployment

# Apply model mappings from the active CU CLI profile to the remote resource.
cu defaults set --from-profile
```

Content Understanding defaults map model names and prebuilt analyzer aliases to
deployment names on the Microsoft Foundry resource. `cu defaults` changes those
remote mappings; `cu profile` changes local connection and mapping settings.
`cu defaults set` requires an explicit source:
`--from-profile`, one or more `--model MODEL=DEPLOYMENT` options, or both. A
bare `cu defaults set` command fails before contacting the service.

## Diagnostics and environment

Run diagnostics after initial setup or when changing resources:

```bash
# Check the active profile.
cu doctor

# Check prod without changing the active profile.
cu doctor --profile prod

# Apply reviewed local model mappings as remote Content Understanding defaults.
cu doctor --fix-defaults
```

`cu doctor` checks the API version, endpoint, authentication, service
connectivity, and Content Understanding defaults. It exits nonzero when a
required check fails, so scripts can use it as a readiness gate. Review local
mappings with `cu profile show` before using `--fix-defaults`.

See [Environment overrides](#environment-overrides) for temporary configuration
and cleanup. Use `--info` on supported service commands when you need to inspect
their effective non-secret settings.

## Help and exit behavior

Every command has examples and supported-version information:

```bash
# List top-level command groups and global options.
cu --help

# Show how to save profile values, including supported keys and examples.
cu profile set --help

# Show profile-based and Azure-discovery analyzer copy options.
cu analyzer copy --help
```

Command-line usage errors return status `2`. Operational and validation
failures return a nonzero status with an actionable CU CLI error rather than a
Python traceback. Batch analyze returns status `1` after reporting any
per-input failures. Successful commands return status `0`.
