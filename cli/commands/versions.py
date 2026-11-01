from __future__ import annotations

import csv
import io
import re
import urllib.error

import click

from ..aliyun_market import fetch_aliyun_product
from ..marketplace import OFFER_URL, load_json


@click.command("versions")
@click.option(
    "--platform",
    required=True,
    help="Marketplace platform key from config/marketplace.json (currently: aliyun)",
)
@click.option("--offer", default=OFFER_URL, metavar="SOURCE", help="offer.json URL or local path")
@click.option("--timeout", type=float, default=30, show_default=True, help="HTTP timeout in seconds")
@click.option("--format", "output_format", type=click.Choice(["table", "csv"]), default="table")
def versions_command(platform: str, offer: str, timeout: float, output_format: str) -> None:
    """List marketplace products and their versions from product summaries."""
    platform = platform.strip().lower()
    if platform != "aliyun":
        raise click.ClickException(
            f"version lookup is not implemented for platform '{platform}'; currently supported: aliyun"
        )

    try:
        offers = load_json(offer, timeout)
    except (OSError, ValueError, urllib.error.URLError) as error:
        raise click.ClickException(f"failed to load offer data: {error}") from error

    if not isinstance(offers, list):
        raise click.ClickException("offer data must be a JSON array")

    products: list[tuple[str, str]] = []
    for entry in offers:
        if not isinstance(entry, dict) or entry.get("type") != "app":
            continue
        app = str(entry.get("id") or "").strip()
        codes = (entry.get("productID") or {}).get(platform, [])
        if not app or not isinstance(codes, list):
            continue
        products.extend((app, str(code)) for code in codes if code)

    rows = []
    for app, code in products:
        try:
            detail = fetch_aliyun_product(code, timeout=timeout)
        except Exception as error:
            raise click.ClickException(f"failed to query Aliyun product {code}: {error}") from error
        summary = str(detail.get("ShortDescription") or "")
        product_name = str(detail.get("Name") or "")
        version = extract_version(summary, app)
        if version is None and product_name:
            version = extract_version(summary, product_name)
        rows.append(
            (
                product_name,
                app,
                code,
                version or "未识别",
            )
        )

    if output_format == "csv":
        stream = io.StringIO()
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["商品名称", "应用", "code", "版本"])
        writer.writerows(rows)
        click.echo(stream.getvalue(), nl=False)
        return

    click.echo("| 商品名称 | 应用 | code | 版本 |")
    click.echo("| --- | --- | --- | --- |")
    for row in rows:
        click.echo("| " + " | ".join(value.replace("|", "\\|").replace("\n", " ") for value in row) + " |")


def extract_version(summary: str, app: str) -> str | None:
    """Return a version-like token from the product summary, preferring app context."""
    candidates = list(re.finditer(r"(?<![\w])v?\d+(?:\.\d+){1,3}(?:[-+][0-9A-Za-z.-]+)?", summary, re.IGNORECASE))
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

    app_end = original_positions[app_index + len(normalized_app) - 1] + 1
    following = [candidate for candidate in candidates if candidate.start() >= app_end]
    if following:
        return following[0].group(0)
    preceding = [candidate for candidate in candidates if candidate.end() <= original_positions[app_index]]
    return preceding[-1].group(0) if preceding else None
