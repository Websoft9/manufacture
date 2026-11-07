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
            "hasenterprise": False,
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

    def render(self):
        return offer.render(self.item, "20.0", self.vendor_path)

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
        self.item["hasenterprise"] = True
        self.write()
        value = self.render()
        self.assertIn("Deploy Odoo 20.0", value["content"]["ShortDescription"])
        self.assertNotIn("Community Edition", value["content"]["ShortDescription"])
        self.assertIn(
            "This product packages Odoo Community Edition as a hardened AMI",
            value["content"]["LongDescription"],
        )
        self.assertIn(
            "Odoo is a trademark of its respective owner",
            value["content"]["LongDescription"],
        )
        self.assertNotIn("Jupyter", str(value["content"]))
        self.assertEqual(value["publishBlockers"], ["listing: Catalog EntityId is missing"])
        result = self.runner.invoke(
            cli, self.args("build") + ["--cloud", "aws", "--publish-ready"]
        )
        self.assertNotEqual(result.exit_code, 0)

    def test_short_description_uses_multi_version_choice(self):
        self.item["hasenterprise"] = True
        self.write()
        value = offer.render(
            self.item,
            "20.0",
            self.vendor_path,
            version_options=["20.0", "19.0", "18.0", "17.0", "latest"],
        )
        self.assertEqual(
            value["content"]["ShortDescription"],
            "Choose from Odoo 20.0, 19.0, 18.0, or 17.0 at launch for self-hosting "
            "without upstream forks, backed by a 24-hour response SLA on business days. "
            "Use the Websoft9 Console to manage HTTPS, backups, monitoring, "
            "upgrades, and rollback.",
        )

    def test_short_description_uses_single_version(self):
        self.item["hasenterprise"] = True
        self.write()
        value = offer.render(
            self.item,
            "20.0",
            self.vendor_path,
            version_options=["20.0", "latest"],
        )
        self.assertEqual(
            value["content"]["ShortDescription"],
            "Deploy Odoo 20.0 for self-hosting without upstream forks, backed by "
            "a 24-hour response SLA on business days. Use the Websoft9 Console "
            "to manage HTTPS, backups, monitoring, upgrades, and rollback.",
        )

    def test_components_are_inserted_before_nginx_and_docker(self):
        self.item["components"] = []
        self.item["hasenterprise"] = True
        self.write()
        empty_included = next(
            section["text"]
            for section in self.render()["preview"]["longDescriptionSections"]
            if section["heading"] == "What is included?"
        )
        self.assertEqual(
            empty_included,
            "Odoo Community Edition, Nginx, Docker and Websoft9 Console.",
        )
        self.item["components"] = ["PostgreSQL", "pgAdmin"]
        self.write()
        included = next(
            section["text"]
            for section in self.render()["preview"]["longDescriptionSections"]
            if section["heading"] == "What is included?"
        )
        self.assertEqual(
            included,
            "Odoo Community Edition, PostgreSQL, pgAdmin, Nginx, Docker and Websoft9 Console.",
        )

    def test_multi_version_apps_append_selection_to_included(self):
        self.item["hasenterprise"] = True
        self.write()
        value = offer.render(
            self.item, "20.0", self.vendor_path, version_options=["20", "19", "18"]
        )
        included = next(
            section["text"]
            for section in value["preview"]["longDescriptionSections"]
            if section["heading"] == "What is included?"
        )
        self.assertIn("Odoo Community Edition 20/19/18 for selection,", included)

    def test_latest_is_excluded_from_version_selection(self):
        self.item["hasenterprise"] = True
        self.write()
        value = offer.render(
            self.item, "20.0", self.vendor_path, version_options=["20", "latest", "19"]
        )
        included = next(
            section["text"]
            for section in value["preview"]["longDescriptionSections"]
            if section["heading"] == "What is included?"
        )
        self.assertIn("Odoo Community Edition 20/19 for selection,", included)
        self.assertNotIn("latest", included)

    def test_single_version_or_non_multi_app_has_no_selection(self):
        single = offer.render(
            self.item, "20.0", self.vendor_path, version_options=["20"]
        )
        texts = [section["text"] for section in single["preview"]["longDescriptionSections"]]
        self.assertFalse(any("for selection" in text for text in texts))

        with mock.patch.object(offer, "MULTI_VERSION_APPS", frozenset()):
            other = offer.render(
                self.item, "20.0", self.vendor_path, version_options=["20", "19"]
            )
        texts = [section["text"] for section in other["preview"]["longDescriptionSections"]]
        self.assertFalse(any("for selection" in text for text in texts))

    def test_display_version_keeps_at_most_two_components(self):
        self.assertEqual(offer.display_version("20.0.1"), "20.0")
        self.assertEqual(offer.display_version("v2026.9.24"), "v2026.9")
        self.assertEqual(offer.display_version("19.0"), "19.0")
        self.assertEqual(offer.display_version("18"), "18")
        self.assertEqual(offer.display_version("v3-core"), "v3-core")

    def test_multi_version_selection_uses_display_versions(self):
        self.item["hasenterprise"] = True
        self.write()
        value = offer.render(
            self.item,
            "20.0.1",
            self.vendor_path,
            version_options=["20.0.1", "19.0.2", "19.0.3", "latest"],
        )
        included = next(
            section["text"]
            for section in value["preview"]["longDescriptionSections"]
            if section["heading"] == "What is included?"
        )
        self.assertIn("Odoo Community Edition 20.0/19.0 for selection,", included)
        self.assertNotIn("20.0.1", value["content"]["LongDescription"])

    def test_load_versions_accepts_single_value_and_lists(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "versions.json"
            path.write_text(
                json.dumps(
                    [
                        {"id": "odoo", "version": ["20", "19"]},
                        {"id": "mysql", "version": "26.10"},
                        {"id": "redis", "versions": ["8", "7"]},
                        {"id": "no-version"},
                    ]
                ),
                encoding="utf-8",
            )
            self.assertEqual(
                catalog_data.load_versions(str(path)),
                {"odoo": ["20", "19"], "mysql": ["26.10"], "redis": ["8", "7"]},
            )

    def test_long_description_edition_follows_hasenterprise(self):
        self.item["hasenterprise"] = False
        self.write()
        community = self.render()["preview"]["longDescriptionSections"][0]["text"]
        self.assertIn(
            "This product packages Odoo as a hardened AMI",
            community,
        )
        self.assertNotIn("Community Edition", community)
        self.item["hasenterprise"] = True
        self.write()
        enterprise = self.render()["preview"]["longDescriptionSections"][0]["text"]
        self.assertIn(
            "This product packages Odoo Community Edition as a hardened AMI",
            enterprise,
        )

    def test_hasenterprise_uses_open_source_offer_wording(self):
        self.item["hasenterprise"] = True
        self.write()
        pricing = next(
            section["text"]
            for section in self.render()["preview"]["longDescriptionSections"]
            if section["heading"] == "What you pay for"
        )
        self.assertIn(
            "This offer provides the Community Edition of the application. "
            "It does not include any commercial edition.",
            pricing,
        )
        self.assertNotIn("provided under its commercial edition", pricing)

    def test_short_description_does_not_use_hasenterprise_wording(self):
        descriptions = set()
        for value in (False, True, None, "missing"):
            item = copy.deepcopy(self.item)
            if value == "missing":
                item.pop("hasenterprise", None)
            else:
                item["hasenterprise"] = value
            descriptions.add(offer.render(item, "20.0")["content"]["ShortDescription"])
        self.assertEqual(len(descriptions), 1)
        self.assertNotIn("Community Edition", descriptions.pop())

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
            [section["text"] for section in document["longDescriptionSections"] if section["text"].startswith("No separate license fee")],
            ["No separate license fee is charged for the Community Edition. The Websoft9 software fee covers the Console, operations toolset, and business-day support with a 24-hour response SLA. AWS infrastructure charges are billed separately by AWS."],
        )

    def test_long_description_headings_use_markdown_bold(self):
        value = self.render()
        self.assertIn("**What is included?**\n", value["content"]["LongDescription"])
        headings = [
            section["heading"]
            for section in value["preview"]["longDescriptionSections"]
            if section["heading"]
        ]
        self.assertTrue(all("**" not in heading for heading in headings))

    def test_preview_only_sections_are_not_submitted(self):
        value = self.render()
        reference = {item["id"]: item for item in value["preview"]["previewOnlySections"]}
        self.assertEqual(set(reference), {"usage", "refunds"})
        self.assertIn("Launch the AMI", reference["usage"]["text"])
        self.assertIn("No refunds are issued", reference["refunds"]["text"])
        self.assertNotIn("Launch the AMI", str(value["content"]))
        self.assertNotIn("No refunds are issued", str(value["content"]))

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
        self.assertIn("## Reference sections (not submitted)", text)
        self.assertIn("### Refunds", text)

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
        with self.assertRaisesRegex(ValueError, "unsupported"):
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
