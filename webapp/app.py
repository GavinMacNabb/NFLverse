from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
from flask import Flask, abort, render_template, request, url_for

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATABASE_PATH = REPO_ROOT / "data" / "staging" / "nflverse.duckdb"
VISIBLE_SCHEMAS = ("raw_nfl", "stage_nfl", "admin")
DEFAULT_PREVIEW_LIMIT = 50
MAX_PREVIEW_LIMIT = 200
DEFAULT_SEARCH_LIMIT = 25
MAX_SEARCH_LIMIT = 100
SCHEMA_META = {
    "stage_nfl": {
        "label": "Stage Layer",
        "description": "Normalized tables for the 2021-2025 NFL slice.",
        "accent": "stage",
    },
    "raw_nfl": {
        "label": "Raw Layer",
        "description": "Direct source-backed tables from official nflverse-data releases.",
        "accent": "raw",
    },
    "admin": {
        "label": "Admin Layer",
        "description": "Build inventories and metadata about the local warehouse.",
        "accent": "admin",
    },
}


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE_PATH=str(DEFAULT_DATABASE_PATH),
        VISIBLE_SCHEMAS=VISIBLE_SCHEMAS,
        DEFAULT_PREVIEW_LIMIT=DEFAULT_PREVIEW_LIMIT,
        MAX_PREVIEW_LIMIT=MAX_PREVIEW_LIMIT,
        DEFAULT_SEARCH_LIMIT=DEFAULT_SEARCH_LIMIT,
        MAX_SEARCH_LIMIT=MAX_SEARCH_LIMIT,
    )

    if test_config:
        app.config.update(test_config)

    @app.context_processor
    def inject_shell_context() -> dict[str, Any]:
        database_path = Path(app.config["DATABASE_PATH"])
        browser_state = load_browser_state(database_path, tuple(app.config["VISIBLE_SCHEMAS"]))
        return {
            "database_path": database_path,
            "database_missing": browser_state["database_missing"],
            "tables_by_schema": browser_state["tables_by_schema"],
            "schema_summaries": browser_state["schema_summaries"],
            "overview_metrics": browser_state["overview_metrics"],
            "schema_meta": SCHEMA_META,
        }

    @app.get("/")
    def index() -> str:
        return render_template(
            "index.html",
            active_page="overview",
        )

    @app.get("/players")
    def player_search() -> str:
        database_path = Path(app.config["DATABASE_PATH"])
        search_query = request.args.get("q", "").strip()
        limit = parse_positive_int(
            request.args.get("limit"),
            default=app.config["DEFAULT_SEARCH_LIMIT"],
            maximum=app.config["MAX_SEARCH_LIMIT"],
        )
        offset = parse_positive_int(request.args.get("offset"), default=0)

        players: list[dict[str, Any]] = []
        total_count = 0

        if database_path.exists():
            with open_database(database_path) as connection:
                if resolve_table_reference(connection, "stage_nfl", "players") is None:
                    abort(404)
                players, total_count = search_players(
                    connection,
                    search_query=search_query,
                    limit=limit,
                    offset=offset,
                )

        return render_template(
            "players.html",
            active_page="players",
            search_query=search_query,
            players=players,
            total_count=total_count,
            result_start=offset + 1 if total_count > 0 else 0,
            result_end=min(offset + limit, total_count),
            limit=limit,
            offset=offset,
            has_previous=offset > 0,
            has_next=offset + limit < total_count,
            previous_url=build_page_url(
                "player_search",
                limit=limit,
                offset=max(offset - limit, 0),
                q=search_query,
            ),
            next_url=build_page_url(
                "player_search",
                limit=limit,
                offset=offset + limit,
                q=search_query,
            ),
        )

    @app.get("/teams")
    def team_search() -> str:
        database_path = Path(app.config["DATABASE_PATH"])
        limit = parse_positive_int(
            request.args.get("limit"),
            default=app.config["DEFAULT_SEARCH_LIMIT"],
            maximum=app.config["MAX_SEARCH_LIMIT"],
        )
        offset = parse_positive_int(request.args.get("offset"), default=0)

        available_seasons: list[int] = []
        selected_season: int | None = None
        team_options: list[dict[str, str]] = []
        selected_team = request.args.get("team", "").strip().upper()
        games: list[dict[str, Any]] = []
        total_count = 0

        if database_path.exists():
            with open_database(database_path) as connection:
                if resolve_table_reference(connection, "stage_nfl", "game_teams") is None:
                    abort(404)

                available_seasons = load_available_seasons(connection)
                selected_season = choose_selected_season(request.args.get("season"), available_seasons)
                team_options = load_team_options(connection, selected_season)

                if selected_team:
                    games, total_count = search_team_games(
                        connection,
                        season=selected_season,
                        team=selected_team,
                        limit=limit,
                        offset=offset,
                    )

        return render_template(
            "teams.html",
            active_page="teams",
            available_seasons=available_seasons,
            selected_season=selected_season,
            team_options=team_options,
            selected_team=selected_team,
            games=games,
            total_count=total_count,
            result_start=offset + 1 if total_count > 0 else 0,
            result_end=min(offset + limit, total_count),
            limit=limit,
            offset=offset,
            has_previous=offset > 0,
            has_next=offset + limit < total_count,
            previous_url=build_page_url(
                "team_search",
                season=selected_season,
                team=selected_team,
                limit=limit,
                offset=max(offset - limit, 0),
            ),
            next_url=build_page_url(
                "team_search",
                season=selected_season,
                team=selected_team,
                limit=limit,
                offset=offset + limit,
            ),
        )

    @app.get("/weeks")
    def week_search() -> str:
        database_path = Path(app.config["DATABASE_PATH"])
        limit = parse_positive_int(
            request.args.get("limit"),
            default=app.config["DEFAULT_SEARCH_LIMIT"],
            maximum=app.config["MAX_SEARCH_LIMIT"],
        )
        offset = parse_positive_int(request.args.get("offset"), default=0)

        available_seasons: list[int] = []
        selected_season: int | None = None
        available_weeks: list[int] = []
        selected_week: int | None = None
        games: list[dict[str, Any]] = []
        total_count = 0

        if database_path.exists():
            with open_database(database_path) as connection:
                if resolve_table_reference(connection, "stage_nfl", "games") is None:
                    abort(404)

                available_seasons = load_available_seasons(connection)
                selected_season = choose_selected_season(request.args.get("season"), available_seasons)
                available_weeks = load_available_weeks(connection, selected_season)
                selected_week = choose_selected_week(request.args.get("week"), available_weeks)

                if selected_week is not None:
                    games, total_count = search_week_games(
                        connection,
                        season=selected_season,
                        week=selected_week,
                        limit=limit,
                        offset=offset,
                    )

        return render_template(
            "weeks.html",
            active_page="weeks",
            available_seasons=available_seasons,
            selected_season=selected_season,
            available_weeks=available_weeks,
            selected_week=selected_week,
            games=games,
            total_count=total_count,
            result_start=offset + 1 if total_count > 0 else 0,
            result_end=min(offset + limit, total_count),
            limit=limit,
            offset=offset,
            has_previous=offset > 0,
            has_next=offset + limit < total_count,
            previous_url=build_page_url(
                "week_search",
                season=selected_season,
                week=selected_week,
                limit=limit,
                offset=max(offset - limit, 0),
            ),
            next_url=build_page_url(
                "week_search",
                season=selected_season,
                week=selected_week,
                limit=limit,
                offset=offset + limit,
            ),
        )

    @app.get("/schema/<schema_name>")
    def schema_detail(schema_name: str) -> str:
        if schema_name not in app.config["VISIBLE_SCHEMAS"]:
            abort(404)

        database_path = Path(app.config["DATABASE_PATH"])
        if not database_path.exists():
            abort(404)

        browser_state = load_browser_state(database_path, tuple(app.config["VISIBLE_SCHEMAS"]))
        schema_tables = browser_state["tables_by_schema"].get(schema_name, [])

        if not schema_tables:
            abort(404)

        schema_summary = next(
            (summary for summary in browser_state["schema_summaries"] if summary["schema_name"] == schema_name),
            None,
        )

        return render_template(
            "schema.html",
            active_page="schema",
            active_schema=schema_name,
            schema_name=schema_name,
            schema_summary=schema_summary,
            schema_tables=schema_tables,
        )

    @app.get("/table/<schema_name>/<table_name>")
    def table_detail(schema_name: str, table_name: str) -> str:
        database_path = Path(app.config["DATABASE_PATH"])
        if not database_path.exists():
            abort(404)

        with open_database(database_path) as connection:
            table_ref = resolve_table_reference(connection, schema_name, table_name)
            if table_ref is None:
                abort(404)

            limit = parse_positive_int(
                request.args.get("limit"),
                default=app.config["DEFAULT_PREVIEW_LIMIT"],
                maximum=app.config["MAX_PREVIEW_LIMIT"],
            )
            offset = parse_positive_int(request.args.get("offset"), default=0)
            columns = describe_table(connection, schema_name, table_name)
            rows = preview_rows(connection, schema_name, table_name, limit=limit, offset=offset)
            row_count = count_rows(connection, schema_name, table_name)

        previous_offset = max(offset - limit, 0)
        next_offset = offset + limit

        return render_template(
            "table.html",
            active_page="table",
            active_schema=schema_name,
            active_table=table_name,
            schema_name=schema_name,
            table_name=table_name,
            columns=columns,
            rows=rows,
            row_count=row_count,
            column_count=len(columns),
            preview_start=offset + 1 if row_count > 0 else 0,
            preview_end=min(offset + limit, row_count),
            limit=limit,
            offset=offset,
            has_previous=offset > 0,
            has_next=next_offset < row_count,
            previous_url=url_for("table_detail", schema_name=schema_name, table_name=table_name, limit=limit, offset=previous_offset),
            next_url=url_for("table_detail", schema_name=schema_name, table_name=table_name, limit=limit, offset=next_offset),
            table_type=table_ref["table_type"],
            featured_columns=columns[:8],
        )

    @app.get("/health")
    def health() -> tuple[dict[str, str], int]:
        database_path = Path(app.config["DATABASE_PATH"])
        status = "ok" if database_path.exists() else "missing_database"
        return {"status": status}, 200

    return app


