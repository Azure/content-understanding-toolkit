# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Click-free, reusable business logic for the CU CLI.

Modules under ``cu_cli.core`` contain reusable work behind commands: the
concurrent analyze engine, analyzer CRUD, schema authoring, service defaults,
doctor checks, and infrastructure-generation helpers. Shared input discovery
and output planning live in ``cu_cli_core.input_planning``.

The boundary rule: functions here accept an already-built SDK ``client`` and/or
plain parameters and return data or typed result objects. They never call
``console.print``, ``sys.exit``, ``click.confirm``, or ``click.prompt`` — all
presentation, prompting, and exit-code handling lives in ``cu_cli.commands``.
This keeps the logic independently testable and reusable from other tools.
"""

from __future__ import annotations
