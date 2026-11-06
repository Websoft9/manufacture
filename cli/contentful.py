"""Pull English application records from Contentful and combine them by app id."""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Callable

from .marketplace import load_json

DEFAULT_API_URL = "https://cdn.contentful.com"
DEFAULT_FIELDS = ("trademark", "overview", "keywords", "usecases", "summary")
USER_AGENT = "Websoft9-manufacture/1.0"
Progress = Callable[[str], None]


class ContentfulError(RuntimeError):
    """An actionable Contentful or target-catalog failure."""


def _print(progress: Progress | None, message: str) -> None:
    if progress:
        progress(message)


def _field_matcher(fields: dict[str, Any], wanted: str) -> str | None:
    """Match Contentful field IDs such as useCases when the caller asks for usecases."""
    if wanted in fields:
        return wanted
    aliases = {
        "usecases": ("usecases", "useCases", "use_cases"),
        "tags": ("tags", "tag"),
    }
    candidates = aliases.get(wanted, (wanted,))
    normalized = {re.sub(r"[^a-z0-9]", "", key.lower()): key for key in sorted(fields)}
    for candidate in candidates:
        key = normalized.get(re.sub(r"[^a-z0-9]", "", candidate.lower()))
        if key is not None:
            return key
    return None


def _rich_text(value: Any) -> str:
    """Convert the common Contentful RichText shape to readable plain text."""
    if not isinstance(value, dict) or value.get("nodeType") != "document":
        return ""
    parts: list[str] = []

    def walk(node: Any) -> None:
        if not isinstance(node, dict):
            return
        if node.get("nodeType") == "text":
            parts.append(str(node.get("value", "")))
            return
        for child in node.get("content") or []:
            walk(child)
        if node.get("nodeType") in {"paragraph", "heading-1", "heading-2", "heading-3", "list-item", "quote"}:
            parts.append("\n")

    walk(value)
    text = "".join(parts)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _asset_url(asset: dict[str, Any]) -> str | None:
    file = (asset.get("fields") or {}).get("file") or {}
    url = file.get("url") if isinstance(file, dict) else None
    if not isinstance(url, str) or not url:
        return None
    return url if url.startswith("https://") else f"https:{url}"


def _entry_label(entry: dict[str, Any]) -> Any:
    fields = entry.get("fields") or {}
    if not isinstance(fields, dict):
        return entry.get("sys", {}).get("id")
    for key in ("name", "title", "label", "value", "text", "key"):
        if key in fields:
            return fields[key]
    return fields


def _resolve(value: Any, includes: dict[tuple[str, str], dict[str, Any]], raw: bool) -> Any:
    if raw:
        return value
    if isinstance(value, list):
        return [_resolve(item, includes, raw) for item in value]
    if not isinstance(value, dict):
        return value
    if value.get("nodeType") == "document":
        return _rich_text(value)
    sys = value.get("sys")
    if isinstance(sys, dict) and sys.get("type") == "Link":
        linked = includes.get((str(sys.get("linkType")), str(sys.get("id"))))
        if linked is None:
            return value
        if sys.get("linkType") == "Asset":
            return _asset_url(linked) or linked.get("sys", {}).get("id")
        return _entry_label(linked)
    return {key: _resolve(item, includes, raw) for key, item in value.items()}


def _includes(payload: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for group, link_type in (("Entry", "Entry"), ("Asset", "Asset")):
        for item in payload.get("includes", {}).get(group, []) or []:
            sys = item.get("sys") or {}
            if sys.get("id"):
                result[(link_type, str(sys["id"]))] = item
    return result


def _error_message(error: urllib.error.HTTPError) -> str:
    if error.code in {401, 403}:
        return f"Contentful authentication/permission failed (HTTP {error.code}). Check the token, space and environment."
    if error.code == 404:
        return "Contentful resource not found (HTTP 404). Check the space, environment, content type and locale."
    message = ""
    try:
        detail = json.loads(error.read(2000).decode("utf-8", errors="replace"))
        message = str(detail.get("message") or "").strip()
    except (AttributeError, OSError, ValueError, UnicodeError):
        message = ""
    suffix = f" {message}" if message else ""
    return f"Contentful request failed (HTTP {error.code}).{suffix}".strip()


def _get_json(url: str, token: str, timeout: float) -> dict[str, Any]:
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
        "User-Agent": USER_AGENT,
        "X-Contentful-User-Agent": "app websoft9-manufacture/1.0",
    }
    for attempt in range(3):
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code in {429, 500, 502, 503, 504} and attempt < 2:
                retry_after = error.headers.get("Retry-After") if error.headers else None
                try:
                    delay = min(float(retry_after), 10) if retry_after else 2**attempt
                except ValueError:
                    delay = 2**attempt
                time.sleep(delay)
                continue
            raise ContentfulError(_error_message(error)) from None
        except urllib.error.URLError as error:
            raise ContentfulError(f"Contentful request failed: {error.reason}") from None
        except (TimeoutError, OSError) as error:
            raise ContentfulError(f"Contentful request failed: {error}") from None
        except (ValueError, UnicodeError):
            raise ContentfulError("Contentful returned an invalid JSON response.") from None
    raise ContentfulError("Contentful request failed after retries.")


