#!/usr/bin/env python3
"""Compose and send the final product freshness workflow notification."""

from __future__ import annotations

import os

from wecom_notify import send_markdown


def main() -> int:
    repository = os.environ.get("REPOSITORY", "")
    run_url = os.environ.get("RUN_URL", "")
    event_name = os.environ.get("EVENT_NAME", "unknown")
    selected = os.environ.get("SELECTED_PLATFORM", "").strip() or "all configured platforms"
    skipped = os.environ.get("SKIPPED_PLATFORMS", "").strip()
    resolver_result = os.environ.get("RESOLVER_RESULT", "unknown")
    product_result = os.environ.get("PRODUCT_RESULT", "unknown")
    succeeded = resolver_result == "success" and product_result == "success"
    status = "completed" if succeeded else "failed"

    lines = [
        "# Marketplace product freshness",
        f"> Repository: {repository}",
        f"> Trigger: {event_name}",
        f"> Selection: {selected}",
        f"> Result: **{status}**",
        f"> Platform jobs: {product_result}",
    ]
    if skipped:
        lines.append(f"> Not configured yet: {skipped}")
    if run_url:
        lines.extend(["", f"[View workflow run and platform reports]({run_url})"])
    if not succeeded:
        lines.append("Check the run logs for the failed step and its remediation.")

    send_markdown("\n".join(lines), os.environ.get("WECOM_WEBHOOK", ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
