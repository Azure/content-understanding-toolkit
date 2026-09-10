# Azure Content Understanding starter

This infrastructure-only Azure Developer CLI (`azd`) project provisions a Microsoft Foundry resource and project for Azure Content Understanding. It can optionally deploy supported language and embeddings models and configure Content Understanding defaults.

The generated hook runs the internal `az cu _infra-models` helper, so keep Azure CLI and the `content-understanding` extension on `PATH` when running `azd up`. Model setup failures stop the hook and can be retried with `azd up`; layout, read, and digital parsing remain available without optional models.

## Run

```sh
azd up
```

The identity running `azd up` needs Contributor or Owner at subscription scope. Role assignment also requires Role Based Access Control Administrator, User Access Administrator, or Owner. Set `AZD_ASSIGN_ROLES` to `false` to skip role assignment; the post-provision helper can use a resource key for setup, but later `az cu` commands still require existing data-plane access.

## Configure an existing resource

Set `FOUNDRY_EXISTING_ENDPOINT` and `FOUNDRY_EXISTING_RESOURCE_GROUP` before running `azd up` to reuse an existing Microsoft Foundry resource.

## Model selection

Set `CU_MODEL_SELECTION` to `recommended`, `none`, `prompt`, or explicit `model@version` selectors. Without optional models, `prebuilt-digitalParse`, `prebuilt-read`, and `prebuilt-layout` remain available.

## Profile setup

After provisioning, the hook configures the shared default CU profile. Equivalent manual commands include:

```sh
az cu profile set --key endpoint --value <FOUNDRY_ENDPOINT>
az cu profile set --key default_analyzer --value prebuilt-layout
az cu doctor
az cu analyze <file> --analyzer prebuilt-layout
```

Existing profile values are preserved. To replace them, regenerate the project with `az cu infra generate --force`, then run `azd up` again. Set `CU_DISABLE_AUTO_PROFILE_SETUP=true` to disable automatic profile setup.

## Cleanup

```sh
azd down --purge
```
