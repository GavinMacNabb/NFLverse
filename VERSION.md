# Version Policy

## Current Version

The canonical machine-readable version is stored in `VERSION`.

<!-- version:start -->

`0.1.0`

<!-- version:end -->

## Purpose

This file defines how repository version numbers should be managed for `football_db`.

## Versioning Scheme

Use a semver-style format:

`MAJOR.MINOR.PATCH`

- `MAJOR`: breaking changes to stable data contracts, schemas, interfaces, or expected repository behavior
- `MINOR`: backward-compatible additions such as new datasets, new analytics features, or additive schema changes
- `PATCH`: backward-compatible fixes, corrections, cleanup, or implementation improvements

## Release Guidance

- Do not bump the version for purely administrative changes such as GitHub templates, repo settings, or wording-only documentation updates.
- Keep `CHANGELOG.md` aligned with the releaseable change by adding notes under `## [Unreleased]` in pull requests.
- Do not manually edit `VERSION` or the current version block in this file during normal pull request work.
- Release tags use the format `vMAJOR.MINOR.PATCH`.
- GitHub releases are created from the version declared in `VERSION` after the change lands on `main`.

## Automation Workflow

Versioning is automated through GitHub Actions:

1. Add changelog notes to `CHANGELOG.md` under `## [Unreleased]`.
2. Apply exactly one pull request label:
   - `release:major`
   - `release:minor`
   - `release:patch`
   - `release:none` for administrative or documentation-only work
3. After the pull request merges to `main`, GitHub Actions will:
   - calculate the next version
   - update `VERSION`
   - update the mirrored current-version block in `VERSION.md`
   - promote `Unreleased` notes into a dated release section in `CHANGELOG.md`
   - create the Git tag and GitHub release

Manual fallback:

- A maintainer can run the release workflow manually from GitHub Actions for an exceptional or bootstrap release.

## Current Stage

`0.1.0` represents the initial project scaffold and governance baseline.
