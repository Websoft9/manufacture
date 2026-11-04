from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import product_freshness_notification
import wecom_notify


class WecomNotifyTests(unittest.TestCase):
    def test_truncate_utf8_respects_byte_limit(self) -> None:
        content = wecom_notify.truncate_utf8("产品" * 2000)
        self.assertLessEqual(len(content.encode("utf-8")), 4096)
        self.assertTrue(content.endswith("…"))

    def test_send_markdown_posts_and_checks_response(self) -> None:
        requests = []

        def post(request, timeout):
            requests.append(request)
            self.assertEqual(timeout, 5)
            return io.BytesIO(b'{"errcode":0}')

        with patch.object(wecom_notify.urllib.request, "urlopen", post):
            self.assertTrue(wecom_notify.send_markdown("检查完成", "https://example.test/hook"))
        self.assertEqual(len(requests), 1)
        self.assertEqual(
            json.loads(requests[0].data),
            {"msgtype": "markdown", "markdown": {"content": "检查完成"}},
        )

    def test_send_text_supports_mentions(self) -> None:
        requests = []

        def post(request, timeout):
            requests.append(request)
            return io.BytesIO(b'{"errcode":0}')

        with patch.object(wecom_notify.urllib.request, "urlopen", post):
            self.assertTrue(
                wecom_notify.send_text(
                    "请查看通知",
                    "https://example.test/hook",
                    ["tanxiao"],
                    ["13800000000"],
                )
            )
        self.assertEqual(
            json.loads(requests[0].data),
            {
                "msgtype": "text",
                "text": {
                    "content": "请查看通知",
                    "mentioned_list": ["tanxiao"],
                    "mentioned_mobile_list": ["13800000000"],
                },
            },
        )

    def test_offer_list_notification_mentions_configured_mobile(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            message = Path(directory) / "message.md"
            message.write_text("通知内容", encoding="utf-8")
            with patch.dict(
                os.environ,
                {"WECOM_WEBHOOK": "https://example.test/hook"},
                clear=True,
            ), patch.object(wecom_notify, "send_markdown", return_value=True) as markdown, patch.object(
                wecom_notify, "send_text"
            ) as text:
                with patch.object(
                    sys,
                    "argv",
                    ["wecom_notify.py", "--markdown-file", str(message), "--offer-list-notify"],
                ):
                    self.assertEqual(wecom_notify.main(), 0)
        markdown.assert_called_once()
        text.assert_called_once()
        self.assertEqual(text.call_args.args[0], "Please check issue and update offers")
        self.assertEqual(
            text.call_args.kwargs["mentioned_mobile_list"],
            [wecom_notify.OFFER_LIST_MENTION_MOBILE],
        )

    def test_failed_delivery_does_not_log_webhook(self) -> None:
        output = io.StringIO()
        with (
            patch.object(wecom_notify.urllib.request, "urlopen", side_effect=urllib.error.URLError("secret-url")),
            patch.object(wecom_notify.time, "sleep"),
            patch("sys.stdout", output),
        ):
            self.assertFalse(wecom_notify.send_markdown("failed", "https://example.test/?key=secret"))
        self.assertNotIn("secret", output.getvalue())

    def test_product_notice_includes_run_link_and_status(self) -> None:
        with patch.dict(
            os.environ,
            {
                "REPOSITORY": "Websoft9/manufacture",
                "RUN_URL": "https://github.test/run/1",
                "EVENT_NAME": "workflow_dispatch",
                "SELECTED_PLATFORM": "alibabacloud",
                "RESOLVER_RESULT": "success",
                "PRODUCT_RESULT": "failure",
                "SKIPPED_PLATFORMS": "",
                "WECOM_WEBHOOK": "https://example.test/hook",
            },
            clear=True,
        ), patch.object(product_freshness_notification, "send_markdown") as send:
            self.assertEqual(product_freshness_notification.main(), 0)
        message = send.call_args.args[0]
        self.assertIn("**failed**", message)
        self.assertIn("https://github.test/run/1", message)


if __name__ == "__main__":
    unittest.main()
