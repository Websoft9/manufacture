from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

from click.testing import CliRunner

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cli import contentful, contentful_management as cma  # noqa: E402
from cli.cli import cli  # noqa: E402

SCHEMA = {
    "key": {"type": "Symbol", "localized": False},
    "trademark": {"type": "Symbol", "localized": True},
    "overview": {"type": "Text", "localized": True},
    "keywords": {"type": "Array", "localized": True, "items": {"type": "Symbol"}},
    "useCases": {"type": "Array", "localized": False, "items": {"type": "Symbol"}},
    "summary": {"type": "Symbol", "localized": True},
    "other": {"type": "Symbol", "localized": False},
}
ENTRY = {
    "sys": {"id": "entry-1", "version": 3},
    "fields": {
        "key": {"en-US": "wordpress"},
        "trademark": {"en-US": "Old WP", "zh-CN": "旧"},
        "overview": {"en-US": "Old overview"},
        "keywords": {"en-US": ["old"]},
        "useCases": {"en-US": ["old"]},
        "summary": {"en-US": "Old summary"},
        "other": "keep",
    },
}
ITEM = {
    "id": "wordpress",
    "trademark": "WordPress",
    "overview": "New overview",
    "keywords": ["site", "cms"],
    "usecases": ["publishing"],
    "summary": "New summary",
}


class BuildChangesTests(unittest.TestCase):
    def test_merges_only_target_locale_and_preserves_other_fields(self) -> None:
        fields, changed, skipped, unchanged = cma.build_changes(ITEM, ENTRY, SCHEMA)
        self.assertEqual(changed, ["trademark", "overview", "keywords", "usecases", "summary"])
        self.assertEqual(skipped, [])
        self.assertEqual(unchanged, [])
        self.assertEqual(fields["trademark"], {"en-US": "WordPress", "zh-CN": "旧"})
        self.assertEqual(fields["overview"], {"en-US": "New overview"})
        self.assertEqual(fields["keywords"], {"en-US": ["site", "cms"]})
        self.assertEqual(fields["useCases"], {"en-US": ["publishing"]})
        self.assertEqual(fields["summary"], {"en-US": "New summary"})
        self.assertEqual(fields["other"], "keep")
        self.assertEqual(fields["key"], {"en-US": "wordpress"})

    def test_empty_values_are_skipped_or_cleared(self) -> None:
        item = {"id": "wordpress", "trademark": "", "keywords": [], "summary": None}
        fields, changed, skipped, unchanged = cma.build_changes(item, ENTRY, SCHEMA)
        self.assertEqual(changed, [])
        self.assertEqual(skipped, ["trademark", "keywords", "summary"])
        self.assertEqual(fields, ENTRY["fields"])

        fields, changed, skipped, unchanged = cma.build_changes(item, ENTRY, SCHEMA, clear=True)
        self.assertEqual(changed, ["trademark", "keywords", "summary"])
        self.assertEqual(skipped, [])
        self.assertEqual(fields["trademark"]["en-US"], "")
        self.assertEqual(fields["keywords"]["en-US"], [])
        self.assertEqual(fields["summary"]["en-US"], "")

    def test_unchanged_values_are_not_written(self) -> None:
        item = {"id": "wordpress", "trademark": "Old WP"}
        fields, changed, skipped, unchanged = cma.build_changes(item, ENTRY, SCHEMA)
        self.assertEqual(changed, [])
        self.assertEqual(unchanged, ["trademark"])
        self.assertEqual(fields["trademark"]["zh-CN"], "旧")

    def test_unknown_or_mistyped_input_is_rejected(self) -> None:
        with self.assertRaisesRegex(contentful.ContentfulError, "Unsupported input field"):
            cma.build_changes({"id": "wordpress", "tags": ["x"]}, ENTRY, SCHEMA)
        with self.assertRaisesRegex(contentful.ContentfulError, "array of strings"):
            cma.build_changes({"id": "wordpress", "keywords": "not-a-list"}, ENTRY, SCHEMA)
        with self.assertRaisesRegex(contentful.ContentfulError, "must be a string"):
            cma.build_changes({"id": "wordpress", "summary": ["bad"]}, ENTRY, SCHEMA)


class InputTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "input.json"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write(self, data) -> None:
        self.path.write_text(json.dumps(data), encoding="utf-8")

    def test_accepts_dataset_and_array_and_rejects_unknown_fields(self) -> None:
        self.write({"items": [ITEM]})
        by_id, order = cma.load_input(str(self.path))
        self.assertEqual(order, ["wordpress"])
        self.assertEqual(by_id["wordpress"]["keywords"], ["site", "cms"])

        self.write([ITEM])
        self.assertEqual(cma.load_input(str(self.path))[1], ["wordpress"])

        self.write({"items": [{"id": "wordpress", "tags": []}]})
        with self.assertRaisesRegex(contentful.ContentfulError, "unsupported input field"):
            cma.load_input(str(self.path))

    def test_duplicate_and_missing_ids_fail(self) -> None:
        self.write({"items": [ITEM, ITEM]})
        with self.assertRaisesRegex(contentful.ContentfulError, "duplicate"):
            cma.load_input(str(self.path))
        self.write({"items": [{"trademark": "No id"}]})
        with self.assertRaisesRegex(contentful.ContentfulError, "no string id"):
            cma.load_input(str(self.path))


class PushTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "input.json"
        self.path.write_text(json.dumps({"items": [ITEM]}), encoding="utf-8")
        self.update = mock.Mock(return_value={"sys": {"version": 4}})
        self.publish = mock.Mock(return_value={})
        self.schema = mock.Mock(return_value=SCHEMA)
        self.entries = mock.Mock(return_value=[ENTRY])

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_push(self, **kwargs):
        with mock.patch.object(cma, "fetch_schema", self.schema), \
             mock.patch.object(cma, "fetch_entries", self.entries), \
             mock.patch.object(cma, "update_entry", self.update), \
             mock.patch.object(cma, "publish_entry", self.publish):
            return cma.push(token="secret", space_id="space", environment="master",
                            input_path=str(self.path), verbose=True, **kwargs)

    def test_updates_draft_with_version_and_preserves_fields(self) -> None:
        summary = self.run_push(publish=True)
        self.assertEqual(summary["updated"], 1)
        self.assertEqual(summary["published"], 1)
        kwargs = self.update.call_args.kwargs
        self.assertEqual(kwargs["entry_id"], "entry-1")
        self.assertEqual(kwargs["version"], 3)
        self.assertEqual(kwargs["fields"]["trademark"], {"en-US": "WordPress", "zh-CN": "旧"})
        self.assertEqual(kwargs["fields"]["useCases"], {"en-US": ["publishing"]})
        self.assertEqual(self.publish.call_args.kwargs["version"], 4)
        self.assertEqual(self.entries.call_args.kwargs["keys"], ("wordpress",))

    def test_dry_run_never_writes(self) -> None:
        summary = self.run_push(dry_run=True)
        self.assertEqual(summary["updated"], 1)
        self.update.assert_not_called()
        self.publish.assert_not_called()

    def test_without_publish_only_the_draft_is_updated(self) -> None:
        summary = self.run_push()
        self.assertEqual(summary["updated"], 1)
        self.assertEqual(summary["published"], 0)
        self.publish.assert_not_called()

    def test_unchanged_entry_is_skipped(self) -> None:
        current = {"items": [{"id": "wordpress", "trademark": "Old WP"}]}
        self.path.write_text(json.dumps(current), encoding="utf-8")
        summary = self.run_push()
        self.assertEqual(summary["unchanged"], 1)
        self.update.assert_not_called()

    def test_missing_entry_fails_or_is_allowed(self) -> None:
        self.entries.return_value = []
        summary = self.run_push()
        self.assertEqual(len(summary["errors"]), 1)
        self.assertIn("not found", summary["errors"][0])

        summary = self.run_push(allow_missing=True)
        self.assertEqual(summary["missing"], ["wordpress"])
        self.assertEqual(summary["errors"], [])

    def test_version_conflict_is_reported_and_does_not_publish(self) -> None:
        self.update.side_effect = contentful.ContentfulError("Contentful version conflict (HTTP 409).")
        summary = self.run_push(publish=True)
        self.assertEqual(summary["updated"], 0)
        self.assertEqual(summary["published"], 0)
        self.assertIn("version conflict", summary["errors"][0])

    def test_publish_requires_dry_run_separation(self) -> None:
        with self.assertRaisesRegex(contentful.ContentfulError, "dry-run"):
            self.run_push(dry_run=True, publish=True)

    def test_apps_subset_order_and_unknown_app(self) -> None:
        other = {"items": [ITEM, {**ITEM, "id": "odoo"}]}
        self.path.write_text(json.dumps(other), encoding="utf-8")
        summary = self.run_push(app_ids=("odoo", "wordpress"))
        self.assertEqual(summary["selected"], 2)
        with self.assertRaisesRegex(contentful.ContentfulError, "not in the target catalog"):
            self.run_push(app_ids=("missing",))


