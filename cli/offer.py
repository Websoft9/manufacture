"""Deterministic AWS listing rendering, validation and change planning."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .aws_marketplace import (
    CONTENT_FIELDS as FIELDS,
    FIELD_LIMITS as LIMITS,
    aws_call,
    aws_client,
    build_update_request,
    change_status,
    current_content,
)
from .marketplace import MULTI_VERSION_APPS

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "offer"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


PLACEHOLDER = re.compile(r"\{([^{}]+)\}")


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


def _find_outside(text: str, target: str) -> int:
    quote = None
    escaped = False
    for index, character in enumerate(text):
        if escaped:
            escaped = False
            continue
        if character == "\\":
            escaped = True
            continue
        if quote:
            if character == quote:
                quote = None
            continue
        if character in "'\"":
            quote = character
        elif character == target:
            return index
    return -1


def _split_outside(text: str, separator: str) -> list[str]:
    parts: list[str] = []
    start = 0
    while True:
        index = _find_outside(text[start:], separator)
        if index == -1:
            parts.append(text[start:])
            return parts
        index += start
        parts.append(text[start:index])
        start = index + len(separator)


def _unquote(text: str) -> str:
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "'\"":
        return text[1:-1]
    return text


def _evaluate_operand(text: str, roots: dict[str, Any]) -> Any:
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "'\"":
        return _unquote(text)
    return evaluate_expression(text, roots)


def evaluate_expression(expression: str, roots: dict[str, Any]) -> Any:
    expression = expression.strip()
    question = _find_outside(expression, "?")
    if question != -1:
        condition = expression[:question].strip()
        remainder = expression[question + 1:]
        colon = _find_outside(remainder, ":")
        if colon == -1:
            raise ValueError(f"invalid conditional template expression: {expression}")
        return (
            _evaluate_operand(remainder[:colon], roots)
            if evaluate_expression(condition, roots)
            else _evaluate_operand(remainder[colon + 1:], roots)
        )
    parts = _split_outside(expression, "|")
    value = resolve_placeholder(parts[0].strip(), roots)
    for filter_expression in parts[1:]:
        name, _, argument = filter_expression.partition(":")
        if name.strip() != "join":
            raise ValueError(f"unsupported template filter: {name.strip()}")
        if not isinstance(value, list):
            raise ValueError("join filter requires an array value")
        arguments = [_unquote(item.strip()) for item in _split_outside(argument, ",")]
        separator = arguments[0] if arguments else ", "
        suffix = arguments[1] if len(arguments) > 1 else ""
        joined = separator.join(str(item) for item in value)
        value = joined + suffix if joined else joined
    return value


def format_template(text: str, roots: dict[str, Any]) -> Any:
    match = PLACEHOLDER.fullmatch(text.strip())
    if match:
        return evaluate_expression(match.group(1), roots)
    return PLACEHOLDER.sub(lambda item: str(evaluate_expression(item.group(1), roots)), text)


def display_version(value: str) -> str:
    """Keep at most two dotted components for listing display."""
    text = str(value).strip()
    parts = text.split(".")
    return ".".join(parts[:2]) if len(parts) > 2 else text


def version_choices(options: list[str]) -> str:
    values = [display_version(item) for item in options]
    if not values:
        return ""
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return f"{values[0]} or {values[1]}"
    return ", ".join(values[:-1]) + f", or {values[-1]}"


def render(catalog_item: dict, version: str, vendor_path: Path = DATA / "vendor.json", template_path: Path = DATA / "templates/aws-ami.json", version_options: list[str] | None = None) -> dict:
    vendor, template = read_json(vendor_path), read_json(template_path)
    options = [str(item).strip() for item in (version_options or [])]
    options = [display_version(item) for item in options if item and item.casefold() != "latest"]
    options = list(dict.fromkeys(options))
    multi_version = catalog_item.get("id") in MULTI_VERSION_APPS and len(options) >= 2
    selection = f" {'/'.join(options)} for selection" if multi_version else ""
    namespaces = template.get("namespaces")
    if not isinstance(namespaces, list) or not namespaces or any(not isinstance(namespace, str) or not namespace for namespace in namespaces):
        raise ValueError("template.namespaces must contain at least one namespace")
    template_id = catalog_item.get("templateId") or "aws-ami-v1"
    if template.get("templateId") != template_id or template.get("schemaVersion") != 1:
        raise ValueError("unsupported or mismatched template")
    entity_type = catalog_item.get("entityType") or "AmiProduct@1.0"
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
    catalog_values = dict(catalog_item)
    if not isinstance(catalog_values.get("hasenterprise"), bool):
        catalog_values["hasenterprise"] = True
    available = {
        "catalog": catalog_values,
        "versions": {
            "id": catalog_item.get("id"),
            "version": display_version(version) if version else "",
            "selection": selection,
            "multi": multi_version,
            "shortChoices": version_choices(options),
        },
        "vendor": vendor,
    }
    roots = {}
    for namespace in namespaces:
        if namespace not in available:
            raise ValueError(f"template namespace has no source: {namespace}")
        roots[namespace] = available[namespace]
    target = template.get("target") or {}
    if target:
        if target.get("platform") not in (None, "aws"):
            raise ValueError("template target.platform must be aws")
        if target.get("entityType") not in (None, entity_type):
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
    heading_format = "**{}**" if template.get("boldLongDescriptionHeadings") else "{}"
    content["LongDescription"] = "\n\n".join(
        (heading_format.format(section["heading"]) + "\n" if section["heading"] else "") + section["text"]
        for section in rendered_sections
    )
    preview_only_template = template.get("previewOnlySections") or []
    if not isinstance(preview_only_template, list):
        raise ValueError("template.previewOnlySections must be an array")
    preview_only_sections = []
    for section in preview_only_template:
        if not isinstance(section, dict) or set(section) != {"id", "heading", "text"}:
            raise ValueError("template.previewOnlySections items require id, heading and text")
        preview_only_sections.append(
            {
                "id": format_template(section["id"], roots),
                "heading": format_template(section["heading"], roots),
                "text": format_template(section["text"], roots),
            }
        )
    for field in ("Categories", "VideoUrls"):
        if not content.get(field):
            content.pop(field, None)
    if not content.get("LogoUrl"):
        content.pop("LogoUrl", None)
    resources = template.get("AdditionalResources", template.get("additionalResources")) or []
    if resources:
        content["AdditionalResources"] = [
            {key: format_template(str(value), roots) for key, value in item.items()} for item in resources
        ]
    content.update(catalog_item.get("contentOverrides") or {})
    # Absent optional fields preserve the current AWS value. Empty arrays never clear it implicitly.
    validate_content(content)
    blockers = []
    if not version:
        blockers.append("versions: version is missing")
    entity_id = catalog_item.get("entityId")
    if not entity_id:
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
        "previewOnlySections": preview_only_sections,
    }
    return {
        "schemaVersion": 1, "key": catalog_item["id"], "entityId": entity_id, "entityType": entity_type,
        "templateId": template["templateId"], "content": content, "preview": preview,
        "publishBlockers": blockers,
        "sourceHash": digest({"catalog": catalog_item, "version": version, "vendor": vendor, "template": template}),
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
