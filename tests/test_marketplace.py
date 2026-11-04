from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cli import marketplace as app_list  # noqa: E402


class ConfigTests(unittest.TestCase):
    def test_marketplace_config_is_complete(self) -> None:
        config = app_list.CONFIG
        self.assertTrue(config["sources"]["offer"].startswith("https://"))
        self.assertTrue(config["sources"]["catalog"].startswith("https://"))
        self.assertTrue(config["sources"]["versions"].startswith("https://"))

        product_platforms = tuple(
            item["key"] for item in config["platforms"] if item.get("urlTemplate")
        )
        self.assertEqual(product_platforms, app_list.PLATFORMS)

        all_platforms = {item["key"] for item in config["platforms"]}
        for platform in config["platforms"]:
            if platform.get("urlTemplate"):
                self.assertIn("{code}", platform["urlTemplate"])
            for store in platform.get("stores", []):
                self.assertTrue(store["url"].startswith("https://"), store["url"])

        for source, route in config["routing"].items():
            self.assertIn(route["default"], all_platforms, source)
            for rule in route.get("rules", []):
                self.assertIn(rule["platform"], all_platforms, source)


class LinkTests(unittest.TestCase):
    def test_aliyun_codes_route_to_china_and_international_marketplaces(self) -> None:
        self.assertEqual(
            app_list.product_url("aliyun", "cmjj00038106"),
            ("aliyun", "https://market.aliyun.com/detail/cmjj00038106"),
        )
        self.assertEqual(
            app_list.product_url("aliyun", "sgcmjj00035225"),
            (
                "alibabacloud",
                "https://marketplace.alibabacloud.com/products/201072001/sgcmjj00035225.html",
            ),
        )
        self.assertEqual(
            app_list.product_url("alibabacloud", "sgcmjj00035225"),
            (
                "alibabacloud",
                "https://marketplace.alibabacloud.com/products/201072001/sgcmjj00035225.html",
            ),
        )

    def test_huawei_links_support_china_and_international_sites(self) -> None:
        self.assertEqual(
            app_list.product_url("huaweiyun", "abc"),
            ("huaweiyun", "https://marketplace.huaweicloud.com/contents/abc"),
        )
        self.assertEqual(
            app_list.product_url("huaweicloud", "abc"),
            ("huaweicloud", "https://marketplace.huaweicloud.com/intl/contents/abc"),
        )

    def test_azure_split_and_aws_links_use_product_codes(self) -> None:
        self.assertEqual(
            app_list.product_url("azure", "vmlabinc1613642184700.moodle"),
            (
                "azure-vmlab",
                "https://azuremarketplace.microsoft.com/en-us/marketplace/apps/vmlabinc1613642184700.moodle",
            ),
        )
        self.assertEqual(
            app_list.product_url("azure", "websoft9inc.moodle"),
            (
                "azure",
                "https://azuremarketplace.microsoft.com/en-us/marketplace/apps/websoft9inc.moodle",
            ),
        )
        self.assertEqual(
            app_list.product_url("aws", "abc123"),
            ("aws", "https://aws.amazon.com/marketplace/pp?sku=abc123"),
        )


class CollectRowsTests(unittest.TestCase):
    def test_apps_are_matched_by_offer_id_and_catalog_trademark(self) -> None:
        offers = [
            {
                "id": "elasticsearch",
                "type": "app",
                "applications": ["elasticsearch"],
                "productID": {
                    "aws": ["aws-1"],
                    "aliyun": ["cmjj1", "sgcmjj2"],
                    "azure": ["websoft9inc.elasticsearch"],
                },
            },
            {
                "id": "not-an-app",
                "type": "solution",
                "productID": {"aws": ["ignored"]},
            },
        ]
        catalog = [
            {"key": "elasticsearch", "trademark": "Elasticsearch"},
            {"key": "affine", "trademark": "AFFiNE"},
        ]

        rows = app_list.collect_rows(offers, catalog)
        by_key = {row.key: row for row in rows}

        self.assertEqual([row.key for row in rows], ["affine", "elasticsearch"])
        self.assertEqual(by_key["elasticsearch"].name, "Elasticsearch")
        self.assertEqual(
            by_key["elasticsearch"].links["aliyun"],
            [("cmjj1", "https://market.aliyun.com/detail/cmjj1")],
        )
        self.assertEqual(
            by_key["elasticsearch"].links["alibabacloud"],
            [
                (
                    "sgcmjj2",
                    "https://marketplace.alibabacloud.com/products/201072001/sgcmjj2.html",
                )
            ],
        )
        self.assertFalse(by_key["affine"].has_links)
        self.assertTrue(by_key["affine"].in_catalog)

    def test_offers_without_catalog_entries_are_kept(self) -> None:
        offers = [
            {
                "id": "tomcat",
                "type": "app",
                "applications": ["tomcat"],
                "productID": {"aws": ["aws-tomcat"]},
            }
        ]
        rows = app_list.collect_rows(offers, [])

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].name, "tomcat")
        self.assertFalse(rows[0].in_catalog)
        self.assertTrue(rows[0].has_links)


class RenderTests(unittest.TestCase):
    def test_markdown_contains_listed_and_unlisted_apps(self) -> None:
        rows = [
            app_list.AppRow(
                key="elasticsearch",
                name="Elasticsearch",
                links={"aws": [("sku", "https://aws.example/sku")]},
            ),
            app_list.AppRow(key="affine", name="AFFiNE"),
        ]

        markdown = app_list.render_markdown(rows)

        self.assertIn(app_list.START_MARKER, markdown)
        self.assertIn("Elasticsearch", markdown)
        self.assertIn("[sku](https://aws.example/sku)", markdown)
        self.assertIn("未在 Marketplace 找到商品的应用", markdown)
        self.assertIn("- AFFiNE", markdown)

    def test_update_readme_replaces_only_the_generated_section(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            readme = Path(directory) / "README.md"
            readme.write_text(
                "# Project\n\nIntro\n\n"
                f"{app_list.START_MARKER}\nold\n{app_list.END_MARKER}\n\nFooter\n",
                encoding="utf-8",
            )

            changed = app_list.update_readme(
                readme,
                f"{app_list.START_MARKER}\nnew\n{app_list.END_MARKER}",
            )

            self.assertTrue(changed)
            self.assertEqual(
                readme.read_text(encoding="utf-8"),
                "# Project\n\nIntro\n\n"
                f"{app_list.START_MARKER}\nnew\n{app_list.END_MARKER}\n\nFooter\n",
            )


if __name__ == "__main__":
    unittest.main()