class ManagementRequestTests(unittest.TestCase):
    def test_error_messages_do_not_leak_token(self) -> None:
        error = urllib.error.HTTPError("https://api.contentful.com", 401, "Unauthorized", {},
                                       io.BytesIO(b'{"message":"invalid token"}'))
        with mock.patch.object(cma.urllib.request, "urlopen", side_effect=error):
            with self.assertRaises(contentful.ContentfulError) as caught:
                cma._request("GET", "https://example.test", "secret-token")
        self.assertIn("401", str(caught.exception))
        self.assertNotIn("secret-token", str(caught.exception))

    def test_version_conflict_message_is_actionable(self) -> None:
        error = urllib.error.HTTPError("https://api.contentful.com", 409, "Conflict", {}, io.BytesIO(b""))
        with mock.patch.object(cma.urllib.request, "urlopen", side_effect=error):
            with self.assertRaisesRegex(contentful.ContentfulError, "version conflict"):
                cma._request("PUT", "https://example.test", "token")

    def test_management_entry_query_filters_by_application_keys(self) -> None:
        with mock.patch.object(cma, "_request", return_value={"total": 1, "items": [ENTRY]}) as request:
            cma.fetch_entries(token="t", space_id="s", environment="e", content_type="product",
                              keys=("wordpress",))
        url = request.call_args.args[1]
        self.assertIn("fields.key=wordpress", url)
        with mock.patch.object(cma, "_request", return_value={"total": 1, "items": [ENTRY]}) as request:
            cma.fetch_entries(token="t", space_id="s", environment="e", content_type="product",
                              keys=("wordpress", "odoo"))
        url = request.call_args.args[1]
        self.assertIn("fields.key%5Bin%5D=wordpress%2Codoo", url)


class PushCliTests(unittest.TestCase):
    def test_default_input_uses_catalog_dir(self) -> None:
        summary = {"selected": 0, "matched": 0, "updated": 0, "published": 0,
                   "unchanged": 0, "skippedEmpty": 0, "missing": [], "errors": []}
        runner = CliRunner(mix_stderr=False)
        with mock.patch.dict("os.environ", {"MK_CATALOG_DIR": "/tmp/example-catalog"}), \
             mock.patch.object(cma, "push", return_value=summary) as push:
            result = runner.invoke(
                cli,
                ["catalog", "push", "--space-id", "space", "--token", "secret", "--no-progress"],
            )
        self.assertEqual(result.exit_code, 0, result.stderr)
        self.assertEqual(push.call_args.kwargs["input_path"], "/tmp/example-catalog/catalog.json")

    def test_contentful_token_environment_variable_is_used(self) -> None:
        summary = {"selected": 0, "matched": 0, "updated": 0, "published": 0,
                   "unchanged": 0, "skippedEmpty": 0, "missing": [], "errors": []}
        runner = CliRunner(mix_stderr=False)
        with mock.patch.dict("os.environ", {"CONTENTFUL_TOKEN": "secret-token"}), \
             mock.patch.object(cma, "push", return_value=summary) as push:
            result = runner.invoke(
                cli,
                ["catalog", "push", "--space-id", "space", "--no-progress"],
            )
        self.assertEqual(result.exit_code, 0, result.stderr)
        self.assertEqual(push.call_args.kwargs["token"], "secret-token")

    def test_token_is_required_and_help_lists_options(self) -> None:
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(cli, ["catalog", "push", "--space-id", "space"],
                               env={"CONTENTFUL_TOKEN": ""})
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("token", (result.stderr or result.stdout).lower())
        result = runner.invoke(cli, ["catalog", "push", "--help"])
        self.assertEqual(result.exit_code, 0)
        for option in ("--input", "--apps", "--dry-run", "--publish", "--clear"):
            self.assertIn(option, result.output)


if __name__ == "__main__":
    unittest.main()
