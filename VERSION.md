# Versioning

## Current Version

The real version number lives in `VERSION`.

<!-- version:start -->

`0.1.0`

<!-- version:end -->

## Version Format

We use a simple semver-style format:

`MAJOR.MINOR.PATCH`

- `MAJOR` for breaking changes
- `MINOR` for new backward-compatible work
- `PATCH` for fixes and cleanup

## Normal Flow

- Add notes under `## [Unreleased]` in `CHANGELOG.md`.
- Add one PR label: `release:major`, `release:minor`, `release:patch`, or `release:none`.
- Do not manually edit `VERSION` in a normal PR.
- GitHub will update the version, create the tag, and publish the release after merge.

## Tags

Release tags use this format:

`vMAJOR.MINOR.PATCH`

## Manual Fallback

If we ever need a bootstrap release or an exception, a maintainer can run the release workflow manually in GitHub Actions.

## Notes

This file is mainly here so people can quickly see the current version and the release flow without digging through the workflows.
