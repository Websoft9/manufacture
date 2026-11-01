from __future__ import annotations

import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "ci/scripts/opencode_clear.py"


class OpenCodeClearTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Path(self.temp_dir.name) / "opencode.db"
        self.create_database()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def create_database(self) -> None:
        with sqlite3.connect(self.database) as connection:
            connection.executescript(
                """
                CREATE TABLE session (
                    id TEXT PRIMARY KEY,
                    parent_id TEXT,
                    title TEXT,
                    directory TEXT,
                    time_created INTEGER
                );
                CREATE TABLE message (session_id TEXT, body TEXT);
                CREATE TABLE event (aggregate_id TEXT, body TEXT);
                INSERT INTO session VALUES ('root', NULL, 'Root', '/repo', 1000);
                INSERT INTO session VALUES ('child', 'root', 'Child', '/repo/sub', 2000);
                INSERT INTO session VALUES ('other', NULL, 'Other', '/other', 3000);
                INSERT INTO message VALUES ('root', 'root message');
                INSERT INTO message VALUES ('child', 'child message');
                INSERT INTO message VALUES ('other', 'other message');
                INSERT INTO event VALUES ('root', 'root event');
                INSERT INTO event VALUES ('child', 'child event');
                INSERT INTO event VALUES ('other', 'other event');
                """
            )

    def run_script(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--db", str(self.database), *args],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_dry_run_does_not_delete(self) -> None:
        result = self.run_script("--directory", "/repo", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("2 session(s)", result.stdout)
        with sqlite3.connect(self.database) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM session").fetchone()[0], 3)

    def test_delete_is_scoped_to_directory_and_child_sessions(self) -> None:
        result = self.run_script("--directory", "/repo", "--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        with sqlite3.connect(self.database) as connection:
            self.assertEqual(
                connection.execute("SELECT id FROM session ORDER BY id").fetchall(),
                [("other",)],
            )
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM message").fetchone()[0], 1)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM event").fetchone()[0], 1)

    def test_non_interactive_delete_requires_confirmation_flag(self) -> None:
        result = self.run_script("--directory", "/repo")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("without --yes", result.stderr)


if __name__ == "__main__":
    unittest.main()
