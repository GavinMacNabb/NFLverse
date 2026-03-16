# football_db

Data analytics platform for football sports data in the United States, focused on the NFL and college football (CFB).

## Overview

This repository is intended to become the central workspace for collecting, validating, transforming, and analyzing football data. The project will support repeatable data workflows, exploratory analysis, and downstream products built on trusted NFL and CFB datasets.

## Initial Goals

- Build a clean, versioned data foundation for NFL and CFB analytics.
- Standardize schemas, field definitions, and source attribution across datasets.
- Support reproducible ingestion and transformation pipelines.
- Enable analysis for team, player, game, season, and historical trend reporting.
- Keep the project structured so it can grow into dashboards, models, and research workflows.

## Data Domains

- Game schedules and results
- Teams and conferences
- Rosters and player metadata
- Play-by-play and drive-level data
- Team and player statistics
- Rankings, standings, and advanced metrics
- Historical archives and season summaries

## Principles

- Accuracy first: every dataset should be traceable to a source.
- Reproducibility matters: transformations should be deterministic and documented.
- NFL and CFB are related but distinct products: avoid mixing assumptions across leagues.
- Documentation is part of the deliverable, not optional project overhead.

## Versioning

Repository versioning rules live in `VERSION.md`, the canonical machine-readable version lives in `VERSION`, and release history lives in `CHANGELOG.md`.

The intended workflow is:

- add human-readable change notes to `CHANGELOG.md` under `## [Unreleased]`
- apply a release label to the pull request: `release:major`, `release:minor`, `release:patch`, or `release:none`
- let GitHub update `VERSION` and `VERSION.md`, cut the release tag, and publish the GitHub release after merge
- use the manual GitHub Actions dispatch only for bootstrap or exceptional releases

## Development Workflow

Formatting is enforced in pull requests.

Use:

- `npm install`
- `npm run format`
- `npm run format:check`

The repository currently uses Prettier to format Markdown, YAML, JSON, and shell files.

## Planned Repository Shape

As the codebase grows, it should generally evolve toward a structure similar to:

```text
data/
  raw/
  staging/
  curated/
notebooks/
src/
tests/
docs/
```

## Agent Guidance

Repository-specific agent rules live in `agents.md`.

## Status

Initial repository scaffold created. Implementation details, tooling, and data pipelines are still to be defined.