def _base_url(api_url: str, space_id: str, environment: str) -> str:
    return (f"{api_url.rstrip('/')}/spaces/{urllib.parse.quote(space_id, safe='')}"
            f"/environments/{urllib.parse.quote(environment, safe='')}")


def fetch_field_types(
    *,
    token: str,
    space_id: str,
    environment: str,
    content_type: str,
    api_url: str = DEFAULT_API_URL,
    timeout: float = 30,
) -> dict[str, str]:
    """Fetch field ids and types from the content-type schema."""
    url = f"{_base_url(api_url, space_id, environment)}/content_types/{urllib.parse.quote(content_type, safe='')}"
    payload = _get_json(url, token, timeout)
    fields = payload.get("fields") or []
    if not isinstance(fields, list):
        raise ContentfulError("Contentful content-type schema is malformed.")
    return {str(field["id"]): str(field.get("type", "")) for field in fields if isinstance(field, dict) and field.get("id")}


def fetch_entries(
    *,
    token: str,
    space_id: str,
    environment: str,
    content_type: str,
    locale: str,
    keys: tuple[str, ...] | None = None,
    api_url: str = DEFAULT_API_URL,
    page_size: int = 100,
    include_depth: int = 1,
    timeout: float = 30,
    progress: Progress | None = None,
) -> list[dict[str, Any]]:
    """Fetch entries, optionally filtering by application key, with pagination."""
    if not 1 <= page_size <= 1000:
        raise ContentfulError("page size must be between 1 and 1000.")
    entries: list[dict[str, Any]] = []
    skip = 0
    total: int | None = None
    base = f"{_base_url(api_url, space_id, environment)}/entries"
    while True:
        params = {
            "content_type": content_type,
            "locale": locale,
            "limit": page_size,
            "skip": skip,
            "select": "sys.id,fields",
            "include": include_depth,
        }
        if keys:
            if len(keys) == 1:
                params["fields.key"] = keys[0]
            else:
                params["fields.key[in]"] = ",".join(keys)
        payload = _get_json(f"{base}?{urllib.parse.urlencode(params)}", token, timeout)
        page = payload.get("items") or []
        if total is None:
            total = int(payload.get("total") or len(page))
            _print(progress, f"Contentful entries reported: {total}")
        includes = _includes(payload)
        for item in page:
            entries.append({"item": item, "includes": includes})
        skip += len(page)
        _print(progress, f"Fetched {min(skip, total)}/{total} Contentful entries")
        if not page:
            if skip < total:
                raise ContentfulError("Contentful returned an empty page before the reported total.")
            return entries
        if skip >= total:
            return entries
        if skip > total + page_size:
            raise ContentfulError("Contentful pagination did not converge.")


def load_target_keys(source: str, timeout: float, progress: Progress | None = None) -> list[str]:
    """Read product_en.json and return unique application ids in catalog order."""
    _print(progress, f"Reading target applications: {source}")
    try:
        catalog = load_json(source, timeout)
    except (OSError, ValueError, urllib.error.URLError) as error:
        raise ContentfulError(f"failed to read target catalog: {error}") from None
    if not isinstance(catalog, list):
        raise ContentfulError("target catalog must be a JSON array.")
    keys: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(catalog):
        key = item.get("key") if isinstance(item, dict) else None
        if not isinstance(key, str) or not key.strip():
            raise ContentfulError(f"target catalog item {index} has no string key.")
        key = key.strip()
        if key in seen:
            raise ContentfulError(f"duplicate application key in target catalog: {key}")
        seen.add(key)
        keys.append(key)
    if not keys:
        raise ContentfulError("target catalog contains no applications.")
    _print(progress, f"Target applications: {len(keys)}")
    return keys


