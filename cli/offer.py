"""Deterministic AWS listing rendering, validation and change planning."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from .aws_marketplace import (
    CONTENT_FIELDS as FIELDS,
    FIELD_LIMITS as LIMITS,
    aws_call,
    aws_client,
    build_update_request,
    change_status,
    current_content,
)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "offer"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


PLACEHOLDER = re.compile(r"\{([A-Za-z_][A-Za-z0-9_.]*(?:\[\d+\])*)\}")


def resolve_placeholder(path: str, roots: dict[str, Any]) -> Any:
    normalized = re.sub(r"\[(\d+)\]", r".\1", path)
    current: Any = roots
    for part in normalized.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            raise ValueError(f"template placeholder not found: {path}")
    return current


def format_template(text: str, roots: dict[str, Any]) -> Any:
    match = PLACEHOLDER.fullmatch(text.strip())
    if match:
        return resolve_placeholder(match.group(1), roots)
    return PLACEHOLDER.sub(lambda item: str(resolve_placeholder(item.group(1), roots)), text)


def render(product_path: Path | dict, vendor_path: Path = DATA / "vendor.json", template_path: Path = DATA / "templates/aws-ami.json") -> dict:
    product = read_json(product_path) if isinstance(product_path, (str, Path)) else product_path
    schema = read_json(DATA / "product.schema.json")
    errors = sorted(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(product), key=lambda error: str(error.path))
    if errors:
        raise ValueError("; ".join(f"{'.'.join(map(str, error.path))}: {error.message}" for error in errors))
    vendor, template = read_json(vendor_path), read_json(template_path)
    listing, app = product["listings"]["aws"], product["application"]
    if template.get("templateId") != listing["templateId"] or template.get("schemaVersion") != 1:
        raise ValueError("unsupported or mismatched template")
    vendor_fields = (
        "aboutVendor",
        "billingSummary",
        "consoleSummary",
        "sshSummary",
        "supportSummary",
        "supportContact",
        "supportScope",
        "trademarkStatement",
    )
    for field in vendor_fields:
        if not isinstance(vendor.get(field), str) or not vendor[field].strip():
            raise ValueError(f"vendor.{field} must be non-empty text")
    highlights = vendor.get("highlights")
    if not isinstance(highlights, list) or not 1 <= len(highlights) <= 3 or any(
        not isinstance(item, str) or not item.strip() for item in highlights
    ):
        raise ValueError("vendor.highlights must contain 1–3 non-empty strings")
    application = {
        **app,
        "id": product["key"],
        "includedComponentsText": ", ".join(app["includedComponents"]) + ".",
        "useCasesText": "; ".join(app["useCases"]) + ".",
    }
    roots = {
        **app,
        **{field: vendor[field] for field in vendor_fields},
        "includedComponents": application["includedComponentsText"],
        "useCases": application["useCasesText"],
        "key": product["key"],
        "product": product,
        "catalog": application,
        "application": application,
        "vendor": vendor,
        "aws": listing,
    }
    target = template.get("target") or {}
    if target:
        if target.get("platform") not in (None, "aws"):
            raise ValueError("template target.platform must be aws")
        if target.get("entityType") not in (None, listing["entityType"]):
            raise ValueError("template target.entityType does not match the listing")
        if target.get("changeType") not in (None, "UpdateInformation"):
            raise ValueError("template target.changeType must be UpdateInformation")
    content = {key: [format_template(item, roots) for item in value] if isinstance(value, list) else format_template(value, roots) for key, value in template["content"].items()}
    rendered_sections = [
        {
            "heading": format_template(section["heading"], roots),
            "text": format_template(section["text"], roots),
        }
        for section in template["longDescriptionSections"]
    ]
    content["LongDescription"] = "\n\n".join(
        (section["heading"] + "\n" if section["heading"] else "") + section["text"]
        for section in rendered_sections
    )
    for field in ("Categories", "VideoUrls"):
        if not content.get(field):
            content.pop(field, None)
    if not content.get("LogoUrl"):
        content.pop("LogoUrl", None)
    for field, path in template.get("fieldSources", {}).items():
        current = roots
        for part in str(path).split("."):
            if not isinstance(current, dict) or part not in current:
                raise ValueError(f"template fieldSources.{field} path not found: {path}")
            current = current[part]
        content[field] = current
    content.setdefault("SearchKeywords", app["searchKeywords"])
    resources = template.get("AdditionalResources", template.get("additionalResources")) or []
    if resources:
        content["AdditionalResources"] = [
            {key: format_template(str(value), roots) for key, value in item.items()} for item in resources
        ]
    content.update(listing["contentOverrides"])
    # Absent optional fields preserve the current AWS value. Empty arrays never clear it implicitly.
    validate_content(content)
    blockers = []
    if not app.get("version"):
        blockers.append("catalog: version is missing")
    if not listing["entityId"]:
        blockers.append("listing: Catalog EntityId is missing")
    preview_content = {
        key: value
        for key, value in content.items()
        if key not in {"LongDescription", "AdditionalResources"}
    }
    preview = {
        "schemaVersion": template["schemaVersion"],
        "templateId": template["templateId"],
        "target": template.get("target", {}),
        "AdditionalResources": content.get("AdditionalResources", []),
        "content": preview_content,
        "longDescriptionSections": rendered_sections,
    }
    return {
        "schemaVersion": 1, "key": product["key"], "entityId": listing["entityId"], "entityType": listing["entityType"],
        "templateId": template["templateId"], "content": content, "preview": preview,
        "publishBlockers": blockers,
        "sourceHash": digest({"product": product, "vendor": vendor, "template": template}),
    }


def validate_content(content: dict) -> None:
    if not content or set(content) - FIELDS:
        raise ValueError("unsupported or empty UpdateInformation content")
    for field, maximum in LIMITS.items():
        value = content.get(field)
        if not isinstance(value, str) or not value.strip() or len(value) > maximum:
            raise ValueError(f"{field} must contain 1–{maximum} characters")
    for field, maximum, item_max in (("Highlights", 3, 500), ("SearchKeywords", 15, 50), ("Categories", 3, None)):
        if field not in content:
            continue
        values = content[field]
        if not isinstance(values, list) or not 1 <= len(values) <= maximum or any(not isinstance(item, str) or not item.strip() or (item_max and len(item) > item_max) for item in values):
            raise ValueError(f"invalid {field}")
        if len({item.casefold() for item in values}) != len(values):
            raise ValueError(f"duplicate {field}")
    if sum(map(len, content["SearchKeywords"])) > 250:
        raise ValueError("SearchKeywords exceeds 250 combined characters")
    for field in ("LogoUrl", "VideoUrls", "AdditionalResources"):
        if field not in content:
            continue
        value = content[field]
        if field == "LogoUrl":
            urls = [value]
        elif field == "VideoUrls":
            if not isinstance(value, list) or len(value) > 1:
                raise ValueError("VideoUrls supports at most one URL")
            urls = value
        else:
            if not isinstance(value, list) or len(value) > 3 or any(not isinstance(item, dict) or set(item) != {"Text", "Url"} or not isinstance(item["Text"], str) or not item["Text"].strip() for item in value):
                raise ValueError("invalid AdditionalResources")
            urls = [item["Url"] for item in value]
        if any(not isinstance(url, str) or not re.fullmatch(r"https://[^\s?#]+", url) for url in urls):
            raise ValueError(f"{field} requires unsigned HTTPS URLs")
    def text_values(value):
        if isinstance(value, str):
            yield value
        elif isinstance(value, list):
            for item in value:
                yield from text_values(item)
        elif isinstance(value, dict):
            for item in value.values():
                yield from text_values(item)

    strings = list(text_values(content))
    if any(re.search(r"[\x00-\x08\x0b-\x1f]", value) for value in strings):
        raise ValueError("content contains unsupported control characters")
    if any(re.search(r"\{[A-Za-z][A-Za-z0-9_]*\}", value) for value in strings):
        raise ValueError("content contains unresolved template placeholders")


def plan(bundle: dict, entity: dict) -> dict:
    identifier = entity.get("EntityIdentifier", "")
    if not bundle["entityId"] or identifier.split("@")[0] != bundle["entityId"] or "@" not in identifier:
        raise ValueError("snapshot EntityIdentifier does not match the master Catalog EntityId/revision")
    current = current_content(entity)
    changes = {key: value for key, value in bundle["content"].items() if current.get(key) != value}
    request = build_update_request(bundle, identifier, changes)
    result = {"schemaVersion": 1, "key": bundle["key"], "sourceHash": bundle["sourceHash"], "baseRevision": identifier, "currentHash": digest(current), "publishBlockers": bundle["publishBlockers"], "diff": {key: {"before": current.get(key), "after": value} for key, value in changes.items()}, "request": request}
    result["planHash"] = digest(result)
    return result
