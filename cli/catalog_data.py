"""Build the runtime product from the temporary Contentful catalog and AWS rules."""

from __future__ import annotations

import re
import urllib.error
from typing import Any

from .marketplace import load_json

def load_catalog(source: str, timeout: float = 30) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    try:
        data = load_json(source, timeout)
    except (OSError, ValueError, urllib.error.URLError) as error:
        raise ValueError(f"failed to read catalog: {error}") from None
    items = data.get("items") if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise ValueError("catalog must be a JSON array or an object with items")
    by_id: dict[str, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise ValueError("catalog item has no string id")
        by_id[item["id"]] = item
    return (data if isinstance(data, dict) else {"items": items}), by_id


def load_versions(source: str, timeout: float = 30) -> dict[str, str]:
    try:
        data = load_json(source, timeout)
    except (OSError, ValueError, urllib.error.URLError) as error:
        raise ValueError(f"failed to read versions: {error}") from None
    if not isinstance(data, list):
        raise ValueError("versions source must be a JSON array")
    result: dict[str, str] = {}
    for item in data:
        if isinstance(item, dict) and isinstance(item.get("id"), str) and item.get("version"):
            result[item["id"]] = str(item["version"])
    return result


def build_runtime_product(
    *,
    key: str,
    item: dict[str, Any],
    version: str = "",
) -> dict[str, Any]:
    name = item.get("trademark")
    summary = item.get("summary")
    if not isinstance(name, str) or not name.strip() or not isinstance(summary, str) or not summary.strip():
        raise ValueError(f"catalog item {key!r} needs trademark and summary")
    components = item.get("includedComponents")
    if not isinstance(components, list) or not all(isinstance(item, str) and item.strip() for item in components):
        components = [name, "Websoft9 Console"]
    use_cases = item.get("usecases")
    if not isinstance(use_cases, list) or not all(isinstance(item, str) and item.strip() for item in use_cases):
        use_cases = []
    keywords = item.get("keywords")
    if not isinstance(keywords, list) or not all(isinstance(item, str) and item.strip() for item in keywords):
        keywords = []
    application = {
        "name": name,
        "summary": summary,
        "overview": item.get("overview") if isinstance(item.get("overview"), str) else "",
        "includedComponents": components,
        "useCases": use_cases,
        "searchKeywords": keywords,
        "version": version,
        "versions": [version] if version else [],
    }
    listing = {
        "entityType": item.get("entityType") or "AmiProduct@1.0",
        "entityId": item.get("entityId"),
        "templateId": item.get("templateId") or "aws-ami-v1",
        "locale": item.get("locale") or "en-US",
        "contentOverrides": item.get("contentOverrides") or {},
        "categories": item.get("categories") or [],
        "additionalResources": item.get("additionalResources") or [],
        "logoUrl": item.get("logoUrl"),
        "videoUrls": item.get("videoUrls") or [],
    }
    return {"schemaVersion": 1, "key": key, "application": application, "listings": {"aws": listing}}


def load_runtime_product(
    *,
    key: str,
    catalog_source: str,
    versions_source: str,
    timeout: float = 30,
) -> dict[str, Any]:
    _, by_id = load_catalog(catalog_source, timeout)
    item = by_id.get(key)
    if item is None:
        raise ValueError(f"application {key!r} is not in the catalog")
    versions = load_versions(versions_source, timeout)
    return build_runtime_product(
        key=key,
        item=item,
        version=versions.get(key, ""),
    )
