from __future__ import annotations

import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import offer_update as flow


class OfferUpdateTests(unittest.TestCase):
    def setUp(self):
        self.product = flow.load_product("odoo")
        self.product["listings"]["aws"]["entityId"] = "prod-test123"
        self.provider = flow.offer.read_json(flow.offer.DATA / "provider.json")
        for check in [self.product["application"]["verification"], self.provider["verification"],
                      self.product["listings"]["aws"]["verification"],
                      self.product["listings"]["aws"]["deployment"]["verification"],
                      self.product["listings"]["aws"]["commercial"]["verification"]]:
            check.update(status="verified", checkedAt="2026-11-03", evidence=["Synthetic test evidence"])
        original = flow.offer.render

        def render(path):
            value = original(path)
            value["publishBlockers"] = []  # Provider is a separately reviewed synthetic fixture here.
            return value

        self.render_patch = patch.object(flow.offer, "render", side_effect=render)
        self.render_patch.start()
        self.addCleanup(self.render_patch.stop)
        self.bundle = flow.render_product(self.product)
        content = copy.deepcopy(self.bundle["content"])
        support = content.pop("SupportDescription")
        content["ProductTitle"] = "Old title"
        self.live = {"EntityIdentifier": "prod-test123@1", "EntityType": "AmiProduct@1.0",
                     "DetailsDocument": {"Description": content, "SupportInformation": {"Description": support}}}
        self.client = Mock()
        self.client.describe_entity.return_value = self.live
        self.state = {"issue": 1, "request": {"key": "odoo", "platform": "aws"},
                      "product": self.product, "baseSourceHash": self.bundle["sourceHash"]}
        flow.replan(self.state, self.client)

    def test_issue_form_and_comment_commands(self):
        self.assertEqual(flow.request_fields("### 应用\n\nodoo\n\n### 目标平台\n\naws\n\n### 更新目标\n\nFix wording"),
                         {"key": "odoo", "platform": "aws"})
        self.assertEqual(flow.parse_command("/offer optimize 更简洁"), ("optimize", "更简洁"))
        with self.assertRaises(ValueError):
            flow.request_fields("### 应用\n../../private\n### 目标平台\naws")
        with self.assertRaises(ValueError):
            flow.parse_command("/offer publish-other")

    def test_edit_cannot_modify_fixed_fields_or_template_overrides(self):
        for field in ["includedComponents", "edition", "verification", "contentOverrides", "LongDescription"]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                flow.patch_product(self.product, {field: "new"})
        updated = flow.patch_product(self.product, {"summary": "Revised description"})
        self.assertEqual(updated["application"]["summary"], "Revised description")
        self.assertNotEqual(updated, self.product)
        updated["listings"]["aws"]["contentOverrides"] = {"LongDescription": "bypass"}
        with self.assertRaises(ValueError):
            flow.render_product(updated)

    def test_edit_retains_fixed_sections_and_invalidates_review(self):
        token = self.state["draftHash"]
        flow.approve(self.state, token, "reviewer")
        self.state["product"] = flow.patch_product(self.product, {"summary": "Updated application wording."})
        flow.replan(self.state, self.client)
        self.assertIsNone(self.state["approval"])
        self.assertNotEqual(self.state["draftHash"], token)
        rendered = self.state["bundle"]["content"]
        self.assertEqual(rendered["SupportDescription"], self.bundle["content"]["SupportDescription"])
        self.assertIn(self.product["listings"]["aws"]["commercial"]["billingSummary"], rendered["LongDescription"])

    def test_approval_and_publication_are_separate_and_hash_bound(self):
        save = Mock()
        token = self.state["draftHash"]
        with self.assertRaises(ValueError):
            flow.publish(self.state, token, self.client, save)
        with self.assertRaises(ValueError):
            flow.approve(self.state, "wrong-hash", "reviewer")
        self.state["plan"]["publishBlockers"] = ["provider: unverified"]
        self.state["draftHash"] = flow.draft_hash(self.state)
        with self.assertRaises(ValueError):
            flow.approve(self.state, self.state["draftHash"], "reviewer")
        self.client.start_change_set.assert_not_called()

    def test_publish_persists_id_then_status_reads_back_then_completion(self):
        token = self.state["draftHash"]
        flow.approve(self.state, token, "reviewer")
        self.client.start_change_set.return_value = {"ChangeSetId": "cs-test"}
        saved = []
        flow.publish(self.state, token, self.client, lambda state: saved.append(copy.deepcopy(state)))
        self.assertEqual(saved[0]["changeSetId"], "cs-test")
        self.assertEqual(self.state["status"], "发布中")
        self.assertEqual(self.client.start_change_set.call_args.kwargs["ClientRequestToken"], self.state["plan"]["planHash"])
        with self.assertRaises(ValueError):
            flow.publish(self.state, token, self.client, Mock())
        self.client.describe_change_set.return_value = {"ChangeSetId": "cs-test", "Status": "SUCCEEDED"}
        content = copy.deepcopy(self.bundle["content"])
        support = content.pop("SupportDescription")
        self.client.describe_entity.return_value = {**self.live, "EntityIdentifier": "prod-test123@2",
            "DetailsDocument": {"Description": content, "SupportInformation": {"Description": support}}}
        flow.status(self.state, self.client)
        self.assertTrue(self.state["readBackVerified"])
        self.assertEqual(self.state["status"], "待前台确认")

    def test_stale_live_revision_never_submits(self):
        token = self.state["draftHash"]
        flow.approve(self.state, token, "reviewer")
        self.live["EntityIdentifier"] = "prod-test123@2"
        with self.assertRaises(ValueError):
            flow.publish(self.state, token, self.client, Mock())
        self.client.start_change_set.assert_not_called()

    def test_source_change_invalidates_draft(self):
        with patch.object(flow, "load_product", return_value=self.product):
            flow.check_source(self.state, self.state["request"])
            self.product["application"]["summary"] = "Changed repo source"
            with self.assertRaises(ValueError):
                flow.check_source(self.state, self.state["request"])

    def test_pending_failure_and_readback_mismatch(self):
        self.state["changeSetId"] = "cs-test"
        for aws_status, expected in [("APPLYING", "发布中"), ("FAILED", "需处理：发布失败"), ("SUCCEEDED", "需处理：回读不一致")]:
            self.client.describe_change_set.return_value = {"Status": aws_status}
            flow.status(self.state, self.client)
            self.assertEqual(self.state["status"], expected)

    def test_ai_cannot_return_fixed_fields_and_has_no_aws_environment(self):
        result = Mock(returncode=0, stdout=json.dumps({"includedComponents": ["invented"]}))
        with patch.object(flow.subprocess, "run", return_value=result) as run:
            with self.assertRaises(ValueError):
                flow.optimize(self.product, "Improve")
        self.assertNotIn("GH_TOKEN", run.call_args.kwargs["env"])
        self.assertNotIn("AWS_ACCESS_KEY_ID", run.call_args.kwargs["env"])
        self.assertIn("--deny-tool=shell", run.call_args.args[0])

    def test_summary_escapes_untrusted_content(self):
        self.state["plan"]["diff"]["ProductTitle"]["before"] = "</pre><script>alert(1)</script>@everyone"
        text = flow.summary(self.state)
        self.assertNotIn("<script>", text)
        self.assertNotIn("@everyone", text)
        self.assertIn("/offer approve", text)

    def test_issue_comment_edit_approve_publish_and_status_roundtrip(self):
        context = {"repo": "example/repo", "issue": 1, "actor": "reviewer",
                   "request": self.state["request"], "action": "edit",
                   "argument": '```json\n{"summary":"Updated application summary."}\n```'}
        current = copy.deepcopy(self.state)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            with patch.object(flow, "workdir", return_value=path), \
                 patch.object(flow, "previous", side_effect=lambda _: copy.deepcopy(current)), \
                 patch.object(flow, "load_product", return_value=self.product), \
                 patch.object(flow.offer, "aws_client", return_value=self.client):
                for action in ["edit", "approve", "publish", "status"]:
                    context["action"] = action
                    if action in {"approve", "publish"}:
                        context["argument"] = current["draftHash"]
                    self.client.start_change_set.return_value = {"ChangeSetId": "cs-test"}
                    self.client.describe_change_set.return_value = {"Status": "APPLYING"}
                    (path / "context.json").write_text(json.dumps(context))
                    flow.execute()
                    current = json.loads((path / "state.json").read_text())
                    self.assertNotIn("error", current)
                self.assertEqual(current["status"], "发布中")
                self.assertEqual(current["product"]["application"]["summary"], "Updated application summary.")
                self.client.start_change_set.assert_called_once()

    def test_gate_checks_current_operator_permission_before_cloud_access(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "event.json").write_text(json.dumps({"issue": {"number": 1}}))
            issue = {"title": "[Update app] Odoo", "state": "open", "body": "### 应用\nodoo\n### 目标平台\naws"}
            with patch.dict(os.environ, {"GITHUB_EVENT_PATH": str(path / "event.json"),
                 "GITHUB_REPOSITORY": "example/repo", "GITHUB_ACTOR": "visitor",
                 "GITHUB_TRIGGERING_ACTOR": "visitor", "OFFER_ISSUE": "", "OFFER_COMMAND": ""}), \
                 patch.object(flow, "gh", side_effect=[issue, {"permission": "read"}]), \
                 patch.object(flow.offer, "aws_client") as aws:
                with self.assertRaisesRegex(ValueError, "write"):
                    flow.gate()
                aws.assert_not_called()

    def test_rejects_artifact_pointer_from_other_workflow(self):
        context = {"repo": "example/repo", "issue": 1}
        comment = {"user": {"login": "github-actions[bot]"},
                   "body": "<!-- offer-update:123:" + "a" * 64 + " -->"}
        with patch.object(flow, "comments", return_value=[comment]), \
             patch.object(flow, "gh", return_value={"path": "another.yml", "repository": {"full_name": "example/repo"}}):
            with self.assertRaises(ValueError):
                flow.previous(context)


if __name__ == "__main__":
    unittest.main()
