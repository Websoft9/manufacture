from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from click.testing import CliRunner

from cli import offer
from cli.cli import cli


class OfferTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.product = self.directory / "product.json"
        self.provider = self.directory / "provider.json"
        self.plan_path = self.directory / "plan.json"
        self.data = offer.read_json(offer.DATA / "products/odoo.json")
        self.policy = offer.read_json(offer.DATA / "provider.json")
        self.write()
        self.runner = CliRunner()

    def tearDown(self):
        self.temp.cleanup()

    def write(self):
        self.product.write_text(json.dumps(self.data), encoding="utf-8")
        self.provider.write_text(json.dumps(self.policy), encoding="utf-8")

    def render(self):
        return offer.render(self.product, self.provider)

    def verify(self):
        self.data["listings"]["aws"]["entityId"] = "prod-example12345"
        checks = [self.data["application"]["verification"], self.policy["verification"], self.data["listings"]["aws"]["verification"], self.data["listings"]["aws"]["deployment"]["verification"], self.data["listings"]["aws"]["commercial"]["verification"]]
        for check in checks:
            check.update(status="verified", checkedAt="2026-11-03", evidence=["Synthetic test fixture"], notes="Test evidence only")
        self.write()

    def entity(self, value):
        content = copy.deepcopy(value["content"])
        support = content.pop("SupportDescription")
        return {"EntityIdentifier": "prod-example12345@4", "EntityType": "AmiProduct@1.0", "DetailsDocument": {"Description": content, "SupportInformation": {"Description": support}, "PromotionalResources": {}}}

    def args(self, command):
        return ["offer", command, "--product", str(self.product), "--provider", str(self.provider)]

    def test_example_is_consistent_draft_and_publish_check_fails(self):
        value = self.render()
        self.assertIn("Odoo Community", value["content"]["ShortDescription"])
        self.assertNotIn("Jupyter", str(value["content"]))
        self.assertEqual(len(value["publishBlockers"]), 6)
        result = self.runner.invoke(cli, self.args("validate") + ["--publish-ready"])
        self.assertNotEqual(result.exit_code, 0)

    def test_keyword_total_and_unknown_override_are_rejected(self):
        self.data["application"]["searchKeywords"] = [str(index) + "x" * 49 for index in range(6)]
        self.write()
        with self.assertRaisesRegex(ValueError, "250"):
            self.render()
        self.data["application"]["searchKeywords"] = ["ERP"]
        self.data["listings"]["aws"]["contentOverrides"]["RefundPolicy"] = "foo"
        self.write()
        with self.assertRaisesRegex(ValueError, "Additional properties"):
            self.render()

    def test_verified_requires_date_and_evidence(self):
        self.verify()
        self.policy["verification"]["checkedAt"] = None
        self.write()
        with self.assertRaises(Exception):
            self.render()

    def test_plan_noop_and_minimal_update_preserve_optional_fields(self):
        self.verify()
        value = self.render()
        entity = self.entity(value)
        entity["DetailsDocument"]["Description"]["Categories"] = ["Business Applications"]
        entity["DetailsDocument"]["PromotionalResources"]["LogoUrl"] = "https://example.com/old.png"
        self.assertIsNone(offer.plan(value, entity)["request"])
        entity["DetailsDocument"]["Description"]["ShortDescription"] = "Old description"
        planned = offer.plan(value, entity)
        change = planned["request"]["ChangeSet"][0]
        self.assertEqual(change["Entity"]["Identifier"], "prod-example12345@4")
        self.assertEqual(set(change["DetailsDocument"]), {"ShortDescription"})
        self.assertNotIn("UsageInstructions", json.dumps(planned))

    def test_snapshot_wrong_identity_is_rejected(self):
        self.verify()
        value = self.render()
        entity = self.entity(value)
        entity["EntityIdentifier"] = "prod-another@4"
        with self.assertRaisesRegex(ValueError, "does not match"):
            offer.plan(value, entity)

    def prepare_plan(self):
        self.verify()
        value = self.render()
        entity = self.entity(value)
        entity["DetailsDocument"]["Description"]["ProductTitle"] = "Old title"
        planned = offer.plan(value, entity)
        self.plan_path.write_text(json.dumps(planned), encoding="utf-8")
        return value, entity, planned

    def test_apply_submits_reviewed_delta_and_verifies_readback(self):
        value, entity, planned = self.prepare_plan()
        client = mock.Mock()
        client.describe_entity.side_effect = [entity, self.entity(value)]
        client.start_change_set.return_value = {"ChangeSetId": "cs-example"}
        client.describe_change_set.return_value = {"ChangeSetId": "cs-example", "Status": "SUCCEEDED"}
        with mock.patch.object(offer, "aws_client", return_value=client):
            result = self.runner.invoke(cli, self.args("apply") + ["--plan", str(self.plan_path), "--wait-seconds", "1"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn('"readBackVerified": true', result.output)
        self.assertEqual(client.start_change_set.call_args.kwargs["ClientRequestToken"], planned["planHash"])
        self.assertEqual(client.start_change_set.call_args.kwargs["ChangeSet"], planned["request"]["ChangeSet"])

    def test_apply_rejects_modified_stale_and_changed_sources(self):
        for kind in ("modified", "revision", "source"):
            with self.subTest(kind=kind):
                _, entity, planned = self.prepare_plan()
                if kind == "modified":
                    planned["request"]["ChangeSet"][0]["ChangeType"] = "UpdateVisibility"
                    self.plan_path.write_text(json.dumps(planned), encoding="utf-8")
                elif kind == "revision":
                    entity["EntityIdentifier"] = "prod-example12345@5"
                else:
                    self.data["application"]["valueProposition"] = "A different claim."
                    self.write()
                client = mock.Mock()
                client.describe_entity.return_value = entity
                with mock.patch.object(offer, "aws_client", return_value=client):
                    result = self.runner.invoke(cli, self.args("apply") + ["--plan", str(self.plan_path)])
                self.assertNotEqual(result.exit_code, 0)
                client.start_change_set.assert_not_called()

    def test_unverified_apply_never_contacts_aws(self):
        self.plan_path.write_text("{}", encoding="utf-8")
        with mock.patch.object(offer, "aws_client") as client:
            result = self.runner.invoke(cli, self.args("apply") + ["--plan", str(self.plan_path)])
        self.assertNotEqual(result.exit_code, 0)
        client.assert_not_called()

    def test_sdk_errors_do_not_expose_sensitive_message(self):
        client = mock.Mock()
        error = Exception("secret-sensitive-response")
        error.response = {"Error": {"Code": "AccessDeniedException", "Message": "secret"}}
        client.describe_entity.side_effect = error
        with self.assertRaisesRegex(ValueError, "AccessDeniedException") as caught:
            offer.aws_call(client, "describe_entity", EntityId="prod-test")
        self.assertNotIn("secret", str(caught.exception))

    def test_apply_noop_does_not_submit(self):
        self.verify()
        value = self.render()
        entity = self.entity(value)
        self.plan_path.write_text(json.dumps(offer.plan(value, entity)), encoding="utf-8")
        client = mock.Mock()
        client.describe_entity.return_value = entity
        with mock.patch.object(offer, "aws_client", return_value=client):
            result = self.runner.invoke(cli, self.args("apply") + ["--plan", str(self.plan_path)])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("NO_CHANGES", result.output)
        client.start_change_set.assert_not_called()

    def test_read_shape_normalizes_resources_and_legacy_details(self):
        self.verify()
        self.data["listings"]["aws"]["additionalResources"] = [{"Text": "Docs", "Url": "https://example.com/docs"}]
        self.write()
        value = self.render()
        entity = self.entity(value)
        detail = entity.pop("DetailsDocument")
        detail["Description"].pop("AdditionalResources")
        detail["PromotionalResources"]["AdditionalResources"] = [{"Type": "Link", "Text": "Docs", "Url": "https://example.com/docs"}]
        entity["Details"] = json.dumps(detail)
        self.assertIsNone(offer.plan(value, entity)["request"])

    def test_list_paginates_without_exporting_raw_responses(self):
        client = mock.Mock()
        client.list_entities.side_effect = [
            {"NextToken": "next", "EntitySummaryList": [{"EntityId": "prod-first", "AmiProductSummary": {"ProductTitle": "First", "Visibility": "Public"}, "private": "secret"}]},
            {"EntitySummaryList": [{"EntityId": "prod-second", "Name": "Second"}]},
        ]
        with mock.patch.object(offer, "aws_client", return_value=client):
            result = self.runner.invoke(cli, ["offer", "list"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("prod-second", result.output)
        self.assertNotIn("secret", result.output)
        self.assertEqual(client.list_entities.call_args.kwargs["NextToken"], "next")

    def test_control_characters_in_list_and_signed_media_are_rejected(self):
        content = self.render()["content"]
        content["Highlights"] = ["bad\x01text"]
        with self.assertRaisesRegex(ValueError, "control characters"):
            offer.validate_content(content)
        content["Highlights"] = ["Valid"]
        content["LogoUrl"] = "https://example.com/image?X-Amz-Signature=secret"
        with self.assertRaisesRegex(ValueError, "unsigned HTTPS"):
            offer.validate_content(content)

    def test_terminal_failure_and_timeout(self):
        client = mock.Mock()
        client.describe_change_set.return_value = {"ChangeSetId": "cs-test", "Status": "FAILED", "ChangeSet": [{"ErrorDetailList": [{"ErrorCode": "INVALID_INPUT", "ErrorMessage": "secret"}]}]}
        with mock.patch.object(offer, "aws_client", return_value=client):
            result = self.runner.invoke(cli, ["offer", "status", "cs-test"])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("INVALID_INPUT", result.output)
        self.assertNotIn("secret", result.output)
        client.describe_change_set.return_value = {"ChangeSetId": "cs-test", "Status": "APPLYING"}
        with mock.patch.object(offer, "aws_client", return_value=client):
            result = self.runner.invoke(cli, ["offer", "status", "cs-test"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("pollingTimedOut", result.output)


if __name__ == "__main__":
    unittest.main()
