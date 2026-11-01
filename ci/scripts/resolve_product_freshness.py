#!/usr/bin/env python3
"""Resolve the selected marketplace skills into a GitHub Actions matrix."""

import json
import os
from pathlib import Path


SKILLS = {
    "alibabacloud": "aliyun-product-freshness",
    "azure": "azure-product-freshness",
    "aws": "aws-product-freshness",
    "huaweicloud": "huaweicloud-product-freshness",
    "googlecloud": "googlecloud-product-freshness",
}


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    selected = os.environ.get("SELECTED_PLATFORM", "").strip().lower() or "all"
    if event_name == "schedule":
        selected = "all"

    if selected != "all" and selected not in SKILLS:
        raise SystemExit(f"Unsupported platform: {selected}")

    candidates = SKILLS.items() if selected == "all" else [(selected, SKILLS[selected])]
    configured = []
    skipped = []
    for platform, skill in candidates:
        if (root / "skills" / skill / "SKILL.md").is_file():
            configured.append({"platform": platform, "skill": skill})
        elif selected == "all":
            skipped.append(platform)
        else:
            raise SystemExit(
                f"No skill is configured for {platform}. Add "
                f"skills/{skill}/SKILL.md before selecting this platform."
            )

    if not configured:
        raise SystemExit("No product freshness skills are configured.")

    output = os.environ.get("GITHUB_OUTPUT")
    values = {
        "matrix": json.dumps({"include": configured}, separators=(",", ":")),
        "skipped": ",".join(skipped),
    }
    if output:
        with open(output, "a", encoding="utf-8") as file:
            for name, value in values.items():
                file.write(f"{name}={value}\n")
    else:
        print(json.dumps(values, indent=2))


if __name__ == "__main__":
    main()
