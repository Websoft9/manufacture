from __future__ import annotations

import urllib.error
from pathlib import Path

import click

from ..marketplace import (
    CATALOG_URL,
    OFFER_URL,
    collect_rows,
    load_json,
    render_markdown,
    update_readme as update_readme_section,
)


@click.command("list")
@click.option("--offer", default=OFFER_URL, metavar="SOURCE", help="offer.json URL or local path")
@click.option(
    "--catalog",
    default=CATALOG_URL,
    metavar="SOURCE",
    help="product_en.json URL or local path",
)
@click.option(
    "--update-readme",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
    metavar="PATH",
    help="replace the generated table section in an existing README",
)
@click.option(
    "--timeout",
    type=float,
    default=30,
    show_default=True,
    help="HTTP timeout in seconds",
)
def list_command(
    offer: str,
    catalog: str,
    update_readme: Path | None,
    timeout: float,
) -> None:
    """List applications and their Marketplace product links."""
    try:
        offers = load_json(offer, timeout)
        catalog_data = load_json(catalog, timeout)
    except (OSError, ValueError, urllib.error.URLError) as error:
        raise click.ClickException(f"failed to load marketplace data: {error}") from error

    if not isinstance(offers, list) or not isinstance(catalog_data, list):
        raise click.ClickException("offer and catalog data must be JSON arrays")

    rows = collect_rows(offers, catalog_data)
    section = render_markdown(rows)

    if update_readme is None:
        click.echo(section)
        return

    changed = update_readme_section(update_readme, section)
    listed = sum(1 for row in rows if row.in_catalog and row.has_links)
    unlisted = sum(1 for row in rows if row.in_catalog and not row.has_links)
    outside = sum(1 for row in rows if not row.in_catalog and row.has_links)
    state = "updated" if changed else "unchanged"
    click.echo(
        f"{state}: {update_readme} "
        f"(listed={listed}, unlisted={unlisted}, outside_catalog={outside})",
        err=True,
    )
