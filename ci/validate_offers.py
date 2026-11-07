"""Validate the AWS authoring template and shared vendor rules without network calls."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "offer"
PLACEHOLDER = re.compile(r"\{([^}|]+)")
VENDOR_FIELDS = {
    "aboutVendor", "consoleSummary", "supportSummary", "supportContact",
    "supportScope", "trademarkStatement", "billingSummary", "sshSummary",
}


def placeholders(text: str, where: str, namespaces: set[str]) -> list[str]:
    result = []
    for path in PLACEHOLDER.findall(str(text)):
        if not path or path.split(".")[0].split("[")[0] not in namespaces:
            raise ValueError(f"{where}: placeholder has no declared namespace: {{{path}}}")
        result.append(path)
    return result


def validate_template(template: dict) -> None:
    if template.get("templateId") != "aws-ami-v1":
        raise ValueError("unsupported template id")
    namespaces = template.get("namespaces")
    if not isinstance(namespaces, list) or not namespaces or any(
        not isinstance(namespace, str) or not namespace for namespace in namespaces
    ):
        raise ValueError("template.namespaces must contain at least one namespace")
    namespaces = set(namespaces)
    target = template.get("target") or {}
    if target.get("platform") != "aws" or target.get("entityType") != "AmiProduct@1.0":
        raise ValueError("invalid AWS target")
    if target.get("changeType") != "UpdateInformation":
        raise ValueError("invalid change type")
    if "boldLongDescriptionHeadings" in template and not isinstance(template["boldLongDescriptionHeadings"], bool):
        raise ValueError("boldLongDescriptionHeadings must be a boolean")
    for resource in template.get("AdditionalResources") or []:
        if set(resource) != {"Text", "Url"} or not str(resource["Url"]).startswith("https://"):
            raise ValueError("invalid AdditionalResources item")
        placeholders(resource["Text"], "AdditionalResources", namespaces)
        placeholders(resource["Url"], "AdditionalResources", namespaces)
    for field, value in template.get("content", {}).items():
        values = value if isinstance(value, list) else [value]
        for item in values:
            placeholders(item, f"content.{field}", namespaces)
    for section in template.get("longDescriptionSections", []):
        placeholders(section.get("heading", ""), "longDescriptionSections", namespaces)
        placeholders(section.get("text", ""), "longDescriptionSections", namespaces)
    for section in template.get("previewOnlySections", []):
        if not isinstance(section, dict) or set(section) != {"id", "heading", "text"}:
            raise ValueError("previewOnlySections items require id, heading and text")
        placeholders(section.get("id", ""), "previewOnlySections", namespaces)
        placeholders(section.get("heading", ""), "previewOnlySections", namespaces)
        placeholders(section.get("text", ""), "previewOnlySections", namespaces)


def validate_vendor(vendor: dict) -> None:
    missing = [field for field in VENDOR_FIELDS if not isinstance(vendor.get(field), str) or not vendor[field].strip()]
    if missing:
        raise ValueError(f"missing vendor text: {', '.join(sorted(missing))}")
    highlights = vendor.get("highlights")
    if not isinstance(highlights, list) or not 1 <= len(highlights) <= 3 or any(
        not isinstance(item, str) or not item.strip() for item in highlights
    ):
        raise ValueError("vendor.highlights must contain 1–3 non-empty strings")


def main() -> int:
    try:
        template = json.loads((DATA / "templates" / "aws-ami.json").read_text(encoding="utf-8"))
        vendor = json.loads((DATA / "vendor.json").read_text(encoding="utf-8"))
        validate_template(template)
        validate_vendor(vendor)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"offer validation failed: {error}", file=sys.stderr)
        return 1
    print("AWS template and vendor rules are valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
