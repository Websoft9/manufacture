"""Deterministic AWS listing rendering, validation and change planning."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "offer"
LIMITS = {"ProductTitle": 72, "ShortDescription": 1000, "LongDescription": 5000, "SupportDescription": 2000}
FIELDS = set(LIMITS) | {"Highlights", "SearchKeywords", "Categories", "AdditionalResources", "LogoUrl", "VideoUrls"}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def render(product_path: Path, provider_path: Path = DATA / "provider.json", template_path: Path = DATA / "templates/aws-ami.json") -> dict:
    product = read_json(product_path)
    schema = read_json(DATA / "product.schema.json")
    errors = sorted(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(product), key=lambda error: str(error.path))
    if errors:
        raise ValueError("; ".join(f"{'.'.join(map(str, error.path))}: {error.message}" for error in errors))
    provider, template = read_json(provider_path), read_json(template_path)
    listing, app = product["listings"]["aws"], product["application"]
    if template.get("templateId") != listing["templateId"] or template.get("schemaVersion") != 1:
        raise ValueError("unsupported or mismatched template")
    provider_fields = ("aboutProvider", "consoleSummary", "supportSummary", "supportContact", "supportScope", "trademarkStatement")
    for field in provider_fields:
        if not isinstance(provider.get(field), str) or not provider[field].strip():
            raise ValueError(f"provider.{field} must be non-empty text")
    verification_schema = {"$ref": "#/$defs/verification", "$defs": schema["$defs"]}
    Draft202012Validator(verification_schema, format_checker=FormatChecker()).validate(provider.get("verification"))
    values = {**app, **{field: provider[field] for field in provider_fields}, **listing["deployment"], **listing["commercial"]}
    values["includedComponents"] = ", ".join(app["includedComponents"]) + "."
    values["useCases"] = "; ".join(app["useCases"]) + "."
    content = {key: [item.format_map(values) for item in value] if isinstance(value, list) else value.format_map(values) for key, value in template["content"].items()}
    content["LongDescription"] = "\n\n".join((section["heading"].format_map(values) + "\n" if section["heading"] else "") + section["text"].format_map(values) for section in template["longDescriptionSections"])
    content["SearchKeywords"] = app["searchKeywords"]
    content.update(listing["contentOverrides"])
    # Absent optional fields preserve the current AWS value. Empty arrays never clear it implicitly.
    for field, source in (("Categories", "categories"), ("AdditionalResources", "additionalResources"), ("LogoUrl", "logoUrl"), ("VideoUrls", "videoUrls")):
        if listing[source]:
            content[field] = listing[source]
    validate_content(content)
    checks = {"application": app["verification"], "provider": provider["verification"], "listing": listing["verification"], "deployment": listing["deployment"]["verification"], "commercial": listing["commercial"]["verification"]}
    blockers = [f"{key}: unverified" for key, value in checks.items() if value["status"] != "verified"]
    if not listing["entityId"]:
        blockers.append("listing: Catalog EntityId is missing")
    return {
        "schemaVersion": 1, "key": product["key"], "entityId": listing["entityId"], "entityType": listing["entityType"],
        "templateId": template["templateId"], "content": content,
        "deploymentPreview": {"usageInstructions": listing["deployment"]["usageInstructions"]},
        "commercialPreview": {"refundPolicy": listing["commercial"]["refundPolicy"]},
        "verification": checks, "publishBlockers": blockers,
        "sourceHash": digest({"product": product, "provider": provider, "template": template}),
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


def current_content(entity: dict) -> dict:
    if entity.get("EntityType") != "AmiProduct@1.0":
        raise ValueError("snapshot is not an AmiProduct@1.0 entity")
    detail = entity.get("DetailsDocument")
    if detail is None:
        detail = json.loads(entity["Details"])
    description = detail.get("Description", {})
    promotional = detail.get("PromotionalResources", {})
    result = {key: description[key] for key in FIELDS if key in description}
    for field in ("LogoUrl", "AdditionalResources"):
        if field in promotional:
            result[field] = promotional[field]
    if "AdditionalResources" in result:
        result["AdditionalResources"] = [{"Text": item["Text"], "Url": item["Url"]} for item in result["AdditionalResources"]]
    if "Videos" in promotional:
        result["VideoUrls"] = [item if isinstance(item, str) else item["Url"] for item in promotional["Videos"]]
    result["SupportDescription"] = detail.get("SupportInformation", {}).get("Description")
    return result


def plan(bundle: dict, entity: dict) -> dict:
    identifier = entity.get("EntityIdentifier", "")
    if not bundle["entityId"] or identifier.split("@")[0] != bundle["entityId"] or "@" not in identifier:
        raise ValueError("snapshot EntityIdentifier does not match the master Catalog EntityId/revision")
    current = current_content(entity)
    changes = {key: value for key, value in bundle["content"].items() if current.get(key) != value}
    request = {"Catalog": "AWSMarketplace", "ChangeSet": [{"ChangeType": "UpdateInformation", "Entity": {"Type": bundle["entityType"], "Identifier": identifier}, "DetailsDocument": changes}]} if changes else None
    result = {"schemaVersion": 1, "key": bundle["key"], "sourceHash": bundle["sourceHash"], "baseRevision": identifier, "currentHash": digest(current), "publishBlockers": bundle["publishBlockers"], "diff": {key: {"before": current.get(key), "after": value} for key, value in changes.items()}, "request": request}
    result["planHash"] = digest(result)
    return result


def aws_client(profile: str | None = None):
    try:
        import boto3
        from botocore.config import Config
    except ImportError as error:
        raise ValueError("install the AWS SDK with: pip install '.[aws]'") from error
    return boto3.Session(profile_name=profile).client("marketplace-catalog", region_name="us-east-1", config=Config(retries={"mode": "standard", "total_max_attempts": 4}))


def aws_call(client, operation: str, **kwargs) -> dict:
    """Expose error codes only; never log raw signed requests or sensitive SDK responses."""
    try:
        return getattr(client, operation)(Catalog="AWSMarketplace", **kwargs)
    except Exception as error:
        code = getattr(error, "response", {}).get("Error", {}).get("Code", type(error).__name__)
        raise ValueError(f"AWS {operation} failed ({code})") from None


def change_status(response: dict) -> dict:
    return {"changeSetId": response.get("ChangeSetId"), "status": response.get("Status"), "failureCode": response.get("FailureCode"), "errorCodes": [error.get("ErrorCode") for change in response.get("ChangeSet", []) for error in change.get("ErrorDetailList", [])]}
