#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "config" / "nflverse_nfl_datasets.json"
DEFAULT_RAW_ROOT = REPO_ROOT / "data" / "raw" / "nfl"
DEFAULT_DB_PATH = REPO_ROOT / "data" / "staging" / "nflverse.duckdb"
DEFAULT_STAGE_START_SEASON = 2021
DEFAULT_STAGE_END_SEASON = 2025
GITHUB_RELEASE_API = "https://api.github.com/repos/nflverse/nflverse-data/releases/tags"
HTTP_HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "NFLverse-ingestion-pipeline",
}


@dataclass(frozen=True)
class DatasetConfig:
    name: str
    release_tag: str
    mode: str
    table_name: str
    asset_name: str | None = None
    asset_pattern: str | None = None
    first_season: int | None = None


@dataclass(frozen=True)
class AssetSelection:
    dataset: DatasetConfig
    asset: dict[str, Any]
    target_path: Path
    metadata_path: Path
    season: int | None = None


def load_manifest(path: Path = MANIFEST_PATH) -> dict[str, DatasetConfig]:
    raw_manifest = json.loads(path.read_text())
    manifest: dict[str, DatasetConfig] = {}

    for name, config in raw_manifest.items():
        manifest[name] = DatasetConfig(
            name=name,
            release_tag=config["release_tag"],
            mode=config["mode"],
            table_name=config["table_name"],
            asset_name=config.get("asset_name"),
            asset_pattern=config.get("asset_pattern"),
            first_season=config.get("first_season"),
        )

    return manifest


def github_json(url: str, timeout: int) -> dict[str, Any]:
    request = urllib.request.Request(url, headers=HTTP_HEADERS)

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API request failed for {url}: {exc.code} {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"GitHub API request failed for {url}: {exc.reason}") from exc


def fetch_release(config: DatasetConfig, timeout: int) -> dict[str, Any]:
    return github_json(f"{GITHUB_RELEASE_API}/{config.release_tag}", timeout=timeout)


def parse_season_asset_map(config: DatasetConfig, release: dict[str, Any]) -> dict[int, dict[str, Any]]:
    if config.mode != "seasonal" or not config.asset_pattern:
        return {}

    asset_regex = re.compile(
        "^" + re.escape(config.asset_pattern).replace(r"\{season\}", r"(?P<season>\d{4})") + "$"
    )

    season_map: dict[int, dict[str, Any]] = {}

    for asset in release.get("assets", []):
        match = asset_regex.match(asset["name"])
        if not match:
            continue

        season = int(match.group("season"))
        season_map[season] = asset

    return season_map


def resolve_single_asset(config: DatasetConfig, release: dict[str, Any], raw_root: Path) -> AssetSelection:
    if not config.asset_name:
        raise ValueError(f"{config.name} is missing an asset_name in the manifest.")

    for asset in release.get("assets", []):
        if asset["name"] == config.asset_name:
            target_path = raw_root / config.name / asset["name"]
            return AssetSelection(
                dataset=config,
                asset=asset,
                target_path=target_path,
                metadata_path=target_path.with_suffix(target_path.suffix + ".metadata.json"),
            )

    raise RuntimeError(
        f"Could not find {config.asset_name} in nflverse-data release '{config.release_tag}'."
    )


def resolve_seasonal_assets(
    config: DatasetConfig,
    release: dict[str, Any],
    raw_root: Path,
    requested_seasons: list[int] | None,
) -> list[AssetSelection]:
    season_map = parse_season_asset_map(config, release)

    if not season_map:
        raise RuntimeError(f"No seasonal parquet assets were found for dataset '{config.name}'.")

    if requested_seasons:
        selected_seasons = sorted(set(requested_seasons))
    else:
        selected_seasons = [max(season_map)]

    missing = [season for season in selected_seasons if season not in season_map]
    if missing:
        available = ", ".join(str(season) for season in sorted(season_map))
        raise RuntimeError(
            f"Dataset '{config.name}' is missing requested seasons: {', '.join(str(season) for season in missing)}. "
            f"Available seasons: {available}"
        )

    selections: list[AssetSelection] = []

    for season in selected_seasons:
        asset = season_map[season]
        target_path = raw_root / config.name / f"season={season}" / asset["name"]
        selections.append(
            AssetSelection(
                dataset=config,
                asset=asset,
                target_path=target_path,
                metadata_path=target_path.with_suffix(target_path.suffix + ".metadata.json"),
                season=season,
            )
        )

    return selections


def resolve_assets(
    config: DatasetConfig,
    release: dict[str, Any],
    raw_root: Path,
    requested_seasons: list[int] | None,
) -> list[AssetSelection]:
    if config.mode == "single":
        return [resolve_single_asset(config, release, raw_root)]

    if config.mode == "seasonal":
        return resolve_seasonal_assets(config, release, raw_root, requested_seasons)

    raise ValueError(f"Unsupported dataset mode '{config.mode}' for dataset '{config.name}'.")


def dataset_supports_seasons(config: DatasetConfig) -> bool:
    return config.mode == "seasonal"


