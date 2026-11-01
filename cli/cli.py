from __future__ import annotations

import click

from . import __version__
from .commands.list_apps import list_command
from .commands.versions import versions_command


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="mk")
def cli() -> None:
    """Websoft9 marketplace business CLI."""


cli.add_command(list_command, "list")
cli.add_command(versions_command, "versions")


def main() -> None:
    cli(prog_name="mk")
