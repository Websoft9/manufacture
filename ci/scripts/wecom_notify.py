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


def truncate_utf8(text: str, limit: int = MARKDOWN_LIMIT) -> str:
    encoded = text.encode("utf-8")
    if len(encoded) <= limit:
        return text
    suffix = "\n…"
    budget = max(0, limit - len(suffix.encode("utf-8")))
    return encoded[:budget].decode("utf-8", errors="ignore") + suffix


def send_markdown(content: str, webhook: str) -> bool:
    if not webhook:
        print("::warning::WECOM_WEBHOOK is not set; skipping notification")
        return False

    payload = json.dumps(
        {"msgtype": "markdown", "markdown": {"content": truncate_utf8(content)}},
        ensure_ascii=False,
    ).encode("utf-8")
    for attempt in range(3):
        try:
            request = urllib.request.Request(
                webhook,
                data=payload,
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--markdown-file", required=True, type=Path)
    args = parser.parse_args()
    try:
        content = args.markdown_file.read_text(encoding="utf-8")
    except OSError:
        print("::warning::Could not read the WeCom notification message")
        return 0
    send_markdown(content, os.environ.get("WECOM_WEBHOOK", ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
