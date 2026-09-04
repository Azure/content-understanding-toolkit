# Releasing CU CLI

Only repository maintainers should publish `cu-cli-core` and `cu-cli`. Releases
must run from an approved, fully tested commit on the canonical repository's
`main` branch.

## One-time repository configuration

An administrator of `Azure/content-understanding-toolkit` must:

1. Create a GitHub environment named exactly `pypi`.
2. Add at least one Direct Owner other than the person initiating the release
   as a required reviewer.
3. Prevent reviewers from approving their own deployments.
4. Restrict the environment to the protected `main` branch.
5. Register PyPI trusted publishers using:

   | PyPI field | Value |
   | --- | --- |
   | Owner | `Azure` |
   | Repository | `content-understanding-toolkit` |
   | Workflow | `release.yml` |
   | Environment | `pypi` |

The environment and trusted-publisher configuration lives outside the
repository. Verify it before every release.

## First-release bootstrap

Pending publishers do not reserve project names. Bootstrap the projects in
order so the identical OIDC identities cannot select the wrong pending
publisher:

1. Merge all release changes to `main` and wait for every required CI check.
2. Replace `Unreleased` in `CHANGELOG.md` with the release date.
3. Copy the exact 40-character `main` commit SHA.
4. Register only the `cu-cli-core` pending publisher.
5. Run **Release** from `main` with:
   - package: `core`
   - version: the exact `cu-cli-core` version from `packages/core/pyproject.toml`
   - commit: the approved commit SHA
6. Approve the `pypi` environment deployment and verify the core project and
   files on PyPI.
7. Register the `cu-cli` pending publisher.
8. Run **Release** again from the same commit with:
   - package: `cli`
   - version: the exact `cu-cli` version from
     `packages/standalone/pyproject.toml`
   - commit: the same approved commit SHA
9. Approve the deployment and verify the CLI project and files on PyPI.
10. Install the exact released CLI version in a clean environment and run
    smoke tests.

The workflow rejects forks, non-`main` refs, abbreviated or mismatched commits,
version mismatches, an undated CLI changelog, unstable core dependency metadata,
and CLI publication before the matching core version exists on PyPI.

## Subsequent releases

Publish core before CLI when both change. Keep manual, approval-gated releases
until tag automation is introduced through a separate reviewed change with
equivalent commit, version, environment, and ordering controls.
