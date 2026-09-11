Release History
===============

0.1.0b1 (2026-09-11)
+++++++++++++++++++++

* Introduce the preview ``az cu`` command group for Azure Content Understanding.
* Analyze local files, directories, and HTTPS or SAS URLs, with support for
	batch output, reports, dry runs, usage details, and LLM-ready output.
* List, inspect, create, delete, validate, test, and copy analyzers, and create
	analyzer schemas.
* Manage defaults and reusable profiles, with secret redaction in command output.
* Diagnose configuration and connectivity issues with ``az cu doctor`` and
	safely inspect relevant environment variables.
* Generate azd and Bicep projects for new or existing Foundry resources with
	guided subscription, region, model, and RBAC configuration.
* Use the active Azure CLI login, cloud, and subscription, and support standard
	Azure CLI output formats, JMESPath queries, and confirmation behavior.
