from __future__ import annotations

import copy
import json
import time
from pathlib import Path

import click

from .. import offer as service


@click.group("offer")
def offer_command() -> None:
    """Generate, compare and publish AWS AMI listing metadata."""


def inputs(function):
    for option in (
        click.option("--product", type=click.Path(exists=True, dir_okay=False, path_type=Path), required=True),
        click.option("--provider", type=click.Path(exists=True, dir_okay=False, path_type=Path), default=service.DATA / "provider.json"),
        click.option("--template", type=click.Path(exists=True, dir_okay=False, path_type=Path), default=service.DATA / "templates/aws-ami.json"),
    ):
        function = option(function)
    return function


def bundle(product, provider, template):
    try:
        return service.render(product, provider, template)
    except Exception as error:
        raise click.ClickException(f"invalid offer data: {error}") from error


def output(value):
    click.echo(json.dumps(value, indent=2, ensure_ascii=False))


def fetch(bundle, profile):
    if not bundle["entityId"]:
        raise click.ClickException("Catalog EntityId is missing; use mk offer list to resolve it")
    return service.aws_call(service.aws_client(profile), "describe_entity", EntityId=bundle["entityId"])


@offer_command.command("render")
@inputs
@click.option("--format", "output_format", type=click.Choice(["json", "markdown"]), default="json")
def render_command(product, provider, template, output_format):
    """Render a draft offline, including evidence and publication blockers."""
    value = bundle(product, provider, template)
    if output_format == "json":
        output(value)
        return
    sections = []
    for field, content in value["content"].items():
        text = "\n".join(f"- {item['Text']}: {item['Url']}" if isinstance(item, dict) else f"- {item}" for item in content) if isinstance(content, list) else str(content)
        sections.append(f"## {field}\n\n{text}")
    sections.append("## Usage preview (not published)\n\n" + value["deploymentPreview"]["usageInstructions"])
    sections.append("## Publication blockers\n\n" + ("\n".join(f"- {item}" for item in value["publishBlockers"]) or "None"))
    click.echo("\n\n".join(sections))


@offer_command.command("validate")
@inputs
@click.option("--publish-ready", is_flag=True, help="Fail if evidence or Catalog identity is unverified.")
def validate_command(product, provider, template, publish_ready):
    value = bundle(product, provider, template)
    output({"valid": True, "publishBlockers": value["publishBlockers"]})
    if publish_ready and value["publishBlockers"]:
        raise click.ClickException("offer is valid as a draft but not ready to publish")


@offer_command.command("list")
@click.option("--profile", default=None)
def list_command(profile):
    """List seller AMI Catalog IDs and titles (no raw API export)."""
    try:
        client, token = service.aws_client(profile), None
        while True:
            response = service.aws_call(client, "list_entities", EntityType="AmiProduct", MaxResults=10, **({"NextToken": token} if token else {}))
            for item in response.get("EntitySummaryList", []):
                output({"entityId": item["EntityId"], "title": item.get("AmiProductSummary", {}).get("ProductTitle", item.get("Name")), "visibility": item.get("AmiProductSummary", {}).get("Visibility")})
            token = response.get("NextToken")
            if not token:
                break
    except ValueError as error:
        raise click.ClickException(str(error)) from error


@offer_command.command("plan")
@inputs
@click.option("--current", type=click.Path(exists=True, dir_okay=False, path_type=Path), help="Offline DescribeEntity fixture; otherwise query AWS.")
@click.option("--profile", default=None)
def plan_command(product, provider, template, current, profile):
    """Produce a revision-bound UpdateInformation diff without submitting it."""
    value = bundle(product, provider, template)
    try:
        entity = service.read_json(current) if current else fetch(value, profile)
        output(service.plan(value, entity))
    except (ValueError, KeyError, OSError) as error:
        raise click.ClickException(str(error)) from error


@offer_command.command("apply")
@inputs
@click.option("--plan", "plan_path", type=click.Path(exists=True, dir_okay=False, path_type=Path), required=True)
@click.option("--profile", default=None)
@click.option("--wait-seconds", type=click.IntRange(min=0), default=0, help="Poll for up to this many seconds; timeout does not cancel the change.")
def apply_command(product, provider, template, plan_path, profile, wait_seconds):
    """Submit exactly the reviewed plan after rechecking source and live revision."""
    value = bundle(product, provider, template)
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