def select_target_keys(catalog_keys: list[str], apps: tuple[str, ...] | None) -> list[str]:
    """Filter the target catalog to requested application ids, preserving request order."""
    if not apps:
        return catalog_keys
    requested: list[str] = []
    for app in apps:
        app = app.strip()
        if app and app not in requested:
            requested.append(app)
    if not requested:
        raise ContentfulError("--apps must contain at least one application id.")
    available = set(catalog_keys)
    unknown = [app for app in requested if app not in available]
    if unknown:
        preview = ", ".join(unknown[:20]) + (" ..." if len(unknown) > 20 else "")
        raise ContentfulError(f"Applications are not in the target catalog: {preview}")
    return requested


def build_dataset(
    *,
    entries: list[dict[str, Any]],
    target_keys: list[str],
    fields: tuple[str, ...] = DEFAULT_FIELDS,
    id_field: str = "key",
    field_types: dict[str, str] | None = None,
    raw: bool = False,
    allow_missing: bool = False,
    progress: Progress | None = None,
) -> dict[str, Any]:
    """Combine Contentful entries with the target app ids in catalog order."""
    unknown_fields = [name for name in fields if field_types is not None and _field_matcher(field_types, name) is None]
    if unknown_fields:
        raise ContentfulError(
            f"Contentful content type has no requested field(s): {', '.join(unknown_fields)}. "
            f"Available: {', '.join(sorted(field_types or {}))}"
        )
    by_id: dict[str, dict[str, Any]] = {}
    for container in entries:
        item = container["item"]
        item_fields = item.get("fields") or {}
        if not isinstance(item_fields, dict):
            raise ContentfulError(f"Contentful entry {item.get('sys', {}).get('id', '?')} has no fields object.")
        matched = _field_matcher(item_fields, id_field)
        if matched is None:
            raise ContentfulError(f"Contentful entries have no {id_field!r} field for the application id.")
        item_id = item_fields.get(matched)
        if not isinstance(item_id, str) or not item_id.strip():
            raise ContentfulError(f"Contentful entry {item.get('sys', {}).get('id', '?')} has no application id.")
        item_id = item_id.strip()
        if item_id in by_id:
            raise ContentfulError(f"duplicate Contentful application id: {item_id}")
        by_id[item_id] = container

    items: list[dict[str, Any]] = []
    missing: list[str] = []
    missing_fields: list[str] = []
    for key in target_keys:
        container = by_id.get(key)
        if container is None:
            missing.append(key)
            continue
        item = container["item"]
        item_fields = item.get("fields") or {}
        record: dict[str, Any] = {"id": key}
        absent: list[str] = []
        for wanted in fields:
            matched = _field_matcher(item_fields, wanted)
            if matched is None:
                absent.append(wanted)
                schema_field = _field_matcher(field_types or {}, wanted)
                record[wanted] = [] if schema_field and (field_types or {}).get(schema_field) == "Array" else None
                continue
            record[wanted] = _resolve(item_fields[matched], container["includes"], raw)
        if absent:
            missing_fields.append(f"{key}: {', '.join(absent)}")
        items.append(record)
    if missing and not allow_missing:
        preview = ", ".join(missing[:20]) + (" ..." if len(missing) > 20 else "")
        raise ContentfulError(f"{len(missing)} target application(s) are absent from Contentful: {preview}")
    if missing_fields:
        _print(progress, f"Empty field values for {len(missing_fields)} application-field pair(s); arrays use [] and other fields use null.")
    _print(progress, f"Matched {len(items)}/{len(target_keys)} target applications")
    result: dict[str, Any] = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "count": len(items),
        "items": items,
    }
    if missing:
        result["missing"] = missing
    return result


MANAGEMENT_API_URL = "https://api.contentful.com"


def _is_locale_map(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and bool(value)
        and all(isinstance(key, str) and re.fullmatch(r"[a-z]{2,3}(?:[-_][A-Za-z0-9]+)*", key) for key in value)
    )


def _management_fields(fields: dict[str, Any], schema: dict[str, dict[str, Any]], locale: str) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for field, value in fields.items():
        if not _is_locale_map(value):
            normalized[field] = value
            continue
        meta = schema.get(field) or {}
        if meta.get("localized"):
            picked = value.get(locale)
        else:
            picked = value.get(locale)
            if picked is None:
                picked = next(iter(value.values()), None)
        if picked is not None:
            normalized[field] = picked
    return normalized


