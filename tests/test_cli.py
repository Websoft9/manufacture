from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from click.testing import CliRunner

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cli.cli import cli  # noqa: E402
from cli.marketplace import END_MARKER, START_MARKER  # noqa: E402


class ListCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp_dir.name)
        self.offer = self.directory / "offer.json"
        self.catalog = self.directory / "product_en.json"
        self.offer.write_text(
            json.dumps(
                [
                    {
                        "id": "elasticsearch",
                        "type": "app",
                        "applications": ["elasticsearch"],
                        "productID": {"aws": ["sku-elastic"]},
                    }
                ]
            ),
            encoding="utf-8",
        )
        self.catalog.write_text(
            json.dumps(
                [
                    {"key": "elasticsearch", "trademark": "Elasticsearch"},
                    {"key": "affine", "trademark": "AFFiNE"},
                ]
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def invoke(self, *args: str):
        return self.runner.invoke(
            cli,
            [
                "list",
                "--offer",
                str(self.offer),
                "--catalog",
                str(self.catalog),
                *args,
            ],
        )

    def test_list_prints_the_markdown_table(self) -> None:
        result = self.invoke()

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn(
            "| 应用 | 阿里云 | Alibaba Cloud | 华为云 | Huawei Cloud | Azure | AWS |",
            result.output,
        )
        self.assertIn("Elasticsearch", result.output)
        self.assertIn("AFFiNE", result.output)
        self.assertIn(
            "[sku-elastic](https://aws.amazon.com/marketplace/pp?sku=sku-elastic)",
            result.output,
        )

    def test_list_updates_readme_in_place(self) -> None:
        readme = self.directory / "README.md"
        readme.write_text(
            f"# Project\n\n{START_MARKER}\nold\n{END_MARKER}\n",
            encoding="utf-8",
        )

        result = self.invoke("--update-readme", str(readme))

        self.assertEqual(result.exit_code, 0, result.output)
        updated = readme.read_text(encoding="utf-8")
        self.assertIn("Elasticsearch", updated)
        self.assertIn("AFFiNE", updated)
        self.assertNotIn("old", updated)

    def test_help_lists_the_command(self) -> None:
        result = self.runner.invoke(cli, ["--help"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("list", result.output)


if __name__ == "__main__":
    unittest.main()
