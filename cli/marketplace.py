"""Marketplace product catalog and application mapping."""

from __future__ import annotations

import json
import os
import re
import urllib.request
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def find_config() -> Path:
    configured = os.environ.get("MK_CONFIG_PATH")
    if configured:
        return Path(configured)

    starts = (Path.cwd(), Path(__file__).resolve().parents[1])
    for start in starts:
        for directory in (start, *start.parents):
            candidate = directory / "config" / "marketplace.json"
            if candidate.is_file():
                return candidate
    raise FileNotFoundError("Unable to locate config/marketplace.json")


CONFIG_PATH = find_config()
CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
REPO_ROOT = CONFIG_PATH.parents[1]


def catalog_default_path() -> Path:
    """Default staging dataset for catalog pull/push."""
    configured = os.environ.get("MK_CATALOG_DIR")
    directory = Path(configured) if configured else REPO_ROOT / "data" / ".catalog"
    return directory / "catalog.json"

APP_CONFIG_PATH = CONFIG_PATH.parent / "app.json"
APP_CONFIG = (
    json.loads(APP_CONFIG_PATH.read_text(encoding="utf-8"))
    if APP_CONFIG_PATH.is_file()
    else {}
)
MULTI_VERSION_APPS = frozenset(str(item) for item in APP_CONFIG.get("multi_version_apps", []))

SOURCES = CONFIG["sources"]
APP_SOURCES = APP_CONFIG["sources"]
OFFER_URL = os.environ.get("MK_OFFER_URL", SOURCES["offer"])
CATALOG_URL = os.environ.get("MK_CATALOG_URL", APP_SOURCES["catalog"])
VERSIONS_URL = os.environ.get("MK_VERSIONS_URL", APP_SOURCES["versions"])

ALL_PLATFORM_CONFIGS = tuple(CONFIG["platforms"])
CONFIGURED_PLATFORMS = tuple(str(item["key"]) for item in ALL_PLATFORM_CONFIGS)
PLATFORM_CONFIGS = tuple(
    item for item in ALL_PLATFORM_CONFIGS if item.get("urlTemplate")
)
PLATFORMS = tuple(str(item["key"]) for item in PLATFORM_CONFIGS)
PLATFORM_TITLES = {
    str(item["key"]): str(item["label"]) for item in PLATFORM_CONFIGS
}
PLATFORM_URL_TEMPLATES = {
    str(item["key"]): str(item["urlTemplate"])
    for item in PLATFORM_CONFIGS
    if item.get("urlTemplate")
}
ROUTING = CONFIG["routing"]

START_MARKER = "<!-- marketplace-apps:start -->"
END_MARKER = "<!-- marketplace-apps:end -->"


@dataclass
class AppRow:
    key: str
    name: str
    links: dict[str, list[tuple[str, str]]] = field(default_factory=dict)
    in_catalog: bool = True

    @property
    def has_links(self) -> bool:
        return any(self.links.values())


