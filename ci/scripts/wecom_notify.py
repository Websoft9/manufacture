#!/usr/bin/env python3
"""Send a best-effort WeCom markdown notification using WECOM_WEBHOOK."""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

MARKDOWN_LIMIT = 4096
OFFER_LIST_MENTION_MOBILE = "17773112964"
OFFER_LIST_MENTION_MESSAGE = "Please check issue and update offers"


def truncate_utf8(text: str, limit: int = MARKDOWN_LIMIT) -> str:
    encoded = text.encode("utf-8")
    if len(encoded) <= limit:
        return text
    suffix = "\n…"
    budget = max(0, limit - len(suffix.encode("utf-8")))
    return encoded[:budget].decode("utf-8", errors="ignore") + suffix


def _send(payload: dict, webhook: str) -> bool:
    if not webhook:
        print("::warning::WECOM_WEBHOOK is not set; skipping notification")
        return False

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    for attempt in range(3):
        try:
            request = urllib.request.Request(
                webhook,
                data=body,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(request, timeout=5) as response:
                result = json.load(response)
            if isinstance(result, dict) and result.get("errcode") == 0:
                print("WeCom notification sent")
                return True
        except (urllib.error.URLError, OSError, ValueError):
            pass
        if attempt < 2:
            time.sleep(1)

    print("::warning::WeCom notification failed after 3 attempts")
    return False


def send_markdown(content: str, webhook: str) -> bool:
    return _send(
        {"msgtype": "markdown", "markdown": {"content": truncate_utf8(content)}},
        webhook,
    )


def send_text(
    content: str,
    webhook: str,
    mentioned_list: list[str] | None = None,
    mentioned_mobile_list: list[str] | None = None,
) -> bool:
    text: dict[str, object] = {"content": content}
    if mentioned_list:
        text["mentioned_list"] = mentioned_list
    if mentioned_mobile_list:
        text["mentioned_mobile_list"] = mentioned_mobile_list
    return _send({"msgtype": "text", "text": text}, webhook)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--markdown-file", required=True, type=Path)
    parser.add_argument("--offer-list-notify", action="store_true")
    args = parser.parse_args()
    try:
        content = args.markdown_file.read_text(encoding="utf-8")
    except OSError:
        print("::warning::Could not read the WeCom notification message")
        return 0
    webhook = os.environ.get("WECOM_WEBHOOK", "")
    if not send_markdown(content, webhook):
        return 0

    if args.offer_list_notify:
        send_text(
            OFFER_LIST_MENTION_MESSAGE,
            webhook,
            mentioned_mobile_list=[OFFER_LIST_MENTION_MOBILE],
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
