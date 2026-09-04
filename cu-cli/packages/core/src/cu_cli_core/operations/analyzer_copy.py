# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Analyzer management service (Click-free, client-injected).

Thin wrappers over the CU SDK's analyzer CRUD that add the small pieces of
domain logic the CLI needs: stable sorting, custom-only filtering, treating a
create that lands in ``FAILED`` as an error, and treating a delete of a missing
analyzer as an error (server-side DELETE is idempotent, which otherwise makes a
typo look like a success). Callers pass a built client; nothing here prints.
"""

from __future__ import annotations

import shlex
from typing import Any

from ..errors import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    ServiceError,
    UsageError,
)


def get_copy_source_analyzer(client: Any, analyzer_id: str) -> Any:
    """Fetch a copy source with copy-specific 404 and auth guidance.

    The command layer also needs the source definition for cross-resource
    dependency preflight. Keeping the fetch and translation here ensures that
    both that path and :func:`copy_analyzer` surface the same actionable errors.
    """
    from azure.core.exceptions import HttpResponseError, ResourceNotFoundError

    try:
        return client.get_analyzer(analyzer_id)
    except ResourceNotFoundError as exc:
        raise NotFoundError(
            f"source analyzer '{analyzer_id}' was not found; nothing to copy.",
            hint="check the source ID with `cu analyzer list` on the source resource.",
        ) from exc
    except HttpResponseError as exc:
        if getattr(exc, "status_code", None) in (401, 403):
            raise AuthenticationError(
                "source analyzer lookup failed with an auth error on the source resource.",
                hint="the signed-in identity needs *Cognitive Services User* on the "
                     "**source** account. Run `az login` if needed.",
            ) from exc
        raise


def _target_cli_command(
    action: str,
    analyzer_id: str,
    *,
    cross_resource: bool,
    target_cli_options: str | None,
) -> str | None:
    """Build a destination-safe follow-up command, or ``None`` if it cannot be scoped."""
    if cross_resource and not target_cli_options:
        return None
    suffix = f" {target_cli_options.strip()}" if target_cli_options else ""
    return f"cu analyzer {action} {shlex.quote(analyzer_id)}{suffix}"


def _target_exists_error(
    target_analyzer_id: str,
    *,
    cross_resource: bool,
    target_cli_options: str | None,
) -> ConflictError:
    """Return the non-destructive collision error used by preflight and 409 handling."""
    delete_command = _target_cli_command(
        "delete",
        target_analyzer_id,
        cross_resource=cross_resource,
        target_cli_options=target_cli_options,
    )
    overwrite_hint = (
        f"If you really want to overwrite, delete it explicitly at the destination "
        f"with `{delete_command}`, then re-run copy."
        if delete_command
        else "If you really want to overwrite, explicitly delete it at the destination "
             "resource, then re-run copy."
    )
    return ConflictError(
        f"destination analyzer '{target_analyzer_id}' already exists.",
        hint=f"Content Understanding has no in-place replace. Prefer a versioned "
             f"destination name (for example `{target_analyzer_id}_v2`) so the old copy "
             f"stays available for validation. {overwrite_hint}",
    )


def copy_analyzer(
    client: Any,
    source_analyzer_id: str,
    target_analyzer_id: str,
    *,
    target_client: Any = None,
    source_azure_resource_id: str | None = None,
    source_region: str | None = None,
    target_azure_resource_id: str | None = None,
    target_region: str | None = None,
    progress: Any = None,
    source_analyzer: Any = None,
    target_cli_options: str | None = None,
) -> Any:
    """Copy an analyzer, same-resource or cross-resource.

    **Same-resource** (default): only ``client`` is provided. The call goes to
    ``client.begin_copy_analyzer(analyzer_id=TARGET, source_analyzer_id=SOURCE)``
    and the service defaults source coordinates to the current resource.

    **Cross-resource**: ``target_client`` is a second SDK client bound to the
    destination resource, and the four ARM-ID + region args identify the two
    resources canonically. Orchestration:

    1. ``client.grant_copy_authorization(analyzer_id=SOURCE,
       target_azure_resource_id=<destination ARM>,
       target_region=<destination region>)``
       on the *source* client.
    2. ``target_client.begin_copy_analyzer(analyzer_id=TARGET,
       source_analyzer_id=SOURCE, source_azure_resource_id=<source ARM>,
       source_region=<source region>)`` on the *destination* client.

    The authorization record is destination-scoped, time-limited, and never printed
    or persisted — the service stores the grant server-side. The optional
    ``progress`` callable, if supplied, is invoked with a one-line status
    string before each data-plane call so callers can render live progress
    without this module depending on ``rich``.

    ``source_analyzer`` may carry the definition already fetched by the command
    layer's dependency preflight, avoiding a duplicate source request.
    ``target_cli_options`` contains non-secret CLI options that qualify recovery
    commands to the destination (for example ``--profile prod`` or
    ``--endpoint https://... --auth-mode login``).

    Raises a typed core error on 404 or when the destination exists;
    Content Understanding has no in-place replace. Also raises when the LRO
    lands in ``FAILED`` or when authorization expires before the copy completes.
    """
    from azure.core.exceptions import HttpResponseError, ResourceNotFoundError

    cross_resource = target_client is not None and target_client is not client
    copier = target_client if cross_resource else client

    if cross_resource and not (
        source_azure_resource_id
        and source_region
        and target_azure_resource_id
        and target_region
    ):
        raise UsageError(
            "cross-resource copy requires source and destination Azure resource IDs and regions.",
            hint="this is an internal error — the CLI should have resolved them "
                 "via --source-resource/--destination-resource before calling copy_analyzer.",
        )

    # 1. Confirm the source exists up-front. The service returns 400
    #    (InvalidRequest) rather than 404 on a missing source_analyzer_id,
    #    which is harder to interpret than an explicit lookup. The command
    #    layer may already have fetched it for dependency inspection.
    if source_analyzer is None:
        if progress is not None:
            progress(f"checking source analyzer '{source_analyzer_id}'")
        source_analyzer = get_copy_source_analyzer(client, source_analyzer_id)

    # 2. Confirm the destination is absent *before* granting authorization. This is
    #    both safer and more actionable than waiting for begin_copy_analyzer to
    #    return 409. Keep the 409 handler below for races between this lookup
    #    and LRO creation.
    if progress is not None:
        progress(f"checking destination analyzer '{target_analyzer_id}'")
    try:
        copier.get_analyzer(target_analyzer_id)
    except ResourceNotFoundError:
        pass
    except HttpResponseError as exc:
        status = getattr(exc, "status_code", None)
        if status == 404:
            pass
        elif status in (401, 403):
            raise AuthenticationError(
                "destination analyzer lookup failed with an auth error "
                "on the destination resource.",
                hint="the signed-in identity needs *Cognitive Services User* on the "
                     "**destination** account. Run `az login` if needed.",
            ) from exc
        else:
            raise
    else:
        raise _target_exists_error(
            target_analyzer_id,
            cross_resource=cross_resource,
            target_cli_options=target_cli_options,
        )

    # 3. Cross-resource: grant destination-scoped authorization first, so the
    #    subsequent begin_copy_analyzer at the destination can pull the source.
    if cross_resource:
        if progress is not None:
            progress("granting temporary copy authorization for the cross-resource copy")
        try:
            client.grant_copy_authorization(
                analyzer_id=source_analyzer_id,
                target_azure_resource_id=target_azure_resource_id,
                target_region=target_region,
            )
        except HttpResponseError as exc:
            status = getattr(exc, "status_code", None)
            if status in (401, 403):
                raise AuthenticationError(
                    "grant_copy_authorization failed with an auth error on the source resource.",
                    hint="the signed-in identity needs *Cognitive Services User* on the "
                         "**source** account. Run `az login` if needed.",
                ) from exc
            raise
        # Note: we do *not* print the returned CopyAuthorization record
        # (source, target_azure_resource_id, expires_at). The service stores
        # the grant server-side for the target's subsequent copy request.

    # 4. Start the copy LRO on the destination client and wait.
    copy_kwargs: dict[str, Any] = {
        "analyzer_id": target_analyzer_id,
        "source_analyzer_id": source_analyzer_id,
    }
    if cross_resource:
        copy_kwargs["source_azure_resource_id"] = source_azure_resource_id
        copy_kwargs["source_region"] = source_region
    if progress is not None:
        target_suffix = " on the destination resource" if cross_resource else ""
        progress(
            f"copying '{source_analyzer_id}' -> '{target_analyzer_id}'"
            f"{target_suffix}; this may take several minutes"
        )

    try:
        poller = copier.begin_copy_analyzer(**copy_kwargs)
        result = poller.result()
    except HttpResponseError as exc:
        status = getattr(exc, "status_code", None)
        if status == 409:
            raise _target_exists_error(
                target_analyzer_id,
                cross_resource=cross_resource,
                target_cli_options=target_cli_options,
            ) from exc
        if cross_resource and status in (401, 403):
            raise AuthenticationError(
                "copy failed with an auth error on the destination resource.",
                hint="the signed-in identity needs *Cognitive Services User* on the "
                "**destination** account. If authorization has expired between grant "
                "and copy, simply re-run — the CLI grants a fresh one each call.",
            ) from exc
        raise

    # 5. If the copy landed in a terminal FAILED state, treat like create_analyzer.
    final_id = getattr(result, "analyzer_id", target_analyzer_id)
    status = getattr(result, "status", None)
    if status and str(status).lower().endswith("failed"):
        show_command = _target_cli_command(
            "show",
            final_id,
            cross_resource=cross_resource,
            target_cli_options=target_cli_options,
        )
        raise ServiceError(
            f"analyzer '{final_id}' was copied but its status is FAILED.",
            hint=(f"run `{show_command}` for details."
                  if show_command
                  else "inspect the analyzer explicitly at the destination for details."),
        )
    return result


def collect_custom_dependencies(source_analyzer: Any) -> list[str]:
    """Return the list of *custom* analyzer IDs referenced by classifier / segmentation categories.

    Walks ``source.config.content_categories`` (the SDK models this as a mapping
    from category name to ``ContentCategoryDefinition``; list-shaped payloads
    are accepted for compatibility). Each definition may reference another
    analyzer via ``analyzer_id``. Prebuilt refs
    (``prebuilt-<something>``) are skipped—the destination has the same
    prebuilt catalog. Only *custom* refs need to exist at the destination before
    the parent analyzer can be copied.

    Returns an empty list when the analyzer has no categories or no refs.
    """
    result: list[str] = []
    cfg = getattr(source_analyzer, "config", None)
    if cfg is None:
        return result
    categories = getattr(cfg, "content_categories", None) or {}
    category_definitions = categories.values() if isinstance(categories, dict) else categories
    for cat in category_definitions:
        aid = getattr(cat, "analyzer_id", None) or (cat.get("analyzer_id") if isinstance(cat, dict) else None)
        if not aid:
            continue
        if aid.startswith("prebuilt-"):
            continue
        if aid not in result:
            result.append(aid)
    return result


def preflight_dependencies_on_target(
    target_client: Any,
    dependencies: list[str],
) -> list[str]:
    """Return the subset of ``dependencies`` that are missing on ``target_client``.

    Empty result means the target already has every custom analyzer the source
    depends on. This is a black-box existence check — we call
    ``target_client.get_analyzer(aid)`` and treat 404 as missing. Any other
    error is surfaced verbatim so a broken target endpoint doesn't get
    misreported as a missing dependency.
    """
    from azure.core.exceptions import ResourceNotFoundError

    missing: list[str] = []
    for aid in dependencies:
        try:
            target_client.get_analyzer(aid)
        except ResourceNotFoundError:
            missing.append(aid)
    return missing