def download_file(url: str, destination: Path, timeout: int) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers=HTTP_HEADERS)
    digest = hashlib.sha256()

    with tempfile.NamedTemporaryFile(delete=False, dir=destination.parent) as temp_file:
        temp_path = Path(temp_file.name)

        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break

                    temp_file.write(chunk)
                    digest.update(chunk)
        except Exception:
            temp_path.unlink(missing_ok=True)
            raise

    temp_path.replace(destination)
    return digest.hexdigest()


def should_skip_download(metadata_path: Path, asset: dict[str, Any], destination: Path, force: bool) -> bool:
    if force or not destination.exists() or not metadata_path.exists():
        return False

    metadata = json.loads(metadata_path.read_text())
    remote_updated_at = asset.get("updated_at")
    remote_digest = asset.get("digest")
    remote_size = asset.get("size")

    if metadata.get("source_asset_updated_at") != remote_updated_at:
        return False

    if remote_digest and metadata.get("source_digest") != remote_digest:
        return False

    if metadata.get("source_size") != remote_size:
        return False

    return True


def write_asset_metadata(
    selection: AssetSelection,
    release: dict[str, Any],
    local_sha256: str,
) -> None:
    metadata = {
        "dataset": selection.dataset.name,
        "sport": "nfl",
        "season": selection.season,
        "release_tag": selection.dataset.release_tag,
        "release_name": release.get("name"),
        "release_url": release.get("html_url"),
        "source_asset_name": selection.asset["name"],
        "source_asset_url": selection.asset["browser_download_url"],
        "source_asset_updated_at": selection.asset.get("updated_at"),
        "source_digest": selection.asset.get("digest"),
        "source_size": selection.asset.get("size"),
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
        "local_path": str(selection.target_path.relative_to(REPO_ROOT)),
        "local_sha256": local_sha256,
    }
    selection.metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")


def write_dataset_metadata(
    config: DatasetConfig,
    dataset_root: Path,
    release: dict[str, Any],
    selections: list[AssetSelection],
) -> None:
    metadata_dir = dataset_root / "_metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)

    summary = {
        "dataset": config.name,
        "sport": "nfl",
        "release_tag": config.release_tag,
        "release_name": release.get("name"),
        "release_url": release.get("html_url"),
        "release_updated_at": release.get("updated_at"),
        "synced_at_utc": datetime.now(timezone.utc).isoformat(),
        "selected_assets": [
            {
                "asset_name": selection.asset["name"],
                "season": selection.season,
                "target_path": str(selection.target_path.relative_to(REPO_ROOT)),
            }
            for selection in selections
        ],
    }

    timestamp_asset = next(
        (asset for asset in release.get("assets", []) if asset["name"] == "timestamp.json"),
        None,
    )
    if timestamp_asset:
        summary["timestamp_asset_url"] = timestamp_asset["browser_download_url"]
        summary["timestamp_asset_updated_at"] = timestamp_asset.get("updated_at")

    (metadata_dir / "release-metadata.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")


def sync_datasets(args: argparse.Namespace) -> int:
    manifest = load_manifest()
    raw_root = Path(args.raw_root).resolve()
    requested_seasons = sorted(set(args.seasons)) if args.seasons else None

    for dataset_name in args.datasets:
        config = manifest[dataset_name]
        if requested_seasons and not dataset_supports_seasons(config):
            print(
                f"Dataset '{dataset_name}' ignores --seasons because it is not season-partitioned.",
                file=sys.stderr,
            )

        release = fetch_release(config, timeout=args.timeout)
        selections = resolve_assets(config, release, raw_root, requested_seasons)
        dataset_root = raw_root / config.name

        if config.mode == "seasonal" and not requested_seasons:
            latest_season = selections[0].season
            print(f"{dataset_name}: no seasons requested, defaulting to latest available season {latest_season}.")

        for selection in selections:
            label = f"{selection.dataset.name}:{selection.season}" if selection.season else selection.dataset.name

            if args.dry_run:
                print(f"[dry-run] {label} -> {selection.target_path}")
                continue

            if should_skip_download(selection.metadata_path, selection.asset, selection.target_path, args.force):
                print(f"skip {label} -> {selection.target_path}")
                continue

            print(f"download {label} -> {selection.target_path}")
            local_sha256 = download_file(
                url=selection.asset["browser_download_url"],
                destination=selection.target_path,
                timeout=args.timeout,
            )
            write_asset_metadata(selection, release, local_sha256)

        if not args.dry_run:
            write_dataset_metadata(config, dataset_root, release, selections)

    return 0


def import_duckdb() -> Any:
    try:
        import duckdb  # type: ignore

        return duckdb
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "duckdb is required to build the local database. Install it with "
            "`python3 -m pip install -r requirements.txt` or `make install`."
        ) from exc


def find_dataset_files(config: DatasetConfig, raw_root: Path) -> list[Path]:
    dataset_root = raw_root / config.name

    if config.mode == "single":
        if not config.asset_name:
            return []
        return sorted(dataset_root.glob(config.asset_name))

    if config.mode == "seasonal" and config.asset_pattern:
        seasonal_pattern = f"season=*/{config.asset_pattern.format(season='*')}"
        return sorted(dataset_root.glob(seasonal_pattern))

    return []