def open_database(database_path: Path) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(database_path), read_only=True)


def load_browser_state(database_path: Path, visible_schemas: tuple[str, ...]) -> dict[str, Any]:
    if not database_path.exists():
        return {
            "database_missing": True,
            "tables_by_schema": {schema: [] for schema in visible_schemas},
            "schema_summaries": [],
            "overview_metrics": {
                "visible_schema_count": len(visible_schemas),
                "visible_table_count": 0,
                "stage_row_count": 0,
                "raw_file_count": 0,
            },
        }

    tables_by_schema = load_tables(database_path, visible_schemas)
    schema_summaries = build_schema_summaries(tables_by_schema)

    return {
        "database_missing": False,
        "tables_by_schema": tables_by_schema,
        "schema_summaries": schema_summaries,
        "overview_metrics": {
            "visible_schema_count": len(visible_schemas),
            "visible_table_count": sum(len(tables) for tables in tables_by_schema.values()),
            "stage_row_count": sum(table.get("row_count") or 0 for table in tables_by_schema.get("stage_nfl", [])),
            "raw_file_count": sum(table.get("file_count") or 0 for table in tables_by_schema.get("raw_nfl", [])),
        },
    }


def load_tables(database_path: Path, visible_schemas: tuple[str, ...]) -> dict[str, list[dict[str, Any]]]:
    with open_database(database_path) as connection:
        rows = connection.execute(
            """
            SELECT table_schema, table_name, table_type
            FROM information_schema.tables
            WHERE table_schema IN (?, ?, ?)
            ORDER BY
              CASE table_schema
                WHEN 'stage_nfl' THEN 1
                WHEN 'raw_nfl' THEN 2
                WHEN 'admin' THEN 3
                ELSE 4
              END,
              table_name
            """,
            list(visible_schemas),
        ).fetchall()

        tables_by_schema: dict[str, list[dict[str, Any]]] = {schema: [] for schema in visible_schemas}
        stage_counts = load_table_counts(connection, "admin", "stage_build_inventory", "table_name", "row_count")
        raw_counts = load_table_counts(connection, "admin", "ingestion_inventory", "table_name", None)

        for schema_name, table_name, table_type in rows:
            row_count = None
            if schema_name == "stage_nfl":
                row_count = stage_counts.get(table_name)
            elif schema_name == "admin":
                row_count = count_rows(connection, schema_name, table_name)

            file_count = raw_counts.get(table_name) if schema_name == "raw_nfl" else None

            tables_by_schema[schema_name].append(
                {
                    "schema_name": schema_name,
                    "table_name": table_name,
                    "table_type": table_type,
                    "row_count": row_count,
                    "file_count": file_count,
                }
            )

        return tables_by_schema


