"""Typer CLI interface for pi-bridge rune.

Mounted by the MvgeOS CLI as the `pi-import` subcommand (see manifest.json
"commands" and the root cli.py shim, adr-bridge pattern).
"""

from __future__ import annotations

import typer

from mvgeos_runes_pi_bridge.converter import PiFormatError, import_pi_session

app = typer.Typer(
    name="pi-import",
    help="Import a Pi session log (JSONL v3/v4) into a MvgeOS Tome for resume.",
)


@app.command()
def main(
    source_path: str = typer.Argument(..., help="Path to the Pi session .jsonl file"),
    tome_id: str | None = typer.Option(
        None, "--tome-id", help="Tome id to write (default: the Pi session id)"
    ),
    tome_dir: str | None = typer.Option(
        None, "--tome-dir", help="Tome directory (default: ~/.agents/sessions)"
    ),
    force: bool = typer.Option(
        False, "--force", help="Overwrite an existing tome with the same id"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Parse and report without writing anything"
    ),
) -> None:
    """Import a Pi session log into a MvgeOS Tome."""
    try:
        report = import_pi_session(
            source_path,
            tome_id=tome_id,
            tome_dir=tome_dir,
            force=force,
            dry_run=dry_run,
        )
    except PiFormatError as e:
        typer.echo(f"ERROR: {e}", err=True)
        raise typer.Exit(1) from e

    typer.echo(f"Pi format : {report.pi_format}")
    typer.echo(f"Tome id   : {report.tome_id}")
    if report.tome_path:
        typer.echo(f"Tome file : {report.tome_path}")
    typer.echo(f"Entries   : {report.entries}")
    for kind, count in sorted(report.by_pi_type.items()):
        typer.echo(f"  {kind}: {count}")
    for warning in report.warnings:
        typer.echo(f"WARNING: {warning}")
    if report.dry_run:
        typer.echo("(dry run — nothing written)")
    else:
        typer.echo("Done. Resume with: mvgeos --resume " + report.tome_path)
