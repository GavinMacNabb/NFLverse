# NFLverse

NFLverse is the home for our NFL and college football data work.

## What This Repo Is For

The goal is simple:

- Game schedules and results
- Team and conference data
- Rosters and player info
- Play-by-play and drive-level data
- Team and player stats
- Rankings, standings, and advanced metrics
- Historical data and season summaries

## How We Work

- Keep the data traceable back to a source.
- Keep workflows repeatable.
- Treat NFL and CFB as related but separate products.
- Keep the repo easy to grow.

## Versioning

Version notes live in `CHANGELOG.md`.

The actual version number lives in `VERSION`.

Normal flow:

- add notes under `## [Unreleased]` in `CHANGELOG.md`
- add one PR label: `release:major`, `release:minor`, `release:patch`, or `release:none`
- let GitHub handle the version bump, tag, and release after merge

## Formatting

Formatting is checked in pull requests.

Use:

- `npm install`
- `npm run format`
- `npm run format:check`

## NFL Ingestion Pipeline

The first ingestion slice is NFL only.

It pulls verified parquet assets from the official
[`nflverse-data`](https://github.com/nflverse/nflverse-data) GitHub releases and
stores them under `data/raw/nfl/`.

Initial datasets:

- `players`
- `schedules`
- `teams`
- `rosters`
- `draft_picks`
- `combine`
- `pbp`

The sync step is conservative on purpose:

- `players` and `schedules` pull one parquet each
- `rosters` and `pbp` are season-partitioned
- if you do not pass `--seasons` for a season-partitioned dataset, the pipeline only pulls the latest available season

Setup:

- `make install`

Examples:

- `make sample-ingest`
- `make sync-stage-slice`
- `make build-db`
- `make build-stage`
- `make validate-stage`
- `make run-app`

The database step creates a local DuckDB file at `data/staging/nflverse.duckdb`
and registers raw parquet-backed views in the `raw_nfl` schema.

The first staged layer builds `stage_nfl` tables for the 2021-2025 NFL seasons:

- `stage_nfl.teams`
- `stage_nfl.players`
- `stage_nfl.games`
- `stage_nfl.game_teams`
- `stage_nfl.roster_snapshots`
- `stage_nfl.draft_picks`
- `stage_nfl.combine`
- `stage_nfl.rookies`

See `docs/nfl-ingestion.md` for details.

## Table Browser

A small Flask app is available for browsing the local DuckDB tables.

- run `make run-app`
- open `http://127.0.0.1:5000`

See `docs/table-browser.md` for details.

## Layout

Current working layout:

```text
data/
  raw/
    nfl/
  staging/
  curated/
config/
scripts/
tests/
docs/
```

## Status

The repo now has an initial NFL ingestion scaffold and local raw database build
step. The larger transformation, modeling, and analytics layers are still ahead.
