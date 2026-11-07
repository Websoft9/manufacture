from __future__ import annotations

from pathlib import Path

import click

from .. import contentful, contentful_management
from ..marketplace import CATALOG_URL, catalog_default_path


def _progress(enabled: bool):
    def report(message: str) -> None:
        if enabled:
            click.echo(message, err=True)
    return report


@click.group("catalog")
def catalog_command() -> None:
    """Read application metadata from Contentful."""


@catalog_command.command("pull")
@click.option("--space-id", envvar="CONTENTFUL_SPACE_ID", required=True,
              help="Contentful space id. Prefer the CONTENTFUL_SPACE_ID environment variable.")
@click.option("--token", envvar="CONTENTFUL_TOKEN", required=True,
              help="Contentful token. A CFPAT- Management token is also supported for pull; otherwise use a Delivery/Preview token.")
@click.option("--environment", envvar="CONTENTFUL_ENVIRONMENT", default="master", show_default=True)
@click.option("--content-type", default="product", show_default=True,
              help="Contentful content type id.")
@click.option("--locale", default="en-US", show_default=True,
              help="Contentful locale for the English fields.")
@click.option("--id-field", default="key", show_default=True,
              help="Contentful field containing the application id (for example wordpress).")
@click.option("--fields", "field_list", default="trademark,overview,keywords,usecases,components,summary,hasenterprise", show_default=True,
              help="Comma-separated Contentful field ids to include.")
@click.option("--catalog", "catalog_source", default=CATALOG_URL, show_default=True, metavar="SOURCE",
              help="product_en.json URL or local path; only these application ids are returned.")
@click.option("--apps", "app_list", metavar="IDS",
              help="Comma-separated application ids to export, for example wordpress,odoo. Default: all catalog applications.")
@click.option("--api-url", envvar="CONTENTFUL_API_URL", default=contentful.DEFAULT_API_URL, show_default=True,
              help="Contentful Delivery/Preview API base URL.")
@click.option("--output", type=click.Path(dir_okay=False, path_type=Path), metavar="PATH",
              help="Write JSON here. Default: data/.catalog/catalog.json; use - for stdout.")
@click.option("--page-size", type=click.IntRange(1, 1000), default=100, show_default=True)
@click.option("--include-depth", type=click.IntRange(0, 10), default=1, show_default=True,
              help="Contentful link resolution depth.")
@click.option("--timeout", type=float, default=30, show_default=True,
              help="HTTP timeout in seconds.")
@click.option("--progress/--no-progress", default=True, show_default=True,
              help="Print progress to stderr.")
@click.option("--raw", is_flag=True,
              help="Keep Contentful values as returned instead of resolving links/RichText.")
@click.option("--allow-missing", is_flag=True,
              help="Write available records and list target applications absent from Contentful.")
def pull_command(
    space_id: str,
    token: str,
    environment: str,
    content_type: str,
    locale: str,
    id_field: str,
    field_list: str,
    catalog_source: str,
    app_list: str | None,
    api_url: str,
    output: Path | None,
    page_size: int,
    include_depth: int,
    timeout: float,
    progress: bool,
    raw: bool,
    allow_missing: bool,
) -> None:
    """Pull English Contentful fields for every application in product_en.json.

    The output is one JSON dataset containing only the target applications from
    product_en.json, in catalog order, with the application id and requested fields.
    The API token is sent only in the Authorization header and is never printed.
    """
    fields = tuple(dict.fromkeys(item.strip() for item in field_list.split(",") if item.strip()))
    if not fields:
        raise click.ClickException("--fields must contain at least one Contentful field id.")
    app_ids = None if app_list is None else tuple(item.strip() for item in app_list.split(",") if item.strip())
    if app_list is not None and not app_ids:
        raise click.ClickException("--apps must contain at least one application id.")
    reporter = _progress(progress)
    try:
        dataset = contentful.pull_dataset(
            token=token,
            space_id=space_id,
            environment=environment,
            content_type=content_type,
            locale=locale,
            catalog_source=catalog_source,
            app_ids=app_ids,
            fields=fields,
            id_field=id_field,
            api_url=api_url,
            page_size=page_size,
            include_depth=include_depth,
            timeout=timeout,
            raw=raw,
            allow_missing=allow_missing,
            progress=reporter,
        )
    except contentful.ContentfulError as error:
        raise click.ClickException(str(error)) from None

    text = contentful.dumps_dataset(dataset) + "\n"
    output = output if output is not None else catalog_default_path()
    if str(output) == "-":
        click.echo(text, nl=False)
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")
    if progress:
        click.echo(f"Wrote {dataset['count']} application(s) to {output}", err=True)


