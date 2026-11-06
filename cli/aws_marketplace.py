"""AWS Marketplace Catalog adapter.

This module owns the boundary between the authoring model and AWS:

- read shape: Description / PromotionalResources / SupportInformation
- update shape: flat UpdateInformationChangeDetail fields
- field names, limits, read paths and write targets are declared in FIELD_SPECS
"""

from __future__ import annotations

import json
from typing import Any

CATALOG = "AWSMarketplace"
ENTITY_TYPE = "AmiProduct@1.0"
CHANGE_TYPE = "UpdateInformation"

FIELD_SPECS: dict[str, dict[str, Any]] = {
    "ProductTitle": {
        "read": ("Description", "ProductTitle"),
        "write": "ProductTitle",
        "type": "string",
        "max": 72,
        "required": True,
    },
    "ShortDescription": {
        "read": ("Description", "ShortDescription"),
        "write": "ShortDescription",
        "type": "string",
        "max": 1000,
        "required": True,
    },
    "LongDescription": {
        "read": ("Description", "LongDescription"),
        "write": "LongDescription",
        "type": "string",
        "max": 5000,
        "required": True,
    },
    "Highlights": {
        "read": ("Description", "Highlights"),
        "write": "Highlights",
        "type": "stringList",
        "maxItems": 3,
        "itemMax": 500,
        "required": False,
    },
    "SearchKeywords": {
        "read": ("Description", "SearchKeywords"),
        "write": "SearchKeywords",
        "type": "stringList",
        "maxItems": 15,
        "itemMax": 50,
        "maxCombined": 250,
        "required": False,
    },
    "SupportDescription": {
        "read": ("SupportInformation", "Description"),
        "write": "SupportDescription",
        "type": "string",
        "max": 2000,
        "required": True,
    },
    "AdditionalResources": {
        "read": ("PromotionalResources", "AdditionalResources"),
        "write": "AdditionalResources",
        "type": "resourceList",
        "maxItems": 3,
        "required": False,
        "readTransform": "resources",
    },
    "Categories": {
        "read": ("Description", "Categories"),
        "write": "Categories",
        "type": "stringList",
        "maxItems": 3,
        "required": False,
        "template": False,
    },
    "LogoUrl": {
        "read": ("PromotionalResources", "LogoUrl"),
        "write": "LogoUrl",
        "type": "url",
        "required": False,
        "template": False,
    },
    "VideoUrls": {
        "read": ("PromotionalResources", "Videos"),
        "write": "VideoUrls",
        "type": "urlList",
        "maxItems": 1,
        "required": False,
        "template": False,
        "readTransform": "urls",
    },
}

FIELD_LIMITS = {
    name: spec["max"]
    for name, spec in FIELD_SPECS.items()
    if "max" in spec
}
CONTENT_FIELDS = set(FIELD_SPECS)


def normalize_additional_resources(items: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Read-side AdditionalResources include Type; update-side items are Text/Url only."""
    return [{"Text": item["Text"], "Url": item["Url"]} for item in items]


def _get_path(value: Any, path: tuple[str, ...]) -> Any:
    current = value
    for part in path:
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _set_path(value: dict[str, Any], path: tuple[str, ...], item: Any) -> None:
    current = value
    for part in path[:-1]:
        current = current.setdefault(part, {})
    current[path[-1]] = item


def _read_value(detail: dict[str, Any], field: str, spec: dict[str, Any]) -> Any:
    value = _get_path(detail, spec["read"])
    if value is None:
        return None
    transform = spec.get("readTransform")
    if transform == "resources" and isinstance(value, list):
        return normalize_additional_resources(value)
    if transform == "urls" and isinstance(value, list):
        return [item if isinstance(item, str) else item["Url"] for item in value]
    return value


def current_content(entity: dict[str, Any]) -> dict[str, Any]:
    """Normalize the nested AWS read shape to flat UpdateInformation field names."""
    if entity.get("EntityType") != ENTITY_TYPE:
        raise ValueError("snapshot is not an AmiProduct@1.0 entity")
    detail = entity.get("DetailsDocument")
    if detail is None:
        detail = json.loads(entity["Details"])
    result: dict[str, Any] = {}
    for field, spec in FIELD_SPECS.items():
        value = _read_value(detail, field, spec)
        if value is not None:
            result[field] = value
    return result


def to_update_document(content: dict[str, Any]) -> dict[str, Any]:
    """Return the flat UpdateInformation shape used by StartChangeSet."""
    result: dict[str, Any] = {}
    for field, value in content.items():
        spec = FIELD_SPECS.get(field)
        if spec is None:
            continue
        if field == "AdditionalResources":
            value = [{"Text": item["Text"], "Url": item["Url"]} for item in value]
        result[spec["write"]] = value
    return result


def to_read_document(content: dict[str, Any]) -> dict[str, Any]:
    """Return an AWS read-shaped desired document for review and offline diff."""
    result: dict[str, Any] = {}
    for field, value in content.items():
        spec = FIELD_SPECS.get(field)
        if spec is None or "read" not in spec:
            continue
        if field == "AdditionalResources":
            value = [{"Type": "Link", "Text": item["Text"], "Url": item["Url"]} for item in value]
        _set_path(result, spec["read"], value)
    return result


def build_update_request(bundle: dict[str, Any], identifier: str, changes: dict[str, Any]) -> dict[str, Any] | None:
    """Build the AWS UpdateInformation ChangeSet using the flat update shape."""
    if not changes:
        return None
    return {
        "Catalog": CATALOG,
        "ChangeSet": [{
            "ChangeType": CHANGE_TYPE,
            "Entity": {"Type": bundle["entityType"], "Identifier": identifier},
            "DetailsDocument": changes,
        }],
    }


def aws_client(profile: str | None = None):
    try:
        import boto3
        from botocore.config import Config
    except ImportError as error:
        raise ValueError("install the AWS SDK with: pip install '.[aws]'") from error
    return boto3.Session(profile_name=profile).client(
        "marketplace-catalog",
        region_name="us-east-1",
        config=Config(retries={"mode": "standard", "total_max_attempts": 4}),
    )


def aws_call(client, operation: str, **kwargs) -> dict[str, Any]:
    """Expose error codes only; never log raw signed requests or sensitive SDK responses."""
    try:
        return getattr(client, operation)(Catalog=CATALOG, **kwargs)
    except Exception as error:
        code = getattr(error, "response", {}).get("Error", {}).get("Code", type(error).__name__)
        raise ValueError(f"AWS {operation} failed ({code})") from None


def change_status(response: dict[str, Any]) -> dict[str, Any]:
    return {
        "changeSetId": response.get("ChangeSetId"),
        "status": response.get("Status"),
        "failureCode": response.get("FailureCode"),
        "errorCodes": [
            error.get("ErrorCode")
            for change in response.get("ChangeSet", [])
            for error in change.get("ErrorDetailList", [])
        ],
    }