def dataset_glob(config: DatasetConfig, raw_root: Path) -> str:
    dataset_root = (raw_root / config.name).resolve()

    if config.mode == "single":
        if not config.asset_name:
            raise ValueError(f"{config.name} is missing asset_name")
        return str(dataset_root / config.asset_name)

    if config.mode == "seasonal" and config.asset_pattern:
        return str(dataset_root / "season=*" / config.asset_pattern.format(season="*"))

    raise ValueError(f"Unsupported mode for dataset '{config.name}'")


def sql_quote(value: str) -> str:
    return value.replace("'", "''")


def normalize_season_bounds(start_season: int, end_season: int) -> tuple[int, int]:
    if start_season > end_season:
        raise ValueError(
            f"Invalid season range: start season {start_season} is greater than end season {end_season}."
        )

    return start_season, end_season


def ensure_required_raw_views(connection: Any, names: list[str]) -> None:
    existing = {
        row[0]
        for row in connection.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'raw_nfl'"
        ).fetchall()
    }
    missing = [name for name in names if name not in existing]

    if missing:
        raise RuntimeError(
            "Missing required raw_nfl views: "
            + ", ".join(missing)
            + ". Run `build-db` after syncing the required raw datasets."
        )


def replace_table(connection: Any, schema_name: str, table_name: str, select_sql: str, params: list[Any]) -> None:
    connection.execute(f"DROP TABLE IF EXISTS {schema_name}.{table_name}")
    connection.execute(f"CREATE TABLE {schema_name}.{table_name} AS {select_sql}", params)


def build_database(args: argparse.Namespace) -> int:
    manifest = load_manifest()
    raw_root = Path(args.raw_root).resolve()
    database_path = Path(args.database).resolve()
    database_path.parent.mkdir(parents=True, exist_ok=True)

    duckdb = import_duckdb()
    connection = duckdb.connect(str(database_path))
    inventory_rows: list[tuple[str, str, int, str, str]] = []

    connection.execute("CREATE SCHEMA IF NOT EXISTS raw_nfl")
    connection.execute("CREATE SCHEMA IF NOT EXISTS admin")

    for config in manifest.values():
        files = find_dataset_files(config, raw_root)
        if not files:
            print(f"skip {config.name}: no raw files found under {raw_root / config.name}")
            continue

        source_glob = dataset_glob(config, raw_root)
        view_name = config.table_name
        connection.execute(
            f"CREATE OR REPLACE VIEW raw_nfl.{view_name} AS "
            f"SELECT * FROM read_parquet('{sql_quote(source_glob)}', union_by_name = true)"
        )

        inventory_rows.append(
            (
                config.name,
                view_name,
                len(files),
                source_glob,
                datetime.now(timezone.utc).isoformat(),
            )
        )
        print(f"view raw_nfl.{view_name} -> {source_glob}")

    connection.execute("DROP TABLE IF EXISTS admin.ingestion_inventory")
    connection.execute(
        """
        CREATE TABLE admin.ingestion_inventory (
          dataset_name VARCHAR,
          table_name VARCHAR,
          file_count BIGINT,
          source_glob VARCHAR,
          built_at_utc VARCHAR
        )
        """
    )

    for row in inventory_rows:
        connection.execute(
            "INSERT INTO admin.ingestion_inventory VALUES (?, ?, ?, ?, ?)",
            row,
        )

    connection.close()
    print(f"database ready -> {database_path}")
    return 0


