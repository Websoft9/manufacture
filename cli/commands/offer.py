from __future__ import annotations

import copy
import json
import time
from pathlib import Path

import click

from .. import catalog_data
from .. import offer as service
from ..marketplace import CONFIGURED_PLATFORMS, VERSIONS_URL, catalog_default_path


@click.group("offer")
def offer_command() -> None:
    """Generate, compare and publish AWS AMI listing metadata."""


def inputs(function):
    for option in (
        click.option("--app", required=True, help="Application id from data/.catalog/catalog.json."),
        click.option("--catalog", "catalog_source", default=None, metavar="SOURCE",
                     help="Temporary Contentful catalog JSON. Default: data/.catalog/catalog.json."),
        click.option("--versions", default=VERSIONS_URL, metavar="SOURCE",
                     help="Application version source URL or local JSON."),
        click.option("--vendor", type=click.Path(exists=True, dir_okay=False, path_type=Path),
                     default=service.DATA / "vendor.json"),
        click.option("--template", type=click.Path(exists=True, dir_okay=False, path_type=Path),
                     default=service.DATA / "templates/aws-ami.json"),
    ):
        function = option(function)
    return function


def bundle(app, catalog_source, versions, vendor, template):
    try:
        runtime = catalog_data.load_runtime_product(
            key=app,
            catalog_source=catalog_source or str(catalog_default_path()),
            versions_source=versions,
        )
        return service.render(runtime, vendor, template)
    except Exception as error:
        raise click.ClickException(f"invalid offer data: {error}") from error


def output(value):
    click.echo(json.dumps(value, indent=2, ensure_ascii=False))


def _markdown_value(value):
    if isinstance(value, list):
        return "\n".join(
            f"- {item['Text']}: {item['Url']}" if isinstance(item, dict) else f"- {item}"
            for item in value
        )
    return str(value)


def preview_markdown(preview):
    target = preview.get("target") or {}
    lines = [
        f"# {preview.get('templateId', 'preview')}",
        "",
        f"> Target: {target.get('platform', '-')} / {target.get('service', '-')} / {target.get('entityType', '-')}",
        "",
        "## Content",
        "",
    ]
    for field, value in (preview.get("content") or {}).items():
        lines.extend([f"### {field}", "", _markdown_value(value), ""])
    resources = preview.get("AdditionalResources") or []
    if resources:
        lines.extend(["## AdditionalResources", "", _markdown_value(resources), ""])
    sections = preview.get("longDescriptionSections") or []
    if sections:
        lines.extend(["## Long description", ""])
        for section in sections:
            if section.get("heading"):
                lines.extend([f"### {section['heading']}", ""])
            lines.extend([section.get("text", ""), ""])
    return "\n".join(lines).rstrip() + "\n"


def write_text_output(text, path):
    if path is None or str(path) == "-":
        click.echo(text, nl=False)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    click.echo(f"Wrote {path}", err=True)


def write_output(value, path):
    write_text_output(json.dumps(value, indent=2, ensure_ascii=False) + "\n", path)


def fetch(bundle_value, profile):
    if not bundle_value["entityId"]:
        raise click.ClickException(
            "Catalog EntityId is missing; use mk offer resolve-entity --cloud aws --code <offer-code>"
        )
    return service.aws_call(service.aws_client(profile), "describe_entity", EntityId=bundle_value["entityId"])


@offer_command.command("build")
@inputs
@click.option("--cloud", required=True, type=click.Choice(CONFIGURED_PLATFORMS),
              help="Target cloud platform from config/marketplace.json. Must match the template target.")
@click.option("--output", "output_path", type=click.Path(dir_okay=False, path_type=Path), metavar="PATH",
              help="Default: data/.catalog/<cloud>/<key>.json; use - for stdout.")
@click.option("--publish-ready", is_flag=True,
              help="Fail without writing when required version or Catalog identity is missing.")
def build_command(app, catalog_source, versions, vendor, template, cloud, output_path, publish_ready):
    """Build a human-review preview matching the authoring template."""
    value = bundle(app, catalog_source, versions, vendor, template)
    preview = value["preview"]
    target_platform = (preview.get("target") or {}).get("platform")
    if target_platform != cloud:
        raise click.ClickException(
            f"template target platform {target_platform!r} does not match --cloud {cloud!r}"
        )
    if publish_ready and value["publishBlockers"]:
        raise click.ClickException(
            "offer is valid as a draft but not ready to publish: "
            + "; ".join(value["publishBlockers"])
        )
    target = output_path or (service.ROOT / "data" / ".catalog" / cloud / f"{value['key']}.json")
    if str(target) != "-" and target.suffix.lower() in {".md", ".markdown"}:
        write_text_output(preview_markdown(preview), target)
    else:
        write_output(preview, target)


def _resolve_aws_entities(codes, profile, max_results=50):
    client = service.aws_client(profile)
    wanted = set(codes)
    matches = {code: [] for code in wanted}
    token = None
    while True:
        request = {"EntityType": "AmiProduct", "MaxResults": max_results}
        if token:
            request["NextToken"] = token
        response = service.aws_call(client, "list_entities", **request)
        for item in response.get("EntitySummaryList", []):
            entity_id = item.get("EntityId", "")
            if not entity_id:
                continue
            detail = service.aws_call(client, "describe_entity", EntityId=entity_id)
            document = detail.get("DetailsDocument")
            if document is None:
                try:
                    document = json.loads(detail.get("Details") or "{}")
                except (TypeError, ValueError):
                    continue
            description = document.get("Description") or {}
            sku = str(description.get("Sku") or "").strip()
            product_code = str(description.get("ProductCode") or "").strip()
            matched_codes = wanted & {sku, product_code, entity_id}
            if not matched_codes:
                continue
            summary = item.get("AmiProductSummary") or {}
            result = {
                "cloud": "aws",
                "entityId": entity_id,
                "title": summary.get("ProductTitle") or description.get("ProductTitle") or item.get("Name", ""),
                "visibility": summary.get("Visibility") or description.get("Visibility", ""),
                "sku": sku,
                "productCode": product_code,
            }
            for code in matched_codes:
                matches[code].append({**result, "code": code})
        token = response.get("NextToken")
        if not token:
            break
    return matches


