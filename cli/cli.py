from __future__ import annotations

import click

from . import __version__
from .commands.catalog import catalog_command
from .commands.list_apps import list_command
from .commands.versions import versions_command
from .commands.offer import offer_command


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="mk")
def cli() -> None:
    """Websoft9 marketplace business CLI."""


@click.command("help")
@click.pass_context
def help_command(ctx: click.Context) -> None:
    """Show this help message."""
    click.echo(ctx.parent.get_help() if ctx.parent else cli.get_help(click.Context(cli, info_name="mk")))


cli.add_command(list_command, "list")
cli.add_command(versions_command, "versions")
cli.add_command(offer_command, "offer")
cli.add_command(catalog_command, "catalog")
cli.add_command(help_command, "help")


def main() -> None:
    cli(prog_name="mk")
