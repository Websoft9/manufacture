from __future__ import annotations

import re

VERSION_PATTERN = re.compile(
    r"(?<![\w])v?\d+(?:\.\d+){1,3}(?:[-+][0-9A-Za-z.-]+)?",
    re.IGNORECASE,
)

_MODIFIERS = {
    "alibaba",
    "aliyun",
    "cloud",
    "linux",
    "windows",
    "ubuntu",
    "centos",
    "debian",
    "rocky",
    "almalinux",
    "镜像",
    "阿里云",
}

_VERSION_CONTEXT_BLOCKER_PATTERN = re.compile(
    r"\b(?:ubuntu|centos|debian|rocky|almalinux|windows|linux|kernel|"
    r"openjdk|java|python|php|node\.js)\b|阿里云",
    re.IGNORECASE,
)


def _blocked_by_context(text: str) -> bool:
    return _VERSION_CONTEXT_BLOCKER_PATTERN.search(text) is not None


def extract_version(summary: str, app: str) -> str | None:
    """Return a version-like token from the product summary, preferring app context."""
    candidates = list(VERSION_PATTERN.finditer(summary))
    if not candidates:
        return None

    normalized_app = re.sub(r"[^a-z0-9]", "", app.casefold())
    normalized_summary_chars: list[str] = []
    original_positions: list[int] = []
    for index, char in enumerate(summary.casefold()):
        if char.isalnum():
            normalized_summary_chars.append(char)
            original_positions.append(index)
    normalized_summary = "".join(normalized_summary_chars)
    app_index = normalized_summary.find(normalized_app) if normalized_app else -1
    if app_index < 0:
        return None

    app_start = original_positions[app_index]
    app_end = original_positions[app_index + len(normalized_app) - 1] + 1
    for candidate in candidates:
        if candidate.start() < app_end:
            continue
        if _blocked_by_context(summary[app_end:candidate.start()]):
            continue
        return candidate.group(0)

    for candidate in reversed(candidates):
        if candidate.end() > app_start:
            continue
        if _blocked_by_context(summary[max(0, candidate.start() - 24):candidate.start()]):
            continue
        return candidate.group(0)
    return None


def _aliases(product_name: str) -> list[str]:
    names = {product_name}
    for part in re.split(r"[()（）\[\]【】,，/|]", product_name):
        names.add(part)
    without_versions = VERSION_PATTERN.sub(" ", product_name)
    names.add(without_versions)

    aliases: list[str] = []
    for name in names:
        words = [
            word
            for word in re.split(r"[\s_\-]+", name)
            if word and word.casefold() not in _MODIFIERS
        ]
        alias = " ".join(words).strip()
        if alias:
            aliases.append(alias)
    return sorted(set(aliases), key=len, reverse=True)


def extract_summary_version(summary: str, product_name: str) -> str | None:
    """Extract the application version from a product summary using the product name."""
    for alias in _aliases(product_name):
        version = extract_version(summary, alias)
        if version:
            return version
    return None