def build_schema_summaries(tables_by_schema: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []

    for schema_name, tables in tables_by_schema.items():
        summaries.append(
            {
                "schema_name": schema_name,
                "label": SCHEMA_META[schema_name]["label"],
                "description": SCHEMA_META[schema_name]["description"],
                "accent": SCHEMA_META[schema_name]["accent"],
                "table_count": len(tables),
                "row_count_total": sum(table.get("row_count") or 0 for table in tables),
                "file_count_total": sum(table.get("file_count") or 0 for table in tables),
                "tables": tables,
            }
        )

    return summaries


def load_table_counts(
    connection: duckdb.DuckDBPyConnection,
    schema_name: str,
    table_name: str,
    key_column: str,
    value_column: str | None,
) -> dict[str, int]:
    if resolve_table_reference(connection, schema_name, table_name) is None:
        return {}

    if value_column is None:
        rows = connection.execute(
            f'SELECT "{key_column}", file_count FROM "{schema_name}"."{table_name}"'
        ).fetchall()
    else:
        rows = connection.execute(
            f'SELECT "{key_column}", "{value_column}" FROM "{schema_name}"."{table_name}"'
        ).fetchall()

    return {row[0]: int(row[1]) for row in rows}


def resolve_table_reference(
    connection: duckdb.DuckDBPyConnection, schema_name: str, table_name: str
) -> dict[str, str] | None:
    row = connection.execute(
        """
        SELECT table_schema, table_name, table_type
        FROM information_schema.tables
        WHERE table_schema = ? AND table_name = ?
        """,
        [schema_name, table_name],
    ).fetchone()

    if row is None:
        return None

    return {"table_schema": row[0], "table_name": row[1], "table_type": row[2]}


def describe_table(
    connection: duckdb.DuckDBPyConnection, schema_name: str, table_name: str
) -> list[dict[str, str]]:
    rows = connection.execute(
        f'DESCRIBE SELECT * FROM "{schema_name}"."{table_name}"'
    ).fetchall()
    return [{"name": row[0], "type": row[1], "null": row[2]} for row in rows]


def preview_rows(
    connection: duckdb.DuckDBPyConnection,
    schema_name: str,
    table_name: str,
    *,
    limit: int,
    offset: int,
) -> list[dict[str, Any]]:
    cursor = connection.execute(
        f'SELECT * FROM "{schema_name}"."{table_name}" LIMIT ? OFFSET ?',
        [limit, offset],
    )
    columns = [column[0] for column in cursor.description]
    rows = cursor.fetchall()
    return [dict(zip(columns, row, strict=False)) for row in rows]


def count_rows(connection: duckdb.DuckDBPyConnection, schema_name: str, table_name: str) -> int:
    return int(
        connection.execute(f'SELECT COUNT(*) FROM "{schema_name}"."{table_name}"').fetchone()[0]
    )


def build_page_url(endpoint: str, **params: Any) -> str:
    filtered_params = {
        key: value
        for key, value in params.items()
        if value is not None and value != ""
    }
    return url_for(endpoint, **filtered_params)


def load_available_seasons(connection: duckdb.DuckDBPyConnection) -> list[int]:
    rows = connection.execute(
        """
        SELECT DISTINCT season
        FROM stage_nfl.games
        ORDER BY season DESC
        """
    ).fetchall()
    return [int(row[0]) for row in rows]


def choose_selected_season(raw_value: str | None, available_seasons: list[int]) -> int | None:
    if not available_seasons:
        return None

    parsed = parse_positive_int(raw_value, default=available_seasons[0]) if raw_value else None
    if parsed in available_seasons:
        return parsed

    return available_seasons[0]


def load_available_weeks(connection: duckdb.DuckDBPyConnection, season: int | None) -> list[int]:
    if season is None:
        return []

    rows = connection.execute(
        """
        SELECT DISTINCT week
        FROM stage_nfl.games
        WHERE season = ?
        ORDER BY week
        """,
        [season],
    ).fetchall()
    return [int(row[0]) for row in rows if row[0] is not None]


def choose_selected_week(raw_value: str | None, available_weeks: list[int]) -> int | None:
    if not available_weeks:
        return None

    parsed = parse_positive_int(raw_value, default=available_weeks[0]) if raw_value else None
    if parsed in available_weeks:
        return parsed

    return available_weeks[0]


def load_team_options(connection: duckdb.DuckDBPyConnection, season: int | None) -> list[dict[str, str]]:
    if season is None:
        return []

    rows = connection.execute(
        """
        SELECT DISTINCT
          gt.team,
          coalesce(t.team_full_name, t.team_name, gt.team) AS team_label
        FROM stage_nfl.game_teams AS gt
        LEFT JOIN stage_nfl.teams AS t
          ON gt.team = t.team
        WHERE gt.season = ?
        ORDER BY gt.team
        """,
        [season],
    ).fetchall()

    return [{"team": row[0], "label": row[1]} for row in rows]


def search_players(
    connection: duckdb.DuckDBPyConnection,
    *,
    search_query: str,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    where_clause, params = build_player_search_clause(search_query)

    rows = connection.execute(
        f"""
        SELECT
          player_id,
          gsis_id,
          display_name,
          position,
          latest_team,
          rookie_season,
          status
        FROM stage_nfl.players
        {where_clause}
        ORDER BY coalesce(display_name, short_name, gsis_id), gsis_id
        LIMIT ? OFFSET ?
        """,
        [*params, limit, offset],
    ).fetchall()

    total_count = int(
        connection.execute(
            f"""
            SELECT COUNT(*)
            FROM stage_nfl.players
            {where_clause}
            """,
            params,
        ).fetchone()[0]
    )

    return (
        [
            {
                "player_id": row[0],
                "gsis_id": row[1],
                "display_name": row[2],
                "position": row[3],
                "latest_team": row[4],
                "rookie_season": row[5],
                "status": row[6],
            }
            for row in rows
        ],
        total_count,
    )


def build_player_search_clause(search_query: str) -> tuple[str, list[str]]:
    trimmed_query = search_query.strip().lower()
    if not trimmed_query:
        return "", []

    like_query = f"%{trimmed_query}%"
    params = [like_query, like_query, like_query, like_query, like_query]
    return (
        """
        WHERE
          lower(coalesce(display_name, '')) LIKE ?
          OR lower(coalesce(short_name, '')) LIKE ?
          OR lower(trim(coalesce(first_name, '') || ' ' || coalesce(last_name, ''))) LIKE ?
          OR lower(coalesce(gsis_id, '')) LIKE ?
          OR lower(coalesce(latest_team, '')) LIKE ?
        """,
        params,
    )


def search_team_games(
    connection: duckdb.DuckDBPyConnection,
    *,
    season: int | None,
    team: str,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    if season is None or not team:
        return [], 0

    rows = connection.execute(
        """
        SELECT
          game_id,
          week,
          game_date,
          home_away,
          opponent_team,
          team_result,
          team_score,
          opponent_score,
          point_diff
        FROM stage_nfl.game_teams
        WHERE season = ? AND team = ?
        ORDER BY week, game_date, game_id
        LIMIT ? OFFSET ?
        """,
        [season, team, limit, offset],
    ).fetchall()

    total_count = int(
        connection.execute(
            """
            SELECT COUNT(*)
            FROM stage_nfl.game_teams
            WHERE season = ? AND team = ?
            """,
            [season, team],
        ).fetchone()[0]
    )

    return (
        [
            {
                "game_id": row[0],
                "week": row[1],
                "game_date": row[2],
                "home_away": row[3],
                "opponent_team": row[4],
                "team_result": row[5],
                "team_score": row[6],
                "opponent_score": row[7],
                "point_diff": row[8],
            }
            for row in rows
        ],
        total_count,
    )


def search_week_games(
    connection: duckdb.DuckDBPyConnection,
    *,
    season: int | None,
    week: int,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    if season is None:
        return [], 0

    rows = connection.execute(
        """
        SELECT
          game_id,
          game_date,
          away_team,
          away_score,
          home_team,
          home_score,
          stadium,
          is_completed
        FROM stage_nfl.games
        WHERE season = ? AND week = ?
        ORDER BY game_date, game_id
        LIMIT ? OFFSET ?
        """,
        [season, week, limit, offset],
    ).fetchall()

    total_count = int(
        connection.execute(
            """
            SELECT COUNT(*)
            FROM stage_nfl.games
            WHERE season = ? AND week = ?
            """,
            [season, week],
        ).fetchone()[0]
    )

    return (
        [
            {
                "game_id": row[0],
                "game_date": row[1],
                "away_team": row[2],
                "away_score": row[3],
                "home_team": row[4],
                "home_score": row[5],
                "stadium": row[6],
                "is_completed": row[7],
            }
            for row in rows
        ],
        total_count,
    )


def parse_positive_int(raw_value: str | None, *, default: int, maximum: int | None = None) -> int:
    if raw_value is None or raw_value == "":
        return default

    try:
        value = int(raw_value)
    except ValueError:
        return default

    if value < 0:
        return default

    if maximum is not None:
        return min(value, maximum)

    return value


app = create_app()
