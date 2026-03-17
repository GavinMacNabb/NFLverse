# NFL Ingestion

This workflow is the first real data pipeline in the repo.

## Scope

- NFL only
- Raw source assets come from the official
  [`nflverse-data`](https://github.com/nflverse/nflverse-data) GitHub releases
- Raw files land in `data/raw/nfl/`
- The local DuckDB database lands in `data/staging/`

This keeps NFL and CFB separate while the pipeline is still being built out.

## Current Dataset Coverage

- `players`
  Source release: <https://github.com/nflverse/nflverse-data/releases/tag/players>
- `schedules`
  Source release: <https://github.com/nflverse/nflverse-data/releases/tag/schedules>
- `teams`
  Source release: <https://github.com/nflverse/nflverse-data/releases/tag/teams>
- `rosters`
  Source release: <https://github.com/nflverse/nflverse-data/releases/tag/rosters>
- `draft_picks`
  Source release: <https://github.com/nflverse/nflverse-data/releases/tag/draft_picks>
- `combine`
  Source release: <https://github.com/nflverse/nflverse-data/releases/tag/combine>
- `pbp`
  Source release: <https://github.com/nflverse/nflverse-data/releases/tag/pbp>

The manifest lives in `config/nflverse_nfl_datasets.json`.

## Commands

Create the local Python environment and install DuckDB:

```bash
make install
```

Pull the lightweight starter datasets:

```bash
make sample-ingest
```

Pull the 2021-2025 staged slice inputs:

```bash
make sync-stage-slice
```

Build the local database:

```bash
make build-db
```

Build the staged NFL layer:

```bash
make build-stage
```

Validate the staged NFL layer:

```bash
make validate-stage
```

Run the tests:

```bash
make test
```

## Data Layout

Single-file datasets land here:

```text
data/raw/nfl/players/players.parquet
data/raw/nfl/schedules/games.parquet
data/raw/nfl/teams/teams_colors_logos.parquet
data/raw/nfl/draft_picks/draft_picks.parquet
data/raw/nfl/combine/combine.parquet
```

Season-partitioned datasets land here:

```text
data/raw/nfl/rosters/season=2025/roster_2025.parquet
data/raw/nfl/pbp/season=2025/play_by_play_2025.parquet
```

Each downloaded asset gets a sibling metadata file with the upstream release
URL, asset URL, upstream update timestamp, and local checksum.

Each dataset directory also gets `_metadata/release-metadata.json`.

## Database

`scripts/nflverse_pipeline.py build-db` creates raw parquet-backed views in DuckDB:

- `raw_nfl.players`
- `raw_nfl.schedules`
- `raw_nfl.teams`
- `raw_nfl.rosters`
- `raw_nfl.draft_picks`
- `raw_nfl.combine`
- `raw_nfl.pbp`

It also writes `admin.ingestion_inventory` so we can see what raw datasets were
registered into the database.

## Stage Layer

`scripts/nflverse_pipeline.py build-stage --start-season 2021 --end-season 2025`
materializes the first normalized NFL layer:

- `stage_nfl.teams`
  One row per team code
- `stage_nfl.games`
  One row per game for seasons 2021-2025
- `stage_nfl.game_teams`
  Two rows per game, one for each team side
- `stage_nfl.roster_snapshots`
  One row per `season/team/week/game_type/player` snapshot from the roster files
- `stage_nfl.players`
  One row per player referenced by the 2021-2025 staged slice
- `stage_nfl.draft_picks`
  One row per draft pick for the 2021-2025 draft classes
- `stage_nfl.combine`
  One row per combine entry for the 2021-2025 draft classes
- `stage_nfl.rookies`
  One row per rookie-season player, enriched with draft and combine data when a verified join exists

`scripts/nflverse_pipeline.py validate-stage` checks key uniqueness, season
range, two-rows-per-game behavior, and team/player/draft/combine key resolution.
