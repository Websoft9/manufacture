from __future__ import annotations

import re

VERSION_PATTERN = re.compile(
    r"(?<![\w])v?\d+(?:\.\d+){1,3}(?:[-+][0-9A-Za-z.-]+)?",
    re.IGNORECASE,
)
MARKETPLACE_VERSION_PATTERN = re.compile(
    r"(?<![\w])v?\d+(?:\.\d+){0,3}(?:[-+][0-9A-Za-z.-]+)?",
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


_STOPWORDS = {
    "a",
    "an",
    "and",
    "by",
    "for",
    "from",
    "hardened",
    "in",
    "latest",
    "minutes",
    "of",
    "on",
    "or",
    "preconfigured",
    "preview",
    "provided",
    "ready",
    "the",
    "to",
    "version",
    "with",
}

_ATTACHED_VERSION_PATTERN = re.compile(
    r"(?P<name>[A-Za-z][A-Za-z0-9+._-]*?)[ ]?(?P<version>v?\d+(?:\.\d+){0,3})",
    re.IGNORECASE,
)

_TITLE_VERSION_PATTERN = re.compile(
    r"v?\d+(?:\.\d+){0,3}(?:[-+][0-9A-Za-z.-]+)?",
    re.IGNORECASE,
)


def _title_tokens(*titles: str | None) -> set[str]:
    """Return lower-case ASCII words and runs from titles, ignoring stopwords."""
    tokens: set[str] = set()
    for title in titles:
        if not title:
            continue
        for word in re.findall(r"[A-Za-z]+", title):
            folded = word.casefold()
            if len(folded) >= 2 and folded not in _STOPWORDS:
                tokens.add(folded)
        for run in re.findall(r"[A-Za-z][A-Za-z0-9+._-]*", title):
            tokens.add(run.casefold())
    return tokens


def _preceding_tokens(text: str, limit: int = 48) -> set[str]:
    """Return ASCII words immediately before a version token."""
    window = text[-limit:]
    tokens = {
        word.casefold()
        for word in re.findall(r"[A-Za-z][A-Za-z0-9+._-]*", window)
        if len(word) >= 2 and word.casefold() not in _STOPWORDS
    }
    return tokens


def _first_clause_versions(clause: str) -> list[tuple[int, str, str | None]]:
    """List (start, version, attached_name) candidates in a clause."""
    found: list[tuple[int, str, str | None]] = []
    attached_spans: list[tuple[int, int]] = []
    for match in _ATTACHED_VERSION_PATTERN.finditer(clause):
        name = match.group("name")
        version = match.group("version")
        # Only treat the digits as attached when they directly follow letters.
        if match.start("version") != match.end("name"):
            continue
        found.append((match.start("name"), version, name))
        attached_spans.append((match.start("version"), match.end("version")))
    for match in MARKETPLACE_VERSION_PATTERN.finditer(clause):
        if any(start <= match.start() < end for start, end in attached_spans):
            continue
        found.append((match.start(), match.group(0), None))
    found.sort(key=lambda item: item[0])
    return found


def _version_from_title(title: str) -> str | None:
    for match in _TITLE_VERSION_PATTERN.finditer(title):
        value = match.group(0)
        start = match.start()
        if start == 0:
            continue
        attached = not title[start - 1].isspace()
        if attached:
            if "." not in value or not title[start - 1].isalpha():
                continue
            return value.lstrip("vV")
        word = re.search(r"[A-Za-z][A-Za-z0-9+._-]*\s*$", title[:start])
        if word and word.group(0).strip().casefold() not in _STOPWORDS:
            return value.lstrip("vV")
    return None


def extract_marketplace_version(
    summary: str,
    product_title: str,
    app_name: str | None = None,
) -> str | None:
    """Extract a marketplace app version from the first summary clause.

    Marketplace titles follow `<trademark> <description>` and the summary's first
    comma-delimited clause usually starts with `<trademark> <version>`. Match a
    version in that clause when the text just before it shares a word with the
    title/app name. If that fails, fall back to an explicit version in the title
    itself, and only then to an unanchored `vN`/dotted version in the clause.
    """
    first_clause = re.split(r"[,，]", summary, maxsplit=1)[0].strip()
    title_tokens = _title_tokens(product_title, app_name)

    if first_clause:
        for start, version, attached_name in _first_clause_versions(first_clause):
            if attached_name:
                # A digit embedded in a trademark (TYPO3, Neo4j, Websoft9) is not
                # a version: skip when the whole run already appears in the title.
                run = re.match(r"[A-Za-z][A-Za-z0-9+._-]*", first_clause[start:])
                run_text = run.group(0) if run else ""
                if run_text.casefold() in title_tokens:
                    continue
                stem = re.sub(r"v?\d+$", "", attached_name, flags=re.IGNORECASE)
                if stem.casefold() in title_tokens:
                    return version.lstrip("vV")
                continue
            if _blocked_by_context(first_clause[:start]):
                continue
            if _preceding_tokens(first_clause[:start]) & title_tokens:
                return version.lstrip("vV")

        for _, version, _ in _first_clause_versions(first_clause):
            if version.casefold().startswith("v") or "." in version:
                return version.lstrip("vV")

    return _version_from_title(product_title)
