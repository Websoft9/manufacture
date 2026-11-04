from __future__ import annotations

import json
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from click.testing import CliRunner

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cli.cli import cli  # noqa: E402
from cli.marketplace import END_MARKER, START_MARKER  # noqa: E402
from cli.commands import versions as versions_module  # noqa: E402
from cli.versioning import extract_marketplace_version, extract_summary_version  # noqa: E402


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
            "| 应用 | Azure | Azure (by VMLab) | AWS | 阿里云 | Alibaba Cloud | 华为云 | Huawei Cloud |",
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

    def test_help_command_matches_help_options(self) -> None:
        outputs = [
            self.runner.invoke(cli, args).output
            for args in (["help"], ["-h"], ["--help"])
        ]

        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(outputs[0], outputs[2])


class VersionsCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.offer = Path(self.temp_dir.name) / "offer.json"
        self.offer.write_text(
            json.dumps(
                [
                    {
                        "id": "moodle",
                        "type": "app",
                        "productID": {"aliyun": ["cmjj-one", "cmjj-two"], "aws": ["ignored"]},
                    },
                    {"id": "not-app", "type": "solution", "productID": {"aliyun": ["ignored"]}},
                ]
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_versions_queries_selected_cloud_codes_and_renders_result(self) -> None:
        calls: list[str] = []

        def fake_fetch(code: str, timeout: float = 30) -> dict[str, object]:
            calls.append(code)
            return {
                "Name": f"Moodle {code}",
                "ShortDescription": "Moodle 5.2 on Ubuntu 24.04",
            }

        with mock.patch.object(versions_module, "fetch_aliyun_product", fake_fetch):
            result = self.runner.invoke(
                cli,
                ["versions", "--platform", "aliyun", "--offer", str(self.offer)],
            )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(calls, ["cmjj-one", "cmjj-two"])
        self.assertIn("| 商品名称 | 应用 | code | 版本 |", result.output)
        self.assertIn("| Moodle cmjj-one | moodle | cmjj-one | 5.2 |", result.output)

    def test_versions_rejects_unimplemented_cloud(self) -> None:
        result = self.runner.invoke(cli, ["versions", "--platform", "aws", "--offer", str(self.offer)])

        self.assertEqual(result.exit_code, 1)
        self.assertIn("currently supported: aliyun", result.output)

    def test_extract_version_uses_app_context(self) -> None:
        self.assertEqual(
            versions_module.extract_version("Ubuntu 24.04 with Moodle 5.2.1", "moodle"),
            "5.2.1",
        )
        self.assertEqual(
            versions_module.extract_version("Ubuntu 24.04, ONLYOFFICE Docs 9.0", "onlyofficedocs"),
            "9.0",
        )
        self.assertIsNone(versions_module.extract_version("Ubuntu 24.04, preinstalled image", "moodle"))

    def test_extract_summary_version_ignores_os_versions(self) -> None:
        self.assertEqual(
            extract_summary_version("Moodle 5.2.1 on Ubuntu 24.04", "Moodle（Linux）"),
            "5.2.1",
        )
        self.assertEqual(
            extract_summary_version("ONLYOFFICE Docs 9.0 on Ubuntu 24.04", "ONLYOFFICE Docs（Linux）"),
            "9.0",
        )
        self.assertIsNone(
            extract_summary_version("Moodle on Ubuntu 24.04", "Moodle（Linux）")
        )
        self.assertEqual(
            extract_summary_version("Moodle for JavaScript 5.2", "Moodle"),
            "5.2",
        )

    def test_extract_marketplace_version_from_first_comma_clause(self) -> None:
        cases = [
            ("Moodle v5.2, preconfigured & hardened", "Moodle - Preconfigured", "Moodle", "5.2"),
            ("WordPress 7.1 with Varnish, Redis for static performance", "WordPress - Ready", "WordPress", "7.1"),
            ("ONLYOFFICE Docs CE v9, preconfigured", "ONLYOFFICE Docs - Ready", "ONLYOFFICE Docs", "9"),
            ("n8n v2.38, preconfigured & hardened", "Workflow Automation - Ready", "n8n", "2.38"),
            ("WordPress 7.1 镜像，内置管理面板", "WordPress 企业建站平台", "WordPress", "7.1"),
            ("由 Websoft9 提供的 Oracle Linux 7.9 桌面环境", "Oracle Linux 7.9 Desktop", "Oracle Linux", "7.9"),
            ("Moodle 最新版, 提供运维支持", "Moodle - Ready", "Moodle", None),
            ("Moodle v5.2, Ubuntu 24.04", "Moodle - Ready", "Moodle", "5.2"),
            # Digits embedded in the trademark are not versions.
            ("TYPO3 v13.4 preconfigured & hardened", "TYPO3 - Ready", "TYPO3", "13.4"),
            ("Neo4j v2026.07 preconfigured", "Neo4j - Ready", "Neo4j", "2026.07"),
            ("Websoft9 platform for hosting", "Websoft9 Apps Hosting Platform", "Websoft9", None),
            # Trademark differs between the marketing title and the summary.
            ("开机即用 ERPNext 16 镜像", "ERPNext 开源企业 ERP/CRM", "ERPNext", "16"),
            ("开机即用 Odoo19/18/17/16 镜像", "Odoo 开源企业 ERP/CRM", "Odoo", "19"),
            ("开机即用 n8n v2.38 镜像", "Workflow Automation 平台", "Workflow Automation", "2.38"),
            # Fall back to a version written in the title.
            ("Pre-configured image", "Cloud Native Database for MySQL 5.7", None, "5.7"),
            ("Pre-configured image", "PHP 7.4 Runtime on CentOS (LAMP)", None, "7.4"),
            ("Pre-configured image", "Canvas 在线学习平台", None, None),
        ]

        for summary, title, app_name, expected in cases:
            with self.subTest(summary=summary, title=title):
                self.assertEqual(
                    extract_marketplace_version(summary, title, app_name),
                    expected,
                )


if __name__ == "__main__":
    unittest.main()
