from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
import urllib.error
import urllib.parse
from pathlib import Path
from unittest import mock

from click.testing import CliRunner

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cli import contentful  # noqa: E402
from cli.cli import cli  # noqa: E402


def link(link_type: str, entry_id: str) -> dict:
    return {"sys": {"type": "Link", "linkType": link_type, "id": entry_id}}


def entry(fields: dict, entry_id: str = "sys-id") -> dict:
    return {"sys": {"id": entry_id, "type": "Entry"}, "fields": fields}


class CatalogPullTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner(mix_stderr=False)
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.catalog = self.directory / "product_en.json"
        self.catalog.write_text(json.dumps([
            {"key": "wordpress"},
            {"key": "odoo"},
            {"key": "ghost"},
        ]), encoding="utf-8")
        self.offer = self.directory / "offer.json"
        self.offer.write_text(json.dumps([
            {"id": "wordpress", "type": "app", "applications": ["wordpress"],
             "productID": {"aws": ["wp-aws"], "azure": ["wp-azure"]}},
            {"id": "odoo", "type": "app", "applications": ["odoo"],
             "productID": {"aws": ["odoo-aws"]}},
            {"id": "ghost", "type": "app", "applications": ["ghost"],
             "productID": {"aws": ["ghost-aws"]}},
        ]), encoding="utf-8")
        self.wordpress = entry({
            "key": "wordpress",
            "trademark": "WordPress",
            "overview": "WordPress overview",
            "keywords": ["Website", "CMS"],
            "tags": [link("Entry", "tag-cms")],
            "useCases": ["Blog", "CMS"],
            "components": ["Nginx", "Docker"],
            "summary": "WordPress summary",
            "notRequested": "do not export",
        }, "wp-entry")
        self.odoo = entry({
            "key": "odoo",
            "trademark": "Odoo",
            "overview": {"nodeType": "document", "content": [
                {"nodeType": "paragraph", "content": [{"nodeType": "text", "value": "Odoo overview"}]},
                {"nodeType": "paragraph", "content": [{"nodeType": "text", "value": "Second paragraph"}]},
            ]},
            "keywords": ["ERP", "Business"],
            "tags": ["ERP"],
            "usecases": ["Sales", "Inventory"],
            "components": ["PostgreSQL", "pgAdmin"],
            "summary": "Odoo summary",
            "hasEnterprise": True,
        }, "odoo-entry")
        self.ghost = entry({
            "key": "ghost",
            "trademark": "Ghost",
            "overview": "Ghost overview",
            "keywords": [],
            "tags": [],
            "usecases": ["Publishing"],
            "summary": "Ghost summary",
            "hasEnterprise": False,
        }, "ghost-entry")
        self.extra = entry({"key": "not-in-catalog", "trademark": "Extra", "overview": "x", "keywords": [], "tags": [], "usecases": [], "summary": "x"})
        self.includes = {"Entry": [{"sys": {"id": "tag-cms", "type": "Entry"}, "fields": {"name": "CMS"}}]}

    def tearDown(self) -> None:
        self.temp.cleanup()

    def fake_get_json(self, url: str, token: str, timeout: float) -> dict:
        self.assertEqual(token, "secret-token")
        self.assertEqual(timeout, 5)
        if "/content_types/product" in url:
            return {"fields": [
                {"id": "key", "type": "Symbol"},
                {"id": "trademark", "type": "Symbol"},
                {"id": "overview", "type": "Text"},
                {"id": "keywords", "type": "Array"},
                {"id": "tags", "type": "Array"},
                {"id": "useCases", "type": "Array"},
                {"id": "components", "type": "Array"},
                {"id": "summary", "type": "Symbol"},
                {"id": "hasenterprise", "type": "Boolean"},
            ]}
        query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        self.assertEqual(query["content_type"], ["product"])
        self.assertEqual(query["locale"], ["en-US"])
        self.assertEqual(query["select"], ["sys.id,fields"])
        if query["skip"] == ["0"]:
            return {"total": 4, "skip": 0, "limit": 2, "items": [self.wordpress, self.odoo],
                    "includes": self.includes}
        return {"total": 4, "skip": 2, "limit": 2, "items": [self.ghost, self.extra]}

    def invoke(self, *args: str, **kwargs):
        args = list(args)
        if "--output" not in args:
            args = ["--output", "-", *args]
        return self.runner.invoke(
            cli,
            ["catalog", "pull", "--space-id", "space", "--token", "secret-token",
             "--catalog", str(self.catalog), "--offer", str(self.offer), "--timeout", "5", *args],
            **kwargs,
        )

    def test_pulls_only_catalog_apps_in_order_and_combines_fields(self) -> None:
        with mock.patch.object(contentful, "_get_json", side_effect=self.fake_get_json) as fetch:
            result = self.invoke("--page-size", "2", "--no-progress")

        self.assertEqual(result.exit_code, 0, result.stderr)
        dataset = json.loads(result.stdout)
        self.assertEqual(dataset["count"], 3)
        self.assertEqual([item["id"] for item in dataset["items"]], ["wordpress", "odoo", "ghost"])
        self.assertEqual(dataset["items"][0]["trademark"], "WordPress")
        self.assertEqual(dataset["items"][0]["keywords"], ["Website", "CMS"])
        self.assertEqual(dataset["items"][0]["usecases"], ["Blog", "CMS"])
        self.assertEqual(dataset["items"][0]["offerCodes"]["aws"], ["wp-aws"])
        self.assertEqual(dataset["items"][0]["offerCodes"]["azure"], ["wp-azure"])
        self.assertEqual(dataset["items"][1]["overview"], "Odoo overview\nSecond paragraph")
        self.assertEqual(dataset["items"][0]["components"], ["Nginx", "Docker"])
        self.assertEqual(dataset["items"][1]["components"], ["PostgreSQL", "pgAdmin"])
        self.assertTrue(dataset["items"][0]["hasenterprise"])
        self.assertTrue(dataset["items"][1]["hasenterprise"])
        self.assertFalse(dataset["items"][2]["hasenterprise"])
        self.assertNotIn("notRequested", dataset["items"][0])
        self.assertNotIn("tags", dataset["items"][0])
        self.assertNotIn("missingFields", dataset)
        self.assertIn('"keywords": ["Website", "CMS"]', result.stdout)
        self.assertNotIn('"keywords": [\n', result.stdout)
        self.assertEqual(fetch.call_count, 3)  # schema + two entry pages
        self.assertNotIn("secret-token", json.dumps(dataset))
        self.assertNotIn("secret-token", result.stderr)

    def test_apps_subset_uses_requested_order_and_count(self) -> None:
        with mock.patch.object(contentful, "_get_json", side_effect=self.fake_get_json):
            result = self.invoke("--page-size", "2", "--no-progress", "--apps", "odoo,wordpress,odoo")
        self.assertEqual(result.exit_code, 0, result.stderr)
        dataset = json.loads(result.stdout)
        self.assertEqual(dataset["count"], 2)
        self.assertEqual([item["id"] for item in dataset["items"]], ["odoo", "wordpress"])

    def test_apps_outside_target_catalog_fails(self) -> None:
        with mock.patch.object(contentful, "_get_json", side_effect=self.fake_get_json):
            result = self.invoke("--no-progress", "--apps", "wordpress,not-in-catalog")
        self.assertEqual(result.exit_code, 1)
        self.assertIn("not in the target catalog", result.stderr)
        self.assertIn("not-in-catalog", result.stderr)

    def test_empty_apps_option_fails(self) -> None:
        result = self.invoke("--no-progress", "--apps", "")
        self.assertEqual(result.exit_code, 1)
        self.assertIn("--apps", result.stderr)

    def test_single_and_multiple_apps_are_filtered_in_the_api_query(self) -> None:
        def response(url, token, timeout):
            return {"total": 1, "items": [self.wordpress]}
        with mock.patch.object(contentful, "_get_json", side_effect=response) as get:
            contentful.fetch_entries(token="t", space_id="s", environment="e",
                                     content_type="product", locale="en-US", keys=("wordpress",))
        query = urllib.parse.parse_qs(urllib.parse.urlparse(get.call_args.args[0]).query)
        self.assertEqual(query["fields.key"], ["wordpress"])
        self.assertNotIn("fields.key[in]", query)

        with mock.patch.object(contentful, "_get_json", side_effect=response) as get:
            contentful.fetch_entries(token="t", space_id="s", environment="e",
                                     content_type="product", locale="en-US", keys=("wordpress", "odoo"))
        query = urllib.parse.parse_qs(urllib.parse.urlparse(get.call_args.args[0]).query)
        self.assertEqual(query["fields.key[in]"], ["wordpress,odoo"])
        self.assertNotIn("fields.key", query)

    def test_progress_reports_fetch_progress(self) -> None:
        with mock.patch.object(contentful, "_get_json", side_effect=self.fake_get_json):
            result = self.invoke("--page-size", "2")

        self.assertEqual(result.exit_code, 0, result.stderr)
        self.assertIn("Target applications: 3", result.stderr)
        self.assertIn("Fetched 2/4 Contentful entries", result.stderr)
        self.assertIn("Matched 3/3 target applications", result.stderr)

    def test_missing_target_fails_by_default_and_can_be_reported(self) -> None:
        self.catalog.write_text(json.dumps([{"key": "wordpress"}, {"key": "missing"}]), encoding="utf-8")
        with mock.patch.object(contentful, "_get_json", side_effect=self.fake_get_json):
            result = self.invoke("--no-progress")
        self.assertEqual(result.exit_code, 1)
        self.assertIn("absent from Contentful", result.stderr)
        self.assertIn("missing", result.stderr)

        with mock.patch.object(contentful, "_get_json", side_effect=self.fake_get_json):
            result = self.invoke("--no-progress", "--allow-missing")
        self.assertEqual(result.exit_code, 0, result.stderr)
        dataset = json.loads(result.stdout)
        self.assertEqual(dataset["missing"], ["missing"])
        self.assertEqual(dataset["count"], 1)

    def test_empty_field_is_emitted_without_an_extra_flag(self) -> None:
        self.catalog.write_text(json.dumps([{"key": "wordpress"}]), encoding="utf-8")
        broken = entry({"key": "wordpress", "overview": "x", "keywords": [], "tags": [], "usecases": []}, "broken")
        schema = {"fields": [
            {"id": "key", "type": "Symbol"}, {"id": "trademark", "type": "Symbol"},
            {"id": "overview", "type": "Text"},
            {"id": "keywords", "type": "Array"}, {"id": "tags", "type": "Array"},
            {"id": "useCases", "type": "Array"},
            {"id": "components", "type": "Array"}, {"id": "summary", "type": "Symbol"},
            {"id": "hasenterprise", "type": "Boolean"},
        ]}
        def only_broken(url, token, timeout):
            if "/content_types/product" in url:
                return schema
            return {"total": 1, "items": [broken]}
        with mock.patch.object(contentful, "_get_json", side_effect=only_broken):
            result = self.invoke("--no-progress")
        self.assertEqual(result.exit_code, 0, result.stderr)
        dataset = json.loads(result.stdout)
        self.assertIsNone(dataset["items"][0]["summary"])
        self.assertNotIn("missingFields", dataset)

    def test_unknown_field_is_rejected(self) -> None:
        with mock.patch.object(contentful, "_get_json", side_effect=self.fake_get_json):
            result = self.invoke("--no-progress", "--fields", "overview,notAField")
        self.assertEqual(result.exit_code, 1)
        self.assertIn("no requested field", result.stderr)
        self.assertIn("notAField", result.stderr)

    def test_empty_array_field_is_emitted_as_empty_list(self) -> None:
        self.catalog.write_text(json.dumps([{"key": "wordpress"}]), encoding="utf-8")
        no_usecases = entry({"key": "wordpress", "overview": "x", "keywords": [], "tags": [], "summary": "y"}, "one")
        schema = {"fields": [
            {"id": "key", "type": "Symbol"}, {"id": "trademark", "type": "Symbol"},
            {"id": "overview", "type": "Text"},
            {"id": "keywords", "type": "Array"}, {"id": "tags", "type": "Array"},
            {"id": "useCases", "type": "Array"},
            {"id": "components", "type": "Array"}, {"id": "summary", "type": "Symbol"},
            {"id": "hasenterprise", "type": "Boolean"},
        ]}
        def api(url, token, timeout):
            if "/content_types/product" in url:
                return schema
            return {"total": 1, "items": [no_usecases]}
        with mock.patch.object(contentful, "_get_json", side_effect=api):
            result = self.invoke("--no-progress")
        self.assertEqual(result.exit_code, 0, result.stderr)
        dataset = json.loads(result.stdout)
        self.assertEqual(dataset["items"][0]["usecases"], [])
        self.assertNotIn("missingFields", dataset)

    def test_output_file_and_raw_mode(self) -> None:
        output = self.directory / "out" / "catalog.json"
        with mock.patch.object(contentful, "_get_json", side_effect=self.fake_get_json):
            result = self.invoke("--page-size", "2", "--output", str(output), "--raw", "--no-progress",
                                 "--fields", "overview,tags,usecases,summary")
        self.assertEqual(result.exit_code, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        dataset = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(dataset["items"][0]["tags"][0]["sys"]["linkType"], "Entry")
        self.assertEqual(dataset["items"][1]["overview"]["nodeType"], "document")

    def test_explicit_tags_field_resolves_linked_entry_names(self) -> None:
        with mock.patch.object(contentful, "_get_json", side_effect=self.fake_get_json):
            result = self.invoke("--page-size", "2", "--no-progress",
                                 "--fields", "overview,tags,usecases,summary")
        self.assertEqual(result.exit_code, 0, result.stderr)
        dataset = json.loads(result.stdout)
        self.assertEqual(dataset["items"][0]["tags"], ["CMS"])

    def test_token_is_required_and_not_echoed(self) -> None:
        result = self.runner.invoke(
            cli,
            ["catalog", "pull", "--space-id", "space", "--catalog", str(self.catalog), "--offer", str(self.offer)],
            env={"CONTENTFUL_TOKEN": ""},
        )
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("token", (result.stderr or result.stdout).lower())

    def test_http_errors_are_actionable_and_do_not_leak_token(self) -> None:
        error = urllib.error.HTTPError(
            "https://cdn.contentful.com/spaces/space/environments/master/entries",
            401, "Unauthorized", {}, io.BytesIO(b'{"message":"invalid token"}'),
        )
        with mock.patch.object(contentful.urllib.request, "urlopen", side_effect=error):
            with self.assertRaises(contentful.ContentfulError) as caught:
                contentful._get_json("https://example.test", "secret-token", 5)
        self.assertIn("401", str(caught.exception))
        self.assertNotIn("secret-token", str(caught.exception))

    def test_retries_rate_limit(self) -> None:
        class Response:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self, *args):
                return b'{"total":0,"items":[]}'
        limited = urllib.error.HTTPError("https://example.test", 429, "limited", {"Retry-After": "0"}, io.BytesIO(b""))
        with mock.patch.object(contentful.urllib.request, "urlopen", side_effect=[limited, Response()]), \
             mock.patch.object(contentful.time, "sleep") as sleep:
            self.assertEqual(contentful._get_json("https://example.test", "token", 5), {"total": 0, "items": []})
        sleep.assert_called_once()

    def test_cfpat_token_pulls_through_management_api(self) -> None:
        schema = {
            "key": {"type": "Symbol", "localized": False},
            "trademark": {"type": "Symbol", "localized": True},
            "overview": {"type": "Text", "localized": True},
            "keywords": {"type": "Array", "localized": True},
            "useCases": {"type": "Array", "localized": False},
            "components": {"type": "Array", "localized": False},
            "summary": {"type": "Symbol", "localized": True},
            "hasEnterprise": {"type": "Boolean", "localized": False},
        }
        cma_entry = {"sys": {"id": "entry"}, "fields": {
            "key": {"en-US": "wordpress"},
            "trademark": {"en-US": "WordPress"},
            "overview": {"en-US": "WordPress overview"},
            "keywords": {"en-US": ["Website", "CMS"], "zh-CN": ["网站"]},
            "useCases": {"en-US": ["Blogging", "CMS"]},
            "components": {"en-US": ["Nginx", "Docker"]},
            "summary": {"en-US": "WordPress summary"},
            "hasEnterprise": {"en-US": True},
        }}
        with mock.patch("cli.contentful_management.fetch_schema", return_value=schema) as schema_call, \
             mock.patch("cli.contentful_management.fetch_entries", return_value=[cma_entry]) as entries_call, \
             mock.patch.object(contentful, "_get_json") as cda:
            result = self.runner.invoke(
                cli,
                ["catalog", "pull", "--space-id", "space", "--token", "CFPAT-test",
                 "--catalog", str(self.catalog), "--offer", str(self.offer),
                 "--timeout", "5", "--apps", "wordpress",
                 "--output", "-", "--no-progress"],
            )
        self.assertEqual(result.exit_code, 0, result.stderr)
        dataset = json.loads(result.stdout)
        item = dataset["items"][0]
        self.assertEqual(item["keywords"], ["Website", "CMS"])
        self.assertEqual(item["usecases"], ["Blogging", "CMS"])
        self.assertEqual(item["components"], ["Nginx", "Docker"])
        self.assertTrue(item["hasenterprise"])
        self.assertEqual(dataset["source"]["contentful"]["api"], "https://api.contentful.com")
        schema_call.assert_called_once()
        entries_call.assert_called_once()
        cda.assert_not_called()

    def test_cfpat_resolves_linked_component_names(self) -> None:
        schema = {
            "key": {"type": "Symbol", "localized": False},
            "components": {"type": "Array", "localized": False},
        }
        top = {
            "sys": {"id": "entry"},
            "fields": {
                "key": {"en-US": "wordpress"},
                "components": {"en-US": [link("Entry", "comp-1"), link("Entry", "comp-2")]},
            },
        }
        linked = [
            {"sys": {"id": "comp-1"}, "fields": {"title": {"en-US": "PostgreSQL"}}},
            {"sys": {"id": "comp-2"}, "fields": {"trademark": {"en-US": "pgAdmin"}}},
        ]

        def entries(**kwargs):
            return linked if kwargs.get("ids") else [top]

        with mock.patch("cli.contentful_management.fetch_schema", return_value=schema), \
             mock.patch("cli.contentful_management.fetch_entries", side_effect=entries), \
             mock.patch.object(contentful, "_get_json") as cda:
            result = self.runner.invoke(
                cli,
                ["catalog", "pull", "--space-id", "space", "--token", "CFPAT-test",
                 "--catalog", str(self.catalog), "--offer", str(self.offer),
                 "--apps", "wordpress", "--fields", "components",
                 "--output", "-", "--no-progress"],
            )

        self.assertEqual(result.exit_code, 0, result.stderr)
        item = json.loads(result.stdout)["items"][0]
        self.assertEqual(item["components"], ["PostgreSQL", "pgAdmin"])
        cda.assert_not_called()

    def test_contentful_token_environment_variable_is_used(self) -> None:
        with mock.patch.object(contentful, "_get_json", side_effect=self.fake_get_json):
            result = self.runner.invoke(
                cli,
                ["catalog", "pull", "--space-id", "space", "--catalog", str(self.catalog),
                 "--offer", str(self.offer), "--timeout", "5", "--apps", "wordpress",
                 "--output", "-", "--no-progress"],
                env={"CONTENTFUL_TOKEN": "secret-token"},
            )
        self.assertEqual(result.exit_code, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["count"], 1)

    def test_default_output_uses_catalog_dir(self) -> None:
        target = self.directory / "catalog"
        with mock.patch.object(contentful, "_get_json", side_effect=self.fake_get_json), \
             mock.patch.dict("os.environ", {"MK_CATALOG_DIR": str(target)}):
            result = self.runner.invoke(
                cli,
                ["catalog", "pull", "--space-id", "space", "--token", "secret-token",
                 "--catalog", str(self.catalog), "--offer", str(self.offer),
                 "--timeout", "5", "--no-progress"],
            )
        self.assertEqual(result.exit_code, 0, result.stderr)
        dataset = json.loads((target / "catalog.json").read_text(encoding="utf-8"))
        self.assertEqual(dataset["count"], 3)

    def test_help_exposes_options(self) -> None:
        result = self.runner.invoke(cli, ["catalog", "pull", "--help"])
        self.assertEqual(result.exit_code, 0)
        for option in ("--space-id", "--token", "--fields", "--apps", "--offer", "--progress", "--output"):
            self.assertIn(option, result.output)


if __name__ == "__main__":
    unittest.main()