def build_stage(args: argparse.Namespace) -> int:
    start_season, end_season = normalize_season_bounds(args.start_season, args.end_season)
    database_path = Path(args.database).resolve()

    duckdb = import_duckdb()
    connection = duckdb.connect(str(database_path))
    ensure_required_raw_views(connection, ["players", "rosters", "schedules", "teams", "draft_picks", "combine"])

    connection.execute("CREATE SCHEMA IF NOT EXISTS stage_nfl")
    connection.execute("CREATE SCHEMA IF NOT EXISTS admin")

    replace_table(
        connection,
        "stage_nfl",
        "teams",
        """
        WITH slice_teams AS (
          SELECT DISTINCT away_team AS team
          FROM raw_nfl.schedules
          WHERE season BETWEEN ? AND ?

          UNION

          SELECT DISTINCT home_team AS team
          FROM raw_nfl.schedules
          WHERE season BETWEEN ? AND ?

          UNION

          SELECT DISTINCT team
          FROM raw_nfl.rosters
          WHERE season BETWEEN ? AND ?
        )
        SELECT
          trim(team_abbr) AS team,
          trim(team_name) AS team_name,
          trim(team_nick) AS team_nickname,
          trim(coalesce(team_name, '') || ' ' || coalesce(team_nick, '')) AS team_full_name,
          team_id,
          trim(team_conf) AS conference,
          trim(team_division) AS division,
          team_color,
          team_color2,
          team_color3,
          team_color4,
          team_logo_wikipedia,
          team_logo_espn,
          team_wordmark,
          team_conference_logo,
          team_league_logo,
          team_logo_squared
        FROM raw_nfl.teams AS t
        INNER JOIN slice_teams
          ON t.team_abbr = slice_teams.team
        WHERE team_abbr IS NOT NULL
        QUALIFY row_number() OVER (PARTITION BY team_abbr ORDER BY team_abbr) = 1
        """,
        [start_season, end_season, start_season, end_season, start_season, end_season],
    )

    replace_table(
        connection,
        "stage_nfl",
        "games",
        """
        SELECT
          game_id,
          season::INTEGER AS season,
          game_type,
          week::INTEGER AS week,
          try_cast(gameday AS DATE) AS game_date,
          weekday,
          gametime AS game_time_local,
          away_team,
          away_score,
          home_team,
          home_score,
          location,
          result AS home_margin,
          total AS total_points,
          coalesce(overtime, 0) = 1 AS went_to_overtime,
          coalesce(div_game, 0) = 1 AS is_division_game,
          roof,
          surface,
          temp,
          wind,
          away_rest,
          home_rest,
          away_moneyline,
          home_moneyline,
          spread_line,
          away_spread_odds,
          home_spread_odds,
          total_line,
          under_odds,
          over_odds,
          away_qb_id,
          home_qb_id,
          away_qb_name,
          home_qb_name,
          away_coach,
          home_coach,
          referee,
          stadium_id,
          stadium,
          old_game_id,
          gsis AS gsis_numeric_id,
          nfl_detail_id,
          pfr AS pfr_game_id,
          pff AS pff_game_id,
          espn AS espn_game_id,
          ftn AS ftn_game_id,
          away_score IS NOT NULL AND home_score IS NOT NULL AS is_completed,
          CASE
            WHEN away_score IS NOT NULL AND home_score IS NOT NULL AND away_score = home_score THEN TRUE
            ELSE FALSE
          END AS is_tie,
          CASE
            WHEN away_score IS NOT NULL AND home_score IS NOT NULL AND home_score > away_score THEN home_team
            WHEN away_score IS NOT NULL AND home_score IS NOT NULL AND away_score > home_score THEN away_team
            ELSE NULL
          END AS winner_team,
          CASE
            WHEN away_score IS NOT NULL AND home_score IS NOT NULL AND home_score > away_score THEN away_team
            WHEN away_score IS NOT NULL AND home_score IS NOT NULL AND away_score > home_score THEN home_team
            ELSE NULL
          END AS loser_team
        FROM raw_nfl.schedules
        WHERE season BETWEEN ? AND ?
        """,
        [start_season, end_season],
    )

    replace_table(
        connection,
        "stage_nfl",
        "game_teams",
        """
        WITH games AS (
          SELECT * FROM stage_nfl.games
        )
        SELECT
          game_id,
          season,
          game_type,
          week,
          game_date,
          home_team AS team,
          away_team AS opponent_team,
          'home' AS home_away,
          TRUE AS is_home,
          FALSE AS is_away,
          home_score AS team_score,
          away_score AS opponent_score,
          CASE
            WHEN home_score IS NOT NULL AND away_score IS NOT NULL THEN home_score - away_score
            ELSE NULL
          END AS point_diff,
          home_rest AS rest_days,
          home_qb_id AS starting_qb_id,
          home_qb_name AS starting_qb_name,
          home_coach AS head_coach,
          CASE
            WHEN home_score IS NULL OR away_score IS NULL THEN NULL
            WHEN home_score > away_score THEN 'W'
            WHEN home_score < away_score THEN 'L'
            ELSE 'T'
          END AS team_result,
          stadium_id,
          stadium,
          location,
          roof,
          surface,
          temp,
          wind
        FROM games

        UNION ALL

        SELECT
          game_id,
          season,
          game_type,
          week,
          game_date,
          away_team AS team,
          home_team AS opponent_team,
          'away' AS home_away,
          FALSE AS is_home,
          TRUE AS is_away,
          away_score AS team_score,
          home_score AS opponent_score,
          CASE
            WHEN away_score IS NOT NULL AND home_score IS NOT NULL THEN away_score - home_score
            ELSE NULL
          END AS point_diff,
          away_rest AS rest_days,
          away_qb_id AS starting_qb_id,
          away_qb_name AS starting_qb_name,
          away_coach AS head_coach,
          CASE
            WHEN away_score IS NULL OR home_score IS NULL THEN NULL
            WHEN away_score > home_score THEN 'W'
            WHEN away_score < home_score THEN 'L'
            ELSE 'T'
          END AS team_result,
          stadium_id,
          stadium,
          location,
          roof,
          surface,
          temp,
          wind
        FROM games
        """,
        [],
    )

    replace_table(
        connection,
        "stage_nfl",
        "roster_snapshots",
        """
        SELECT
          md5(
            coalesce(cast(season AS VARCHAR), '') || '|' ||
            coalesce(team, '') || '|' ||
            coalesce(cast(week AS VARCHAR), '') || '|' ||
            coalesce(game_type, '') || '|' ||
            coalesce(nullif(trim(gsis_id), ''), '') || '|' ||
            coalesce(full_name, '') || '|' ||
            coalesce(position, '') || '|' ||
            coalesce(cast(jersey_number AS VARCHAR), '')
          ) AS roster_entry_id,
          season::INTEGER AS season,
          week::INTEGER AS week,
          game_type,
          team,
          nullif(trim(gsis_id), '') AS player_id,
          nullif(trim(gsis_id), '') AS gsis_id,
          full_name,
          first_name,
          last_name,
          football_name,
          position,
          depth_chart_position,
          ngs_position,
          jersey_number,
          status,
          status_description_abbr,
          birth_date,
          height,
          weight,
          college,
          years_exp,
          headshot_url,
          espn_id,
          sportradar_id,
          yahoo_id,
          rotowire_id,
          pff_id,
          pfr_id,
          fantasy_data_id,
          sleeper_id,
          esb_id,
          gsis_it_id,
          smart_id,
          entry_year,
          rookie_year,
          draft_club,
          draft_number
        FROM raw_nfl.rosters
        WHERE season BETWEEN ? AND ?
        """,
        [start_season, end_season],
    )

    replace_table(
        connection,
        "stage_nfl",
        "players",
        """
        WITH slice_player_ids AS (
          SELECT DISTINCT gsis_id
          FROM stage_nfl.roster_snapshots
          WHERE gsis_id IS NOT NULL

          UNION

          SELECT DISTINCT away_qb_id AS gsis_id
          FROM stage_nfl.games
          WHERE away_qb_id IS NOT NULL

          UNION

          SELECT DISTINCT home_qb_id AS gsis_id
          FROM stage_nfl.games
          WHERE home_qb_id IS NOT NULL
        ),
        roster_latest AS (
          SELECT
            gsis_id,
            full_name,
            first_name,
            last_name,
            football_name,
            position,
            ngs_position,
            jersey_number,
            status,
            birth_date,
            height,
            weight,
            college,
            years_exp,
            headshot_url,
            espn_id,
            pfr_id,
            pff_id,
            esb_id,
            smart_id,
            rookie_year,
            season,
            week,
            team,
            draft_club,
            draft_number,
            row_number() OVER (
              PARTITION BY gsis_id
              ORDER BY season DESC, week DESC, team
            ) AS row_number_in_player
          FROM stage_nfl.roster_snapshots
          WHERE gsis_id IS NOT NULL
        )
        SELECT
          p.gsis_id AS player_id,
          p.gsis_id,
          p.display_name,
          p.common_first_name,
          p.first_name,
          p.last_name,
          p.short_name,
          p.football_name,
          p.suffix,
          p.esb_id,
          p.nfl_id,
          p.pfr_id,
          p.pff_id,
          p.otc_id,
          p.espn_id,
          p.smart_id,
          try_cast(p.birth_date AS DATE) AS birth_date,
          p.position_group,
          p.position,
          p.ngs_position_group,
          p.ngs_position,
          p.height,
          p.weight,
          p.headshot,
          p.college_name,
          p.college_conference,
          p.jersey_number,
          p.rookie_season,
          p.last_season,
          p.latest_team,
          p.status,
          p.ngs_status,
          p.ngs_status_short_description,
          p.years_of_experience,
          p.pff_position,
          p.pff_status,
          p.draft_year,
          p.draft_round,
          p.draft_pick,
          p.draft_team
        FROM raw_nfl.players AS p
        INNER JOIN slice_player_ids AS ids
          ON p.gsis_id = ids.gsis_id

        UNION ALL

        SELECT
          r.gsis_id AS player_id,
          r.gsis_id,
          r.full_name AS display_name,
          NULL AS common_first_name,
          r.first_name,
          r.last_name,
          r.full_name AS short_name,
          r.football_name,
          NULL AS suffix,
          r.esb_id,
          NULL AS nfl_id,
          r.pfr_id,
          r.pff_id,
          NULL AS otc_id,
          r.espn_id,
          r.smart_id,
          r.birth_date,
          NULL AS position_group,
          r.position,
          NULL AS ngs_position_group,
          r.ngs_position,
          try_cast(round(r.height) AS INTEGER) AS height,
          r.weight,
          r.headshot_url AS headshot,
          r.college AS college_name,
          NULL AS college_conference,
          cast(r.jersey_number AS VARCHAR) AS jersey_number,
          r.rookie_year AS rookie_season,
          r.season AS last_season,
          r.team AS latest_team,
          r.status,
          NULL AS ngs_status,
          NULL AS ngs_status_short_description,
          r.years_exp AS years_of_experience,
          NULL AS pff_position,
          NULL AS pff_status,
          NULL AS draft_year,
          NULL AS draft_round,
          r.draft_number AS draft_pick,
          r.draft_club AS draft_team
        FROM roster_latest AS r
        LEFT JOIN raw_nfl.players AS p
          ON r.gsis_id = p.gsis_id
        WHERE r.row_number_in_player = 1
          AND p.gsis_id IS NULL
        """,
        [],
    )

    replace_table(
        connection,
        "stage_nfl",
        "draft_picks",
        """
        SELECT
          md5(
            cast(season AS VARCHAR) || '|' ||
            coalesce(cast(round AS VARCHAR), '') || '|' ||
            coalesce(cast(pick AS VARCHAR), '') || '|' ||
            coalesce(team, '') || '|' ||
            coalesce(gsis_id, pfr_player_id, pfr_player_name, '')
          ) AS draft_pick_id,
          season AS draft_season,
          round AS draft_round,
          pick AS overall_pick,
          team AS draft_team,
          gsis_id AS player_id,
          gsis_id,
          pfr_player_id,
          cfb_player_id,
          pfr_player_name AS player_name,
          hof,
          position,
          category,
          side,
          college,
          age,
          "to" AS last_season,
          allpro,
          probowls,
          seasons_started,
          w_av,
          car_av,
          dr_av,
          games,
          pass_completions,
          pass_attempts,
          pass_yards,
          pass_tds,
          pass_ints,
          rush_atts,
          rush_yards,
          rush_tds,
          receptions,
          rec_yards,
          rec_tds,
          def_solo_tackles,
          def_ints,
          def_sacks
        FROM raw_nfl.draft_picks
        WHERE season BETWEEN ? AND ?
        """,
        [start_season, end_season],
    )

    replace_table(
        connection,
        "stage_nfl",
        "combine",
        """
        SELECT
          md5(
            cast(coalesce(try_cast(draft_year AS INTEGER), season) AS VARCHAR) || '|' ||
            coalesce(pfr_id, cfb_id, player_name, '') || '|' ||
            coalesce(school, '') || '|' ||
            coalesce(pos, '')
          ) AS combine_entry_id,
          season AS combine_season,
          coalesce(try_cast(draft_year AS INTEGER), season) AS draft_year,
          draft_team,
          try_cast(draft_round AS INTEGER) AS draft_round,
          try_cast(draft_ovr AS INTEGER) AS overall_pick,
          pfr_id,
          cfb_id,
          player_name,
          pos AS position,
          school,
          ht AS height_text,
          wt AS weight,
          forty,
          bench,
          vertical,
          broad_jump,
          cone,
          shuttle
        FROM raw_nfl.combine
        WHERE coalesce(try_cast(draft_year AS INTEGER), season) BETWEEN ? AND ?
        """,
        [start_season, end_season],
    )

    replace_table(
        connection,
        "stage_nfl",
        "rookies",
        """
        WITH rookie_base AS (
          SELECT *
          FROM stage_nfl.players
          WHERE rookie_season BETWEEN ? AND ?
        ),
        rookie_with_draft AS (
          SELECT
            r.*,
            d.draft_pick_id,
            d.draft_round,
            d.overall_pick AS draft_pick,
            d.draft_team,
            d.position AS draft_position,
            d.category AS draft_category,
            d.side AS draft_side,
            d.college AS draft_college,
            d.age AS draft_age,
            d.pfr_player_id AS draft_pfr_id,
            row_number() OVER (
              PARTITION BY r.player_id
              ORDER BY d.draft_season, d.overall_pick NULLS LAST, d.draft_pick_id
            ) AS draft_row_number
          FROM rookie_base AS r
          LEFT JOIN stage_nfl.draft_picks AS d
            ON d.draft_season = r.rookie_season
           AND (
             (r.gsis_id IS NOT NULL AND d.gsis_id = r.gsis_id)
             OR (r.pfr_id IS NOT NULL AND d.pfr_player_id = r.pfr_id)
           )
        ),
        rookie_with_primary_draft AS (
          SELECT *
          FROM rookie_with_draft
          WHERE draft_row_number = 1
        ),
        rookie_with_combine AS (
          SELECT
            r.*,
            c.combine_entry_id,
            c.player_name AS combine_player_name,
            c.position AS combine_position,
            c.school AS combine_school,
            c.height_text AS combine_height_text,
            c.weight AS combine_weight,
            c.forty,
            c.bench,
            c.vertical,
            c.broad_jump,
            c.cone,
            c.shuttle,
            row_number() OVER (
              PARTITION BY r.player_id
              ORDER BY c.draft_year, c.overall_pick NULLS LAST, c.combine_entry_id
            ) AS combine_row_number
          FROM rookie_with_primary_draft AS r
          LEFT JOIN stage_nfl.combine AS c
            ON c.draft_year = r.rookie_season
           AND (
             (r.pfr_id IS NOT NULL AND c.pfr_id = r.pfr_id)
             OR (r.pfr_id IS NULL AND r.draft_pfr_id IS NOT NULL AND c.pfr_id = r.draft_pfr_id)
           )
        )
        SELECT
          player_id AS rookie_id,
          player_id,
          gsis_id,
          rookie_season,
          display_name,
          first_name,
          last_name,
          short_name,
          football_name,
          birth_date,
          position_group,
          position,
          height,
          weight,
          college_name,
          college_conference,
          jersey_number,
          latest_team,
          status,
          years_of_experience,
          pfr_id,
          pff_id,
          espn_id,
          headshot,
          draft_pick_id,
          draft_round,
          draft_pick,
          draft_team,
          draft_position,
          draft_category,
          draft_side,
          draft_college,
          draft_age,
          combine_entry_id,
          combine_player_name,
          combine_position,
          combine_school,
          combine_height_text,
          combine_weight,
          forty,
          bench,
          vertical,
          broad_jump,
          cone,
          shuttle,
          draft_pick_id IS NOT NULL AS is_drafted,
          combine_entry_id IS NOT NULL AS has_combine_data
        FROM rookie_with_combine
        WHERE combine_row_number = 1
        """,
        [start_season, end_season],
    )

    replace_table(
        connection,
        "admin",
        "stage_build_inventory",
        """
        SELECT 'teams' AS table_name, (SELECT count(*) FROM stage_nfl.teams) AS row_count, ? AS start_season, ? AS end_season
        UNION ALL
        SELECT 'games' AS table_name, (SELECT count(*) FROM stage_nfl.games) AS row_count, ? AS start_season, ? AS end_season
        UNION ALL
        SELECT 'game_teams' AS table_name, (SELECT count(*) FROM stage_nfl.game_teams) AS row_count, ? AS start_season, ? AS end_season
        UNION ALL
        SELECT 'roster_snapshots' AS table_name, (SELECT count(*) FROM stage_nfl.roster_snapshots) AS row_count, ? AS start_season, ? AS end_season
        UNION ALL
        SELECT 'players' AS table_name, (SELECT count(*) FROM stage_nfl.players) AS row_count, ? AS start_season, ? AS end_season
        UNION ALL
        SELECT 'draft_picks' AS table_name, (SELECT count(*) FROM stage_nfl.draft_picks) AS row_count, ? AS start_season, ? AS end_season
        UNION ALL
        SELECT 'combine' AS table_name, (SELECT count(*) FROM stage_nfl.combine) AS row_count, ? AS start_season, ? AS end_season
        UNION ALL
        SELECT 'rookies' AS table_name, (SELECT count(*) FROM stage_nfl.rookies) AS row_count, ? AS start_season, ? AS end_season
        """,
        [
            start_season,
            end_season,
            start_season,
            end_season,
            start_season,
            end_season,
            start_season,
            end_season,
            start_season,
            end_season,
            start_season,
            end_season,
            start_season,
            end_season,
            start_season,
            end_season,
        ],
    )

    connection.close()
    print(f"stage_nfl ready for seasons {start_season}-{end_season} -> {database_path}")
    return 0


