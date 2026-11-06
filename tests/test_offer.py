from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from click.testing import CliRunner

from cli import aws_marketplace, catalog_data, offer
from cli.cli import cli


class OfferTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.catalog_path = self.directory / "catalog.json"
        self.versions_path = self.directory / "versions.json"
        self.vendor_path = self.directory / "vendor.json"
        self.plan_path = self.directory / "plan.json"
        catalog = offer.read_json(offer.DATA.parent / ".catalog" / "catalog.json")
        self.item = copy.deepcopy(next(item for item in catalog["items"] if item["id"] == "odoo"))
        self.item.update({
            "entityId": None,
            "templateId": "aws-ami-v1",
            "locale": "en-US",
            "contentOverrides": {},
            "categories": [],
            "additionalResources": [
                {"Text": "Odoo guide by Websoft9", "Url": "https://support.websoft9.com/en/docs/odoo"},
                {"Text": "Websoft9 Console login guide", "Url": "https://support.websoft9.com/en/docs/login-console"},
            ],
            "logoUrl": None,
            "videoUrls": [],
        })
        self.vendor_data = offer.read_json(offer.DATA / "vendor.json")
        self.write()
        self.runner = CliRunner()

    def tearDown(self):
        self.temp.cleanup()

    def write(self):
        self.catalog_path.write_text(json.dumps({"items": [self.item]}), encoding="utf-8")
        self.versions_path.write_text(json.dumps([{"id": "odoo", "version": "20.0"}]), encoding="utf-8")
        self.vendor_path.write_text(json.dumps(self.vendor_data), encoding="utf-8")

    def runtime(self):
        return catalog_data.build_runtime_product(
            key="odoo", item=self.item, version="20.0",
        )

    def render(self):
        return offer.render(self.runtime(), self.vendor_path)

    def set_entity_id(self):
        self.item["entityId"] = "prod-example12345"
        self.write()

    def entity(self, value):
        return {
            "EntityIdentifier": "prod-example12345@4",
            "EntityType": "AmiProduct@1.0",
            "DetailsDocument": aws_marketplace.to_read_document(value["content"]),
        }

    def args(self, command):
        return [
            "offer", command, "--app", "odoo",
            "--catalog", str(self.catalog_path),
            "--versions", str(self.versions_path),
            "--vendor", str(self.vendor_path),
        ]

    def test_example_is_consistent_draft_and_publish_check_fails(self):
        value = self.render()
        self.assertIn("Odoo Community Edition", value["content"]["ShortDescription"])
        self.assertIn("20.0", value["content"]["LongDescription"])
        self.assertNotIn("Jupyter", str(value["content"]))
        self.assertEqual(value["publishBlockers"], ["listing: Catalog EntityId is missing"])
        result = self.runner.invoke(
            cli, self.args("build") + ["--cloud", "aws", "--publish-ready"]
        )
        self.assertNotEqual(result.exit_code, 0)

    def test_publish_ready_does_not_require_separate_verification_records(self):
        self.set_entity_id()
        output = self.directory / "publish-ready.json"
        result = self.runner.invoke(
            cli,
            self.args("build") + ["--cloud", "aws", "--publish-ready", "--output", str(output)],
        )
        self.assertEqual(result.exit_code, 0, result.output)
        preview = json.loads(output.read_text(encoding="utf-8"))
        self.assertNotIn("verification", preview)

    def test_build_writes_template_shaped_preview(self):
        output = self.directory / "aws" / "odoo.json"
        result = self.runner.invoke(cli, self.args("build") + ["--cloud", "aws", "--output", str(output)])
        self.assertEqual(result.exit_code, 0, result.output)
        document = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(document["templateId"], "aws-ami-v1")
        self.assertEqual(document["target"]["entityType"], "AmiProduct@1.0")
        self.assertEqual(document["content"]["SearchKeywords"], self.item["keywords"])
        self.assertEqual(document["content"]["Highlights"], self.vendor_data["highlights"])
        self.assertNotIn("Categories", document["content"])
        self.assertNotIn("LogoUrl", document["content"])
        self.assertNotIn("VideoUrls", document["content"])
        self.assertNotIn("LongDescription", document["content"])
        self.assertEqual(document["AdditionalResources"], [
            {"Text": "Odoo Image Guide by Websoft9", "Url": "https://support.websoft9.com/en/docs/odoo"},
            {"Text": "Install Websoft9 on AWS", "Url": "https://support.websoft9.com/en/docs/install-aws"},
        ])
        self.assertEqual(
            [section["text"] for section in document["longDescriptionSections"] if section["text"].startswith("The software fee")],
            ["The software fee covers the Websoft9 Console, operations tools, and support. AWS infrastructure is billed separately."],
        )

    def test_template_fields_are_declared_in_aws_field_contract(self):
        template = offer.read_json(offer.DATA / "templates" / "aws-ami.json")
        fields = set(template["content"]) | {"LongDescription"}
        if template.get("AdditionalResources"):
            fields.add("AdditionalResources")
        self.assertLessEqual(fields, set(aws_marketplace.FIELD_SPECS))
        self.assertNotIn("Categories", fields)
        self.assertNotIn("LogoUrl", fields)
        self.assertNotIn("VideoUrls", fields)

    def test_build_infers_markdown_from_output_suffix(self):
        output = self.directory / "odoo-preview.md"
        result = self.runner.invoke(cli, self.args("build") + ["--cloud", "aws", "--output", str(output)])
        self.assertEqual(result.exit_code, 0, result.output)
        text = output.read_text(encoding="utf-8")
        self.assertIn("# aws-ami-v1", text)
        self.assertIn("Odoo on AWS - Preconfigured", text)
        self.assertIn("## Long description", text)
        self.assertIn("What you pay for", text)

    def test_plan_writes_complete_plan_to_output(self):
        output = self.directory / "plan.json"
        current = self.directory / "current.json"
        self.set_entity_id()
        current.write_text(json.dumps(self.entity(self.render())), encoding="utf-8")
        result = self.runner.invoke(cli, self.args("plan") + [
            "--current", str(current), "--output", str(output),
        ])
        self.assertEqual(result.exit_code, 0, result.output)
        plan = json.loads(output.read_text(encoding="utf-8"))
        self.assertIn("planHash", plan)
        self.assertIn("request", plan)
        self.assertIn("diff", plan)

    def test_vendor_highlights_are_used_in_rendered_content(self):
        value = self.render()
        self.assertEqual(value["content"]["Highlights"], self.vendor_data["highlights"])

    def test_template_supplies_search_keywords_and_learning_resources(self):
        self.item["additionalResources"] = []
        self.write()
        value = self.render()
        self.assertEqual(value["content"]["SearchKeywords"], self.item["keywords"])
        self.assertEqual(value["content"]["AdditionalResources"], [
            {"Text": "Odoo Image Guide by Websoft9", "Url": "https://support.websoft9.com/en/docs/odoo"},
            {"Text": "Install Websoft9 on AWS", "Url": "https://support.websoft9.com/en/docs/install-aws"},
        ])

    def test_listing_additional_resources_do_not_override_template_defaults(self):
        value = self.render()
        self.assertEqual(value["content"]["AdditionalResources"], [
            {"Text": "Odoo Image Guide by Websoft9", "Url": "https://support.websoft9.com/en/docs/odoo"},
            {"Text": "Install Websoft9 on AWS", "Url": "https://support.websoft9.com/en/docs/install-aws"},
        ])

    def test_keyword_total_and_unknown_override_are_rejected(self):
        self.item["keywords"] = [str(index) + "x" * 49 for index in range(6)]
        self.write()
        with self.assertRaisesRegex(ValueError, "250"):
            self.render()
        self.item["keywords"] = ["ERP"]
        self.item["contentOverrides"]["RefundPolicy"] = "foo"
        self.write()
        with self.assertRaisesRegex(ValueError, "Additional properties"):
            self.render()

    def test_plan_noop_and_minimal_update_preserve_optional_fields(self):
        self.set_entity_id()
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
        self.set_entity_id()
        value = self.render()
        entity = self.entity(value)
        entity["EntityIdentifier"] = "prod-another@4"
        with self.assertRaisesRegex(ValueError, "does not match"):
            offer.plan(value, entity)

    def prepare_plan(self):
        self.set_entity_id()
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
                    self.item["summary"] = "A different catalog claim."
                    self.write()
                client = mock.Mock()
                client.describe_entity.return_value = entity
                with mock.patch.object(offer, "aws_client", return_value=client):
                    result = self.runner.invoke(cli, self.args("apply") + ["--plan", str(self.plan_path)])
                self.assertNotEqual(result.exit_code, 0)
                client.start_change_set.assert_not_called()

    def test_missing_entity_apply_never_contacts_aws(self):
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
        self.set_entity_id()
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
        self.set_entity_id()
        value = self.render()
        entity = self.entity(value)
        detail = entity.pop("DetailsDocument")
        detail["Description"].pop("AdditionalResources", None)
        detail["PromotionalResources"]["AdditionalResources"] = [
            {"Type": "Link", **item} for item in value["content"]["AdditionalResources"]
        ]
        entity["Details"] = json.dumps(detail)
        self.assertIsNone(offer.plan(value, entity)["request"])

    def test_resolve_entity_paginates_and_matches_offer_code(self):
        client = mock.Mock()
        client.list_entities.side_effect = [
            {"NextToken": "next", "EntitySummaryList": [{"EntityId": "prod-first", "AmiProductSummary": {"ProductTitle": "First", "Visibility": "Public"}, "private": "secret"}]},
            {"EntitySummaryList": [{"EntityId": "prod-second", "Name": "Second"}]},
        ]
        client.describe_entity.side_effect = lambda **kwargs: {
            "DetailsDocument": {
                "Description": {
                    "Sku": "sku-first" if kwargs["EntityId"] == "prod-first" else "sku-second",
                    "ProductCode": "code-second",
                    "ProductTitle": "Second",
                }
            }
        }
        with mock.patch.object(offer, "aws_client", return_value=client):
            result = self.runner.invoke(
                cli,
                ["offer", "resolve-entity", "--cloud", "aws", "--code", "sku-second"],
            )
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn('"entityId": "prod-second"', result.output)
        self.assertIn('"sku": "sku-second"', result.output)
        self.assertNotIn("secret", result.output)
        self.assertEqual(client.list_entities.call_args_list[1].kwargs["NextToken"], "next")

    def test_resolve_entity_accepts_multiple_codes_in_one_scan(self):
        client = mock.Mock()
        client.list_entities.return_value = {
            "EntitySummaryList": [
                {"EntityId": "prod-first", "AmiProductSummary": {"ProductTitle": "First", "Visibility": "Public"}},
                {"EntityId": "prod-second", "AmiProductSummary": {"ProductTitle": "Second", "Visibility": "Public"}},
            ]
        }
        client.describe_entity.side_effect = lambda **kwargs: {
            "DetailsDocument": {
                "Description": {
                    "Sku": "sku-first" if kwargs["EntityId"] == "prod-first" else "sku-second",
                    "ProductCode": "code-first" if kwargs["EntityId"] == "prod-first" else "code-second",
                }
            }
        }
        with mock.patch.object(offer, "aws_client", return_value=client):
            result = self.runner.invoke(
                cli,
                [
                    "offer", "resolve-entity", "--cloud", "aws",
                    "--code", "sku-first", "--code", "code-second",
                ],
            )
        self.assertEqual(result.exit_code, 0, result.output)
        document = json.loads(result.output)
        self.assertEqual([item["entityId"] for item in document["results"]], ["prod-first", "prod-second"])
        self.assertEqual(document["notFound"], [])
        self.assertEqual(client.list_entities.call_count, 1)

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