@catalog_command.command("push")
@click.option("--space-id", envvar="CONTENTFUL_SPACE_ID", required=True,
              help="Contentful space id. Prefer the CONTENTFUL_SPACE_ID environment variable.")
@click.option("--token", envvar="CONTENTFUL_TOKEN", required=True,
              help="Contentful Management API token (CFPAT-). Prefer the CONTENTFUL_TOKEN environment variable.")
@click.option("--input", "input_path", metavar="PATH",
              help="JSON dataset from catalog pull, a JSON array, or - for stdin. Default: data/.catalog/catalog.json.")
@click.option("--apps", "app_list", metavar="IDS",
              help="Comma-separated application ids to push. Default: every item in the input.")
@click.option("--environment", envvar="CONTENTFUL_ENVIRONMENT", default="master", show_default=True)
@click.option("--content-type", default="product", show_default=True)
@click.option("--locale", default="en-US", show_default=True,
              help="Locale updated for localized fields.")
@click.option("--id-field", default="key", show_default=True,
              help="Contentful field containing the application id.")
@click.option("--api-url", envvar="CONTENTFUL_MANAGEMENT_API_URL", default=contentful_management.DEFAULT_API_URL,
              show_default=True, help="Contentful Management API base URL.")
@click.option("--page-size", type=click.IntRange(1, 1000), default=1000, show_default=True)
@click.option("--timeout", type=float, default=30, show_default=True)
@click.option("--dry-run", is_flag=True, help="Show what would change without writing Contentful.")
@click.option("--publish", is_flag=True, help="Publish each successfully updated entry.")
@click.option("--clear", is_flag=True,
              help="Write empty strings/arrays instead of skipping empty input values.")
@click.option("--allow-missing", is_flag=True,
              help="Skip input applications that are absent from Contentful.")
@click.option("--verbose", is_flag=True, help="Print per-application update details to stderr.")
@click.option("--progress/--no-progress", default=True, show_default=True,
              help="Print progress to stderr.")
def push_command(
    space_id: str,
    token: str,
    input_path: str,
    app_list: str | None,
    environment: str,
    content_type: str,
    locale: str,
    id_field: str,
    api_url: str,
    page_size: int,
    timeout: float,
    dry_run: bool,
    publish: bool,
    clear: bool,
    allow_missing: bool,
    verbose: bool,
    progress: bool,
) -> None:
    """Push repository/catalog changes to Contentful drafts (and optionally publish).

    Only trademark, overview, keywords, usecases, components, summary and
    hasenterprise are written. Empty values are skipped unless --clear is used. Writes use the
    entry's current version, so concurrent Contentful edits fail instead of
    being overwritten.
    """
    app_ids = None if app_list is None else tuple(item.strip() for item in app_list.split(",") if item.strip())
    if app_list is not None and not app_ids:
        raise click.ClickException("--apps must contain at least one application id.")
    reporter = _progress(progress)
    input_path = input_path or str(catalog_default_path())
    try:
        summary = contentful_management.push(
            token=token,
            space_id=space_id,
            environment=environment,
            input_path=input_path,
            content_type=content_type,
            locale=locale,
            id_field=id_field,
            api_url=api_url,
            app_ids=app_ids,
            page_size=page_size,
            timeout=timeout,
            dry_run=dry_run,
            publish=publish,
            clear=clear,
            allow_missing=allow_missing,
            verbose=verbose,
            progress=reporter,
        )
    except contentful.ContentfulError as error:
        raise click.ClickException(str(error)) from None

    label = "Would update" if dry_run else "Updated"
    click.echo(f"Selected applications: {summary['selected']}", err=True)
    click.echo(f"Matched in Contentful: {summary['matched']}", err=True)
    click.echo(f"{label}: {summary['updated']}", err=True)
    if publish and not dry_run:
        click.echo(f"Published: {summary['published']}", err=True)
    click.echo(f"Unchanged: {summary['unchanged']}", err=True)
    click.echo(f"Skipped empty fields: {summary['skippedEmpty']}", err=True)
    if summary["missing"]:
        click.echo(f"Missing in Contentful: {', '.join(summary['missing'])}", err=True)
    if summary["errors"]:
        for error in summary["errors"]:
            click.echo(f"ERROR: {error}", err=True)
        raise click.ClickException(f"{len(summary['errors'])} push error(s).")
    if dry_run:
        click.echo("Dry run: no Contentful changes were written.", err=True)
