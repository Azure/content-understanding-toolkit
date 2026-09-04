# Provision Microsoft Foundry for CU CLI

This is the authoritative guide to creating or reusing a Microsoft Foundry
resource for Content Understanding, deploying supported models, configuring
Content Understanding defaults, and connecting CU CLI.

## Understand what is required

Content Understanding is accessed through a Microsoft Foundry resource in a
[supported region](https://learn.microsoft.com/azure/ai-services/content-understanding/language-region-support#region-support).
This Azure resource is separate from a local CU CLI profile.

Operations that use generative AI require a supported large language model
(LLM) deployment for chat completion and an embeddings model deployment. A
model deployment makes a Foundry model available under a deployment name.
Content Understanding defaults map supported model names and prebuilt analyzer
model aliases to those deployment names, so requests do not need to supply the
mappings.

The `prebuilt-digitalParse`, `prebuilt-read`, and `prebuilt-layout` content
extraction analyzers do not require an LLM, embeddings model, or Content
Understanding model defaults. Other prebuilt analyzers and custom analyzers
require the deployments supported by that analyzer and configured defaults.

`cu infra generate` writes an azd/Bicep project. It performs control-plane
discovery but does not deploy resources or call the Content Understanding data
plane, and it does not create local analyzer schemas, samples, or agent
instructions. Run `azd up` from the generated `provision` directory to deploy.

## Sign in

Azure CLI and Azure Developer CLI maintain separate sessions. Sign in to both
before generating and deploying an azd project:

```bash
# Used for subscription discovery and existing-resource validation.
az login

# Used by the later azd up deployment.
azd auth login
```

Only `az login` is required when you are connecting CU CLI to an already-ready
resource and do not use `cu infra generate` or `azd up`.

## Azure permissions

The generated Bicep deploys at subscription scope for both new and existing
resource paths.

| Scenario | Required access |
| --- | --- |
| Create a new Microsoft Foundry resource **and automatically assign roles** | One of:<ul><li><strong>Owner</strong> on the selected subscription</li><li><strong>Contributor</strong> plus <strong>Role Based Access Control Administrator</strong> on the selected subscription</li><li><strong>Contributor</strong> plus <strong>User Access Administrator</strong> on the selected subscription</li></ul> |
| Create a new Microsoft Foundry resource **without assigning roles** | One of:<ul><li><strong>Contributor</strong> on the selected subscription</li><li><strong>Owner</strong> on the selected subscription</li><li>A custom role with equivalent permissions</li></ul>The identity needs permission to create the resource group, Foundry resource and project, and model deployments. With Contributor only, decline the role-assignment prompt; the generated post-provision step uses key authentication. |
| Deploy models to an existing Microsoft Foundry resource with the generated project | One of:<ul><li><strong>Contributor</strong> on the selected subscription</li><li>A narrower custom role with the required subscription deployment and resource actions</li></ul>The identity needs permission to run the subscription-scope deployment and create model deployments on the selected resource. This path creates no role assignments. |
| Use an existing resource with Microsoft Entra ID authentication | <ul><li><strong>Cognitive Services User</strong> on the Microsoft Foundry resource</li></ul>Contributor is not required and does not include this data-plane access. |
| Use an existing resource with key authentication | <ul><li>A valid resource key</li></ul>Contributor and Cognitive Services User are not required for key-authenticated requests. |

For a new resource, `azd up` can optionally assign **Cognitive Services User**
to the user or service principal running azd. This grants that principal
Entra-based data-plane access; it does not grant access to other identities.
The existing-resource path never creates role assignments.

For an existing resource, grant an Entra identity **Cognitive Services User**
through the resource's **Access control (IAM)** page. Without it,
Entra-authenticated commands such as `cu defaults set`, `cu analyzer create`,
and `cu analyze` fail with an authorization error.

See [Azure built-in privileged roles](https://learn.microsoft.com/azure/role-based-access-control/built-in-roles/privileged#contributor)
and [Cognitive Services User](https://learn.microsoft.com/azure/role-based-access-control/built-in-roles/ai-machine-learning#cognitive-services-user)
for current role definitions.

## Create a new Microsoft Foundry resource

Start with the interactive wizard:

```bash
cu infra generate
cd provision
azd up
```

In the new-resource path, `azd up` creates a resource group, a Microsoft Foundry
resource (an Azure AI Services account with kind `AIServices`), a Foundry
project, and any selected model deployments.

Choose a Content Understanding supported region. When `--models` is omitted in
an interactive terminal, the generated post-provision step asks you to select
from the live CU-supported model catalog during `azd up`, after the resource
exists.

The **azd environment name** identifies a deployment stack, not a CU CLI
profile. For an environment named `dev`, azd stores state under
`provision/.azure/dev/` and the template uses names such as resource group
`rg-dev` and Foundry project `proj-dev`. Separate environment names keep
deployment state separate.

For deterministic generation with recommended supported LLM and embeddings
models:

```bash
cu infra generate \
  --output-dir ./provision \
  --environment dev \
  --location <supported-region> \
  --models recommended
cd provision
azd up
```

To create the resource without deploying models:

```bash
cu infra generate --location <supported-region> --models none
cd provision
azd up
```

This model-free path is ready for `prebuilt-digitalParse`, `prebuilt-read`, and
`prebuilt-layout`. Deploy models and configure defaults before using LLM-based
prebuilt or custom analyzers.

Use `--foundry-prefix my-cu` to produce a globally unique resource name such as
`my-cu-<unique-suffix>`. Without it, the template uses
`aif-<unique-suffix>`. The environment name still controls resource group and
project names.

Successful generation prints the files and next commands. Regeneration in the
same directory preserves model selections and merges azd environment state.
Use `--force` only when you intend to regenerate managed files and permit
post-provision updates to an already populated default CU CLI profile.

## Deploy models and configure defaults

Model availability and quota vary by region. Check the current
[supported generative models](https://learn.microsoft.com/azure/ai-services/content-understanding/service-limits#supported-generative-models).

For a new resource, use the `--models recommended` new-resource command above,
provide exact model names, or omit `--models` for interactive selection.

When the resource already exists but supported deployments or defaults are
missing, reuse it:

```bash
cu infra generate \
  --foundry-endpoint https://<resource-name>.services.ai.azure.com/ \
  --models recommended
cd provision
azd up
```

This reuses the selected resource and resource group. It does not create
another resource group, Foundry resource, Foundry project, or role assignment.
It creates the selected model deployments on that resource. To request exact
models instead:

```bash
cu infra generate \
  --foundry-endpoint https://<resource-name>.services.ai.azure.com/ \
  --models gpt-5.2,text-embedding-3-large
cd provision
azd up
```

The live CU-supported catalog validates model names during `azd up`.
`--foundry-endpoint` and `--foundry-prefix` are mutually exclusive.

## Generated post-provision behavior

After `azd up`, the generated hook:

1. Optionally deploys selected supported LLM and embeddings models.
2. Configures Content Understanding defaults when model deployments exist.
3. Saves the endpoint, authentication, API version, `prebuilt-layout` default
   analyzer, and discovered model mappings in the `default` CU CLI profile.
4. Prints the redacted result of `cu profile show --name default`.
5. Prints only workflows supported by the verified state.

An optional model deployment or default-mapping failure does not make the
resource deployment itself unsuccessful. The hook still configures the default
profile, keeps model-free analyzers available, and prints a focused repair
action. Endpoint or authentication setup failures report incomplete setup and
return a nonzero status.

If the default profile already contains values, the hook preserves it unless
the project was generated with `--force`. Set
`CU_DISABLE_AUTO_PROFILE_SETUP=true` before `azd up` only when profile setup
must be skipped entirely.

Verify the generated state:

```bash
cu profile show --name default
cu doctor --profile default
```

## Configure an existing ready resource

If the resource, required deployments, and Content Understanding defaults
already exist, no infrastructure generation is needed. Configure the automatic
`default` profile with Entra authentication:

```bash
cu profile set endpoint https://<resource-name>.services.ai.azure.com/
cu profile set auth_mode login
az login
cu doctor
```

Or use key authentication:

```bash
cu profile set endpoint https://<resource-name>.services.ai.azure.com/
cu profile set api_key <key>
cu doctor
```

The key is redacted by `cu profile get` and `cu profile show`.

## Configure defaults manually

Use this path when supported LLM and embeddings deployments already exist but
the resource defaults are missing. Configure the profile and authentication as
shown above, then map each supported model name to its deployment name:

```bash
cu defaults set \
  --model gpt-5.2=my-gpt-52-deployment \
  --model text-embedding-3-large=my-embedding-deployment

# Copy resource defaults into the active local profile.
cu profile sync-defaults
cu doctor
```

Replace the examples with the model and deployment names on the resource.
`cu defaults set` configures resource-level Content Understanding defaults.
`cu profile sync-defaults` copies those mappings into the active local profile.
If mappings are already stored in the profile, review them with
`cu profile show`, then push them with `cu defaults set --from-profile`.

To save mappings locally before pushing them:

```bash
cu profile set model_deployments.gpt-5.2 my-gpt-52-deployment
cu profile set model_deployments.text-embedding-3-large my-embedding-deployment
cu defaults set --from-profile
```

For supported models, CU CLI also derives the service aliases used by prebuilt
analyzers. Completion deployments are mapped to
`prebuilt-analyzer-completion` and `prebuilt-analyzer-completion-mini`;
embeddings deployments are mapped to `prebuilt-analyzer-embedding`. You do not
need to enter those alias mappings separately.

`cu doctor --fix-defaults` can apply locally configured mappings after showing
the proposed state. Run `cu defaults show` to inspect resource defaults.

## Diagnose readiness

`cu doctor` checks the API version, endpoint, authentication, service
connectivity, and Content Understanding defaults. It exits nonzero when a
required check fails, so scripts and coding agents can use it as a readiness
gate. Check a named profile without activating it with
`cu doctor --profile NAME`.

Optional deployment failures can leave model-free analyzers ready while
LLM-based analyzers remain unavailable. Follow the focused repair command from
the post-provision hook, correct quota or model availability, and rerun
`cu doctor`.

## Further reading

- [Create a Microsoft Foundry resource](https://learn.microsoft.com/azure/ai-services/content-understanding/how-to/create-multi-service-resource)
- [Content Understanding regions and languages](https://learn.microsoft.com/azure/ai-services/content-understanding/language-region-support)
- [Supported generative models and service limits](https://learn.microsoft.com/azure/ai-services/content-understanding/service-limits)
- [Model deployment options for analyzers](https://learn.microsoft.com/azure/ai-services/content-understanding/concepts/models-deployments)
- [Content Understanding setup quickstart](https://learn.microsoft.com/azure/ai-services/content-understanding/quickstart/content-understanding-studio)
- [Secure communications](https://learn.microsoft.com/azure/ai-services/content-understanding/concepts/secure-communications)
