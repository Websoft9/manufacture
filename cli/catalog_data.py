"""Load application facts and versions from the temporary Contentful catalog."""

from __future__ import annotations

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


def load_versions(source: str, timeout: float = 30) -> dict[str, list[str]]:
    """Load versions per application id.

    An entry may use `version` or `versions`; each may be a single string or a
    list of strings. This keeps the existing single-version shape working while
    allowing multi-version applications.
    """
    try:
        data = load_json(source, timeout)
    except (OSError, ValueError, urllib.error.URLError) as error:
        raise ValueError(f"failed to read versions: {error}") from None
    if not isinstance(data, list):
        raise ValueError("versions source must be a JSON array")
    result: dict[str, list[str]] = {}
    for item in data:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            continue
        raw = item.get("versions", item.get("version"))
        if isinstance(raw, (str, int, float)):
            values = [str(raw)]
        elif isinstance(raw, list):
            values = [str(value) for value in raw if isinstance(value, (str, int, float))]
        else:
            continue
        options = result.setdefault(item["id"], [])
        for value in values:
            value = value.strip()
            if value and value not in options:
                options.append(value)
    return result


def load_application(
    *,
    key: str,
    catalog_source: str,
    versions_source: str,
    timeout: float = 30,
) -> tuple[dict[str, Any], str, list[str]]:
    _, by_id = load_catalog(catalog_source, timeout)
    item = by_id.get(key)
    if item is None:
        raise ValueError(f"application {key!r} is not in the catalog")
    versions = load_versions(versions_source, timeout)
    options = versions.get(key, [])
    return item, options[0] if options else "", options
