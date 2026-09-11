Release History
===============

0.1.0b1 (2026-09-11)
+++++++++++++++++++++

* Add the preview ``az cu analyzer list`` vertical slice.
* Add analyzer show, create, and delete commands.
* Add single-file analysis and defaults show/set commands.
* Use the active Azure CLI login and subscription for Microsoft Entra authentication.
* Reuse CU CLI core profiles, analyzer operations, structured errors, and serialization.
* Add schema validation and creation, analyzer tests, URL/SAS and directory/batch analysis.
* Add profile management with atomic updates and secret redaction.
* Add host-context analyzer copy, structured doctor checks, and safe environment-variable listing.
* Add ``az cu infra generate`` with Azure CLI-native subscription and wizard behavior.
* Generate the canonical azd/Bicep project supplied by ``cu-cli-core`` and use
  an internal ``az cu`` post-provision model helper.
* Generate command and argument registration from the shared ``cu-cli-core``
	command specifications while omitting direct provisioning and self-upgrade.
