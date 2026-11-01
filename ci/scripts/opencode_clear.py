#!/usr/bin/env python3
"""List and safely clear OpenCode sessions from the local database."""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path


def default_db_path() -> Path:
    data_dir = os.environ.get("OPENCODE_DATA_DIR")
    if data_dir:
        return Path(data_dir) / "opencode.db"
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/opencode/opencode.db"
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
        return base / "opencode/opencode.db"
    return Path.home() / ".local/share/opencode/opencode.db"


def columns(connection: sqlite3.Connection, table: str) -> set[str]:
    quoted = table.replace('"', '""')
    return {row[1] for row in connection.execute(f'PRAGMA table_info("{quoted}")')}


def selected_sessions(
    connection: sqlite3.Connection, directory: Path | None
) -> list[sqlite3.Row]:
    session_columns = columns(connection, "session")
    if "id" not in session_columns:
        raise sqlite3.DatabaseError("OpenCode session table has no id column")

    fields = ["id"]
    for optional in ("title", "directory", "parent_id", "time_created"):
        if optional in session_columns:
            fields.append(optional)
    query = f"SELECT {', '.join(fields)} FROM session"
    params: tuple[str, ...] = ()
    if directory is not None:
        if "directory" not in session_columns:
            raise sqlite3.DatabaseError("OpenCode session table has no directory column")
        query += " WHERE directory = ?"
        params = (str(directory),)
    query += " ORDER BY " + ("time_created" if "time_created" in session_columns else "id")
    roots = connection.execute(query, params).fetchall()

    ids = {row["id"] for row in roots}
    connection.execute("CREATE TEMP TABLE selected_session (id TEXT PRIMARY KEY)")
    if ids:
        connection.executemany(
            "INSERT OR IGNORE INTO selected_session (id) VALUES (?)",
            ((session_id,) for session_id in ids),
        )
    if "parent_id" in session_columns and ids:
        connection.execute(
            """
            WITH RECURSIVE descendants (id) AS (
                SELECT id FROM selected_session
                UNION
                SELECT child.id
                FROM session AS child
                JOIN descendants ON child.parent_id = descendants.id
            )
            INSERT OR IGNORE INTO selected_session (id)
            SELECT id FROM descendants
            """
        )
        ids.update(
            row["id"]
            for row in connection.execute("SELECT id FROM selected_session")
        )
    if not ids:
        return []

    placeholders = ",".join("?" for _ in ids)
    return connection.execute(
        f"SELECT {', '.join(fields)} FROM session WHERE id IN ({placeholders}) ORDER BY "
        + ("time_created" if "time_created" in session_columns else "id"),
        tuple(ids),
    ).fetchall()


def format_created(value: object) -> str:
    try:
        timestamp = float(value)
        if timestamp > 10_000_000_000:
            timestamp /= 1000
        return datetime.fromtimestamp(timestamp, timezone.utc).strftime("%Y-%m-%d %H:%M")
    except (TypeError, ValueError, OSError):
        return "unknown"


def display(sessions: list[sqlite3.Row], directory: Path | None) -> None:
    if not sessions:
        print("No sessions found.")
        return
    print(f"{len(sessions)} session(s)")
    for session in sessions:
        title = session["title"] if "title" in session.keys() else ""
        created = format_created(session["time_created"]) if "time_created" in session.keys() else "unknown"
        session_id = session["id"]
        session_directory = session["directory"] if "directory" in session.keys() else str(directory or "")
        print(f"{created}  {session_id}  {title or '(untitled)'}  {session_directory}")


def delete_sessions(connection: sqlite3.Connection) -> int:
    tables = {
        row[0]
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    session_ids = [
        row["id"] for row in connection.execute("SELECT id FROM selected_session")
    ]
    if not session_ids:
        return 0
    placeholders = ",".join("?" for _ in session_ids)
    with connection:
        for table in sorted(tables):
            if table in {"session", "selected_session"}:
                continue
            table_columns = columns(connection, table)
            if "aggregate_id" in table_columns and table in {"event", "event_sequence"}:
                quoted = table.replace('"', '""')
                connection.execute(
                    f'DELETE FROM "{quoted}" WHERE aggregate_id IN ({placeholders})',
                    tuple(session_ids),
                )
            elif "session_id" in table_columns:
                quoted = table.replace('"', '""')
                connection.execute(
                    f'DELETE FROM "{quoted}" WHERE session_id IN ({placeholders})',
                    tuple(session_ids),
                )
        cursor = connection.execute(
            f"DELETE FROM session WHERE id IN ({placeholders})", tuple(session_ids)
        )
    return cursor.rowcount


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, help="database path (default: detect OpenCode data directory)")
    parser.add_argument("--all", action="store_true", help="include sessions from all directories")
    parser.add_argument("--directory", type=Path, help="limit sessions to this directory (default: current directory)")
    parser.add_argument("--dry-run", action="store_true", help="list selected sessions without deleting")
    parser.add_argument("--yes", action="store_true", help="skip confirmation (required in non-interactive use)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    database = (args.db or default_db_path()).expanduser()
    directory = None if args.all else (args.directory or Path.cwd()).expanduser().resolve()
    if not database.is_file():
        print(f"error: OpenCode database not found: {database}", file=sys.stderr)
        return 1

    try:
        connection = sqlite3.connect(database)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
    except sqlite3.Error as error:
        print(f"error: could not open OpenCode database: {error}", file=sys.stderr)
        return 1

    try:
        sessions = selected_sessions(connection, directory)
        display(sessions, directory)
        if not sessions or args.dry_run:
            return 0
        if not args.yes:
            if not sys.stdin.isatty():
                print("error: refusing to delete without --yes in a non-interactive shell", file=sys.stderr)
                return 1
            try:
                answer = input(f"Delete these {len(sessions)} session(s) and their data? [y/N] ")
            except (EOFError, KeyboardInterrupt):
                print("\nAborted; nothing was deleted.")
                return 0
            if answer.strip().lower() not in {"y", "yes"}:
                print("Aborted; nothing was deleted.")
                return 0

        deleted = delete_sessions(connection)
        print(f"Deleted {deleted} session(s).")
        return 0
    except sqlite3.Error as error:
        print(f"error: OpenCode database operation failed: {error}", file=sys.stderr)
        return 1
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