@offer_command.command("resolve-entity")
@click.option("--cloud", required=True, type=click.Choice(["aws"]),
              help="Cloud platform (currently: aws).")
@click.option("--code", "codes", required=True, multiple=True,
              help="Marketplace offer code, SKU, or product code. Repeat for multiple codes.")
@click.option("--profile", default=None)
def resolve_entity_command(cloud, codes, profile):
    """Resolve marketplace offer codes to seller Catalog EntityIds."""
    try:
        if cloud != "aws":
            raise click.ClickException(f"unsupported cloud: {cloud}")
        unique_codes = list(dict.fromkeys(codes))
        matches = _resolve_aws_entities(unique_codes, profile)
        results = []
        not_found = []
        ambiguous = {}
        for code in unique_codes:
            found = matches.get(code, [])
            if len(found) == 1:
                results.append(found[0])
            elif not found:
                not_found.append(code)
            else:
                ambiguous[code] = [item["entityId"] for item in found]
        if len(unique_codes) == 1:
            if not_found:
                raise click.ClickException(
                    f"no AWS AMI product found for offer code {not_found[0]!r}"
                )
            if ambiguous:
                code = next(iter(ambiguous))
                raise click.ClickException(
                    f"offer code {code!r} is ambiguous: {', '.join(ambiguous[code])}"
                )
            output(results[0])
            return
        output({"results": results, "notFound": not_found, "ambiguous": ambiguous})
        if not_found or ambiguous:
            raise click.exceptions.Exit(1)
    except ValueError as error:
        raise click.ClickException(str(error)) from error


@offer_command.command("plan")
@inputs
@click.option("--current", type=click.Path(exists=True, dir_okay=False, path_type=Path), help="Offline DescribeEntity fixture; otherwise query AWS.")
@click.option("--profile", default=None)
@click.option("--output", "output_path", type=click.Path(dir_okay=False, path_type=Path), metavar="PATH",
              help="Write the complete plan/request here instead of stdout.")
def plan_command(app, catalog_source, versions, vendor, template, current, profile, output_path):
    """Produce a revision-bound UpdateInformation diff without submitting it."""
    value = bundle(app, catalog_source, versions, vendor, template)
    try:
        entity = service.read_json(current) if current else fetch(value, profile)
        write_output(service.plan(value, entity), output_path)
    except (ValueError, KeyError, OSError) as error:
        raise click.ClickException(str(error)) from error


@offer_command.command("apply")
@inputs
@click.option("--plan", "plan_path", type=click.Path(exists=True, dir_okay=False, path_type=Path), required=True)
@click.option("--profile", default=None)
@click.option("--wait-seconds", type=click.IntRange(min=0), default=0, help="Poll for up to this many seconds; timeout does not cancel the change.")
def apply_command(app, catalog_source, versions, vendor, template, plan_path, profile, wait_seconds):
    """Submit exactly the reviewed plan after rechecking source and live revision."""
    value = bundle(app, catalog_source, versions, vendor, template)
    if value["publishBlockers"]:
        raise click.ClickException("publication blocked: " + "; ".join(value["publishBlockers"]))
    try:
        reviewed = service.read_json(plan_path)
        client = service.aws_client(profile)
        live = service.aws_call(client, "describe_entity", EntityId=value["entityId"])
        expected = service.plan(value, live)
        if reviewed != expected:
            raise ValueError("plan is stale or modified; regenerate and review it")
        if expected["request"] is None:
            output({"status": "NO_CHANGES"})
            return
        request = copy.deepcopy(expected["request"])
        request.pop("Catalog")
        request["ClientRequestToken"] = expected["planHash"]
        response = service.aws_call(client, "start_change_set", **request)
        change_id = response["ChangeSetId"]
        output({"changeSetId": change_id, "status": "SUBMITTED", "planHash": expected["planHash"]})
        if wait_seconds:
            poll(client, change_id, wait_seconds, value)
    except (ValueError, KeyError, OSError) as error:
        raise click.ClickException(str(error)) from error


def poll(client, change_id, wait_seconds, value=None):
    deadline = time.monotonic() + wait_seconds
    while True:
        status = service.change_status(service.aws_call(client, "describe_change_set", ChangeSetId=change_id))
        if status["status"] in {"SUCCEEDED", "FAILED", "CANCELLED"}:
            output(status)
            if status["status"] != "SUCCEEDED":
                raise ValueError(f"ChangeSet ended with {status['status']}")
            if value:
                live = service.aws_call(client, "describe_entity", EntityId=value["entityId"])
                if service.plan(value, live)["request"] is not None:
                    raise ValueError("ChangeSet succeeded but read-back differs; inspect the product before retrying")
                output({"readBackVerified": True, "entityId": value["entityId"]})
            return
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            output({**status, "pollingTimedOut": True})
            return
        time.sleep(min(5, remaining))


@offer_command.command("status")
@click.argument("change_set_id")
@click.option("--profile", default=None)
@click.option("--wait-seconds", type=click.IntRange(min=0), default=0)
def status_command(change_set_id, profile, wait_seconds):
    """Report ChangeSet status/error codes without dumping its private payload."""
    try:
        poll(service.aws_client(profile), change_set_id, wait_seconds)
    except ValueError as error:
        raise click.ClickException(str(error)) from error