def pull_dataset(
    *,
    token: str,
    space_id: str,
    environment: str,
    content_type: str,
    locale: str,
    catalog_source: str,
    app_ids: tuple[str, ...] | None = None,
    fields: tuple[str, ...] = DEFAULT_FIELDS,
    id_field: str = "key",
    api_url: str = DEFAULT_API_URL,
    page_size: int = 100,
    include_depth: int = 1,
    timeout: float = 30,
    raw: bool = False,
    allow_missing: bool = False,
    progress: Progress | None = None,
) -> dict[str, Any]:
    if not token or not token.strip():
        raise ContentfulError("a Contentful token is required.")
    if not space_id or not space_id.strip():
        raise ContentfulError("a Contentful space id is required.")
    if not fields:
        raise ContentfulError("at least one Contentful field is required.")
    target_keys = load_target_keys(catalog_source, timeout, progress)
    if app_ids:
        target_keys = select_target_keys(target_keys, app_ids)
        _print(progress, f"Selected applications: {len(target_keys)}")
    if token.strip().startswith("CFPAT-"):
        # A CFPAT token is a Management token and is not accepted by the CDA.
        # Read through the Management API so one token can serve both commands.
        from . import contentful_management

        management_api = api_url if re.match(r"https://api(?:\.eu)?\.contentful\.com", api_url) else MANAGEMENT_API_URL
        _print(progress, "Using Contentful Management API for CFPAT token")
        schema = contentful_management.fetch_schema(
            token=token.strip(),
            space_id=space_id.strip(),
            environment=environment.strip(),
            content_type=content_type.strip(),
            api_url=management_api,
            timeout=timeout,
        )
        management_entries = contentful_management.fetch_entries(
            token=token.strip(),
            space_id=space_id.strip(),
            environment=environment.strip(),
            content_type=content_type.strip(),
            keys=tuple(target_keys),
            api_url=management_api,
            page_size=min(page_size, 1000),
            timeout=timeout,
            progress=progress,
        )
        entries = [
            {
                "item": {**entry, "fields": _management_fields(entry.get("fields") or {}, schema, locale.strip())},
                "includes": {},
            }
            for entry in management_entries
        ]
        field_types = {field: str(meta.get("type", "")) for field, meta in schema.items()}
        api_used = management_api
    else:
        _print(progress, "Reading Contentful content-type schema")
        field_types = fetch_field_types(
            token=token.strip(),
            space_id=space_id.strip(),
            environment=environment.strip(),
            content_type=content_type.strip(),
            api_url=api_url,
            timeout=timeout,
        )
        entries = fetch_entries(
            token=token.strip(),
            space_id=space_id.strip(),
            environment=environment.strip(),
            content_type=content_type.strip(),
            locale=locale.strip(),
            keys=tuple(target_keys),
            api_url=api_url,
            page_size=page_size,
            include_depth=include_depth,
            timeout=timeout,
            progress=progress,
        )
        api_used = api_url
    result = build_dataset(
        entries=entries,
        target_keys=target_keys,
        fields=fields,
        id_field=id_field,
        field_types=field_types,
        raw=raw,
        allow_missing=allow_missing,
        progress=progress,
    )
    result["source"] = {
        "catalog": catalog_source,
        "contentful": {
            "api": api_used.rstrip("/"),
            "spaceId": space_id.strip(),
            "environment": environment.strip(),
            "contentType": content_type.strip(),
            "locale": locale.strip(),
        },
    }
    return result


def _is_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def dumps_dataset(value: Any, level: int = 0) -> str:
    """Pretty JSON that keeps scalar arrays such as keywords on one line."""
    pad = "  " * level
    child = "  " * (level + 1)
    if isinstance(value, dict):
        if not value:
            return "{}"
        lines = ["{"]
        items = list(value.items())
        for index, (key, item) in enumerate(items):
            comma = "," if index < len(items) - 1 else ""
            lines.append(f"{child}{json.dumps(key, ensure_ascii=False)}: {dumps_dataset(item, level + 1)}{comma}")
        lines.append(pad + "}")
        return "\n".join(lines)
    if isinstance(value, list):
        if not value:
            return "[]"
        if all(_is_scalar(item) for item in value):
            return "[" + ", ".join(json.dumps(item, ensure_ascii=False) for item in value) + "]"
        lines = ["["]
        for index, item in enumerate(value):
            comma = "," if index < len(value) - 1 else ""
            lines.append(f"{child}{dumps_dataset(item, level + 1)}{comma}")
        lines.append(pad + "]")
        return "\n".join(lines)
    return json.dumps(value, ensure_ascii=False)