def validate_stage(args: argparse.Namespace) -> int:
    start_season, end_season = normalize_season_bounds(args.start_season, args.end_season)
    database_path = Path(args.database).resolve()

    duckdb = import_duckdb()
    connection = duckdb.connect(str(database_path), read_only=True)

    checks = [
        (
            "stage_nfl.teams has 32 teams",
            "SELECT CASE WHEN count(*) = 32 THEN 1 ELSE 0 END FROM stage_nfl.teams",
        ),
        (
            "stage_nfl.games has unique non-null game_id",
            """
            SELECT CASE
              WHEN count(*) = count(game_id) AND count(*) = count(DISTINCT game_id) THEN 1
              ELSE 0
            END
            FROM stage_nfl.games
            """,
        ),
        (
            "stage_nfl.games only covers requested seasons",
            """
            SELECT CASE
              WHEN min(season) >= ? AND max(season) <= ? THEN 1
              ELSE 0
            END
            FROM stage_nfl.games
            """,
        ),
        (
            "stage_nfl.game_teams has exactly two rows per game",
            """
            SELECT CASE
              WHEN (SELECT count(*) FROM stage_nfl.game_teams) = 2 * (SELECT count(*) FROM stage_nfl.games) THEN 1
              ELSE 0
            END
            """,
        ),
        (
            "stage_nfl.roster_snapshots has unique roster_entry_id",
            """
            SELECT CASE
              WHEN count(*) = count(DISTINCT roster_entry_id) THEN 1
              ELSE 0
            END
            FROM stage_nfl.roster_snapshots
            """,
        ),
        (
            "games team codes resolve to stage_nfl.teams",
            """
            SELECT CASE
              WHEN count(*) = 0 THEN 1
              ELSE 0
            END
            FROM (
              SELECT away_team AS team FROM stage_nfl.games
              UNION ALL
              SELECT home_team AS team FROM stage_nfl.games
            ) AS g
            LEFT JOIN stage_nfl.teams AS t
              ON g.team = t.team
            WHERE g.team IS NOT NULL AND t.team IS NULL
            """,
        ),
        (
            "roster team codes resolve to stage_nfl.teams",
            """
            SELECT CASE
              WHEN count(*) = 0 THEN 1
              ELSE 0
            END
            FROM stage_nfl.roster_snapshots AS r
            LEFT JOIN stage_nfl.teams AS t
              ON r.team = t.team
            WHERE r.team IS NOT NULL AND t.team IS NULL
            """,
        ),
        (
            "roster player ids resolve to stage_nfl.players when present",
            """
            SELECT CASE
              WHEN count(*) = 0 THEN 1
              ELSE 0
            END
            FROM stage_nfl.roster_snapshots AS r
            LEFT JOIN stage_nfl.players AS p
              ON r.gsis_id = p.gsis_id
            WHERE r.gsis_id IS NOT NULL AND p.gsis_id IS NULL
            """,
        ),
        (
            "stage_nfl.draft_picks has unique draft_pick_id",
            """
            SELECT CASE
              WHEN count(*) = count(DISTINCT draft_pick_id) THEN 1
              ELSE 0
            END
            FROM stage_nfl.draft_picks
            """,
        ),
        (
            "stage_nfl.combine has unique combine_entry_id",
            """
            SELECT CASE
              WHEN count(*) = count(DISTINCT combine_entry_id) THEN 1
              ELSE 0
            END
            FROM stage_nfl.combine
            """,
        ),
        (
            "stage_nfl.rookies has unique rookie_id",
            """
            SELECT CASE
              WHEN count(*) = count(DISTINCT rookie_id) THEN 1
              ELSE 0
            END
            FROM stage_nfl.rookies
            """,
        ),
        (
            "stage_nfl.rookies only covers requested rookie seasons",
            """
            SELECT CASE
              WHEN min(rookie_season) >= ? AND max(rookie_season) <= ? THEN 1
              ELSE 0
            END
            FROM stage_nfl.rookies
            """,
        ),
    ]

    failures: list[str] = []

    for description, query in checks:
        params = [start_season, end_season] if "min(season)" in query or "min(rookie_season)" in query else []
        result = connection.execute(query, params).fetchone()[0]
        if result == 1:
            print(f"pass {description}")
        else:
            print(f"fail {description}")
            failures.append(description)

    connection.close()

    if failures:
        raise RuntimeError("Stage validation failed: " + "; ".join(failures))

    print(f"stage_nfl validation passed for seasons {start_season}-{end_season}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    manifest = load_manifest()
    dataset_names = sorted(manifest)

    parser = argparse.ArgumentParser(
        description="Sync official nflverse-data parquet assets and register them in DuckDB."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    sync_parser = subparsers.add_parser("sync", help="Download parquet assets from nflverse-data releases.")
    sync_parser.add_argument(
        "--datasets",
        nargs="+",
        choices=dataset_names,
        required=True,
        help="Datasets to sync from nflverse-data.",
    )
    sync_parser.add_argument(
        "--seasons",
        nargs="+",
        type=int,
        help="Optional season list for seasonal datasets like rosters and pbp.",
    )
    sync_parser.add_argument(
        "--raw-root",
        default=str(DEFAULT_RAW_ROOT),
        help=f"Raw data destination root. Default: {DEFAULT_RAW_ROOT}",
    )
    sync_parser.add_argument("--force", action="store_true", help="Redownload files even if metadata matches.")
    sync_parser.add_argument("--dry-run", action="store_true", help="Show the files that would be downloaded.")
    sync_parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="HTTP timeout in seconds for GitHub API and asset downloads.",
    )
    sync_parser.set_defaults(func=sync_datasets)

    db_parser = subparsers.add_parser("build-db", help="Build a local DuckDB database from synced parquet.")
    db_parser.add_argument(
        "--raw-root",
        default=str(DEFAULT_RAW_ROOT),
        help=f"Raw data source root. Default: {DEFAULT_RAW_ROOT}",
    )
    db_parser.add_argument(
        "--database",
        default=str(DEFAULT_DB_PATH),
        help=f"DuckDB database path. Default: {DEFAULT_DB_PATH}",
    )
    db_parser.set_defaults(func=build_database)

    stage_parser = subparsers.add_parser("build-stage", help="Build stage_nfl tables from raw_nfl views.")
    stage_parser.add_argument(
        "--database",
        default=str(DEFAULT_DB_PATH),
        help=f"DuckDB database path. Default: {DEFAULT_DB_PATH}",
    )
    stage_parser.add_argument(
        "--start-season",
        type=int,
        default=DEFAULT_STAGE_START_SEASON,
        help=f"First season to include in stage_nfl. Default: {DEFAULT_STAGE_START_SEASON}",
    )
    stage_parser.add_argument(
        "--end-season",
        type=int,
        default=DEFAULT_STAGE_END_SEASON,
        help=f"Last season to include in stage_nfl. Default: {DEFAULT_STAGE_END_SEASON}",
    )
    stage_parser.set_defaults(func=build_stage)

    validate_parser = subparsers.add_parser("validate-stage", help="Validate the stage_nfl layer.")
    validate_parser.add_argument(
        "--database",
        default=str(DEFAULT_DB_PATH),
        help=f"DuckDB database path. Default: {DEFAULT_DB_PATH}",
    )
    validate_parser.add_argument(
        "--start-season",
        type=int,
        default=DEFAULT_STAGE_START_SEASON,
        help=f"First season expected in stage_nfl. Default: {DEFAULT_STAGE_START_SEASON}",
    )
    validate_parser.add_argument(
        "--end-season",
        type=int,
        default=DEFAULT_STAGE_END_SEASON,
        help=f"Last season expected in stage_nfl. Default: {DEFAULT_STAGE_END_SEASON}",
    )
    validate_parser.set_defaults(func=validate_stage)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