def load_json(source: str, timeout: float = 30) -> Any:
    if re.match(r"^https?://", source):
        request = urllib.request.Request(
            source,
            headers={
                "Accept": "application/json",
                "User-Agent": "Websoft9-manufacture/1.0",
            },
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    with open(source, encoding="utf-8") as file:
        return json.load(file)


def offer_codes_by_app(source: str, timeout: float = 30) -> dict[str, dict[str, list[str]]]:
    """Map application ids to marketplace offer codes by platform."""
    data = load_json(source, timeout)
    offers = data if isinstance(data, list) else data.get("items")
    if not isinstance(offers, list):
        raise ValueError("offer source must be a JSON array or an object with items")
    result: dict[str, dict[str, list[str]]] = {}
    for offer in offers:
        if not isinstance(offer, dict) or offer.get("type") != "app":
            continue
        apps: list[str] = []
        if isinstance(offer.get("id"), str) and offer["id"].strip():
            apps.append(offer["id"].strip())
        for app in offer.get("applications") or []:
            if isinstance(app, str) and app.strip() and app.strip() not in apps:
                apps.append(app.strip())
        product_ids = offer.get("productID") or {}
        if not apps or not isinstance(product_ids, dict):
            continue
        for app in apps:
            by_platform = result.setdefault(app, {})
            for platform, codes in product_ids.items():
                if not isinstance(codes, list):
                    continue
                values = by_platform.setdefault(str(platform), [])
                for code in codes:
                    if isinstance(code, str) and code.strip() and code.strip() not in values:
                        values.append(code.strip())
    return result


def route_platform(source_key: str, code: str) -> str | None:
    route = ROUTING.get(source_key.lower())
    if not route:
        return None

    platform = str(route["default"])
    for rule in route.get("rules", []):
        prefix = str(rule.get("prefix", ""))
        if prefix and code.lower().startswith(prefix.lower()):
            platform = str(rule["platform"])
            break
    return platform


def product_url(platform_key: str, code: str) -> tuple[str, str] | None:
    platform = route_platform(platform_key, code)
    if platform is None:
        return None

    template = PLATFORM_URL_TEMPLATES.get(platform)
    if template is None:
        return None
    return platform, template.replace("{code}", code)


def collect_rows(offers: list[dict[str, Any]], catalog: list[dict[str, Any]]) -> list[AppRow]:
    catalog_by_key = {
        str(item["key"]): item for item in catalog if item.get("key") is not None
    }
    offer_links: OrderedDict[str, dict[str, list[tuple[str, str]]]] = OrderedDict()

    for offer in offers:
        if offer.get("type") != "app":
            continue
        key = offer.get("id")
        if not key:
            applications = offer.get("applications") or []
            key = applications[0] if applications else None
        if not key:
            continue
        key = str(key)
        merged = offer_links.setdefault(key, {})
        for platform_key, codes in (offer.get("productID") or {}).items():
            if not isinstance(codes, list):
                continue
            for code in codes:
                if not code:
                    continue
                result = product_url(str(platform_key), str(code))
                if result is None:
                    continue
                platform, url = result
                entries = merged.setdefault(platform, [])
                entry = (str(code), url)
                if entry not in entries:
                    entries.append(entry)

    def sort_key(key: str) -> tuple[str, str]:
        catalog_item = catalog_by_key.get(key, {})
        name = catalog_item.get("trademark") or key
        return str(name).casefold(), key

    rows = []
    for key in sorted(set(catalog_by_key) | set(offer_links), key=sort_key):
        catalog_item = catalog_by_key.get(key, {})
        rows.append(
            AppRow(
                key=key,
                name=str(catalog_item.get("trademark") or key),
                links=offer_links.get(key, {}),
                in_catalog=key in catalog_by_key,
            )
        )
    return rows


def escape_cell(value: str) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def format_links(entries: list[tuple[str, str]]) -> str:
    return "<br>".join(f"[{escape_cell(code)}]({url})" for code, url in entries)


def render_table(rows: list[AppRow]) -> str:
    lines = [
        "| 应用 | " + " | ".join(PLATFORM_TITLES[platform] for platform in PLATFORMS) + " |",
        "| --- | " + " | ".join("---" for _ in PLATFORMS) + " |",
    ]
    for row in rows:
        cells = [escape_cell(row.name)]
        cells.extend(format_links(row.links.get(platform, [])) for platform in PLATFORMS)
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def render_markdown(rows: list[AppRow]) -> str:
    listed_catalog = [row for row in rows if row.in_catalog and row.has_links]
    unlisted = [row for row in rows if row.in_catalog and not row.has_links]
    outside_catalog = [row for row in rows if not row.in_catalog and row.has_links]

    parts = [
        START_MARKER,
        "## Marketplace 应用对应表",
        "",
        "下表列出 `product_en.json` 中的应用及其在各 Marketplace 的商品链接。"
        f"数据源：[offer.json]({OFFER_URL})、[product_en.json]({CATALOG_URL})；"
        "运行 `mk list --update-readme README.md` 重新生成。",
        "",
        f"已上架应用：{len(listed_catalog)} 个；未上架应用：{len(unlisted)} 个。",
        "",
        render_table(listed_catalog),
    ]

    if unlisted:
        parts.extend(
            [
                "",
                "### 未在 Marketplace 找到商品的应用",
                "",
                *[f"- {escape_cell(row.name)}" for row in unlisted],
            ]
        )

    if outside_catalog:
        parts.extend(
            [
                "",
                "### Marketplace 商品目录之外的应用",
                "",
                "以下应用在 `offer.json` 中存在商品，但 `product_en.json` 中没有对应的 Trademark。",
                "",
                render_table(outside_catalog),
            ]
        )

    parts.append(END_MARKER)
    return "\n".join(parts)


def update_readme(path: Path, section: str) -> bool:
    text = path.read_text(encoding="utf-8")
    if START_MARKER in text and END_MARKER in text:
        before, remainder = text.split(START_MARKER, 1)
        _, after = remainder.split(END_MARKER, 1)
        new_text = before + section + after
    else:
        new_text = text.rstrip() + "\n\n" + section + "\n"
    changed = new_text != text
    if changed:
        path.write_text(new_text, encoding="utf-8")
    return changed
