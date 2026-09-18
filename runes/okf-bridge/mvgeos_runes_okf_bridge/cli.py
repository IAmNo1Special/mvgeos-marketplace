"""Typer CLI interface for okf-bridge rune."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from mvgeos_runes_okf_bridge.graph import KnowledgeGraph
from mvgeos_runes_okf_bridge.migrator import migrate_bundle_in_place
from mvgeos_runes_okf_bridge.validator import validate_okf_bundle
from mvgeos_runes_okf_bridge.visualizer import generate_html_graph

app = typer.Typer(name="okf", help="Open Knowledge Format (OKF v0.2) management")


@app.command("status")
def okf_status(
    bundle_dir: str = typer.Argument(None, help="Path to .okf directory"),
) -> None:
    """Display summary of OKF knowledge bundle."""
    target = Path(bundle_dir) if bundle_dir else (Path.cwd() / ".okf")
    if not target.is_dir():
        typer.echo(f"MISSING: OKF directory '{target}' does not exist.")
        raise typer.Exit(1)

    graph = KnowledgeGraph.load(bundle_path=target)
    trust = graph.trust_summary()
    stale = graph.stale_count()
    types_str = (
        ", ".join(f"{k}: {v}" for k, v in sorted(graph.types_summary().items()))
        or "None"
    )

    typer.echo("OKF Knowledge Bundle Status:")
    typer.echo(f"  Directory:       {target.resolve()}")
    typer.echo(f"  Total Concepts:  {len(graph.concepts)}")
    typer.echo(f"  Types Breakdown: {types_str}")
    typer.echo(f"  Human-Reviewed:  {trust['human-reviewed']}")
    typer.echo(f"  Machine-Confirmed: {trust['machine-confirmed']}")
    typer.echo(f"  Unverified:      {trust['unverified']}")
    typer.echo(f"  Stale Concepts:  {stale}")


@app.command("validate")
def okf_validate(
    bundle_dir: str = typer.Argument(None, help="Path to .okf directory"),
    strict: bool = typer.Option(False, "--strict", help="Treat warnings as errors"),
    output_json: bool = typer.Option(False, "--json", help="Output results as JSON"),
) -> None:
    """Validate OKF bundle against v0.2 specification (§11)."""
    target = Path(bundle_dir) if bundle_dir else (Path.cwd() / ".okf")
    report = validate_okf_bundle(target, strict=strict)

    if output_json:
        data = {
            "valid": report.valid,
            "errors": [
                {"path": e.rel_path, "message": e.message} for e in report.errors
            ],
            "warnings": [
                {"path": w.rel_path, "message": w.message} for w in report.warnings
            ],
            "concepts": report.concepts,
            "indexes": report.indexes,
            "logs": report.logs,
        }
        typer.echo(json.dumps(data, indent=2))
        if not report.valid:
            raise typer.Exit(1)
        return

    if not target.is_dir():
        typer.echo(f"MISSING: OKF directory '{target}' does not exist.")
        raise typer.Exit(1)

    typer.echo(
        f"Validated {report.concepts} concepts, {report.indexes} indexes, {report.logs} logs."
    )
    for err in report.errors:
        typer.echo(f"  FAIL: {err.rel_path}: {err.message}")
    for warn in report.warnings:
        typer.echo(f"  WARN: {warn.rel_path}: {warn.message}")

    if report.valid:
        typer.echo("OK: OKF bundle is fully conformant.")
    else:
        typer.echo(f"FAIL: OKF bundle has {len(report.errors)} conformance errors.")
        raise typer.Exit(1)


@app.command("graph")
def okf_graph(
    bundle_dir: str = typer.Argument(None, help="Path to .okf directory"),
    output_file: str = typer.Option(
        None, "-o", "--output", help="Output HTML file path"
    ),
) -> None:
    """Generate interactive Cytoscape.js HTML visualization of knowledge bundle."""
    target = Path(bundle_dir) if bundle_dir else (Path.cwd() / ".okf")
    if not target.is_dir():
        typer.echo(f"MISSING: OKF directory '{target}' does not exist.")
        raise typer.Exit(1)

    graph = KnowledgeGraph.load(bundle_path=target)
    html = generate_html_graph(graph, title=f"Knowledge Graph: {target.name}")

    out_path = Path(output_file) if output_file else (target / "viz.html")
    out_path.write_text(html, encoding="utf-8")
    typer.echo(f"OK: Rendered knowledge graph to {out_path.resolve()}.")


@app.command("migrate")
def okf_migrate(
    bundle_dir: str = typer.Argument(None, help="Path to .okf directory"),
) -> None:
    """Migrate an OKF v0.1 bundle to v0.2 in place (§13.1)."""
    target = Path(bundle_dir) if bundle_dir else (Path.cwd() / ".okf")
    if not target.is_dir():
        typer.echo(f"MISSING: OKF directory '{target}' does not exist.")
        raise typer.Exit(1)

    modified = migrate_bundle_in_place(target)
    if modified:
        typer.echo(f"OK: Migrated {len(modified)} files to OKF v0.2:")
        for m in modified:
            typer.echo(f"  - {m}")
    else:
        typer.echo("OK: All files already conform to OKF v0.2.")


@app.command("search")
def okf_search_cmd(
    query: str = typer.Argument("", help="Search query string"),
    bundle_dir: str = typer.Option(None, "--bundle", help="Path to .okf directory"),
    type_filter: str = typer.Option(None, "--type", help="Filter by concept type"),
    tag_filter: str = typer.Option(None, "--tag", help="Filter by tag"),
) -> None:
    """Search concepts in OKF knowledge bundle."""
    target = Path(bundle_dir) if bundle_dir else (Path.cwd() / ".okf")
    if not target.is_dir():
        typer.echo(f"MISSING: OKF directory '{target}' does not exist.")
        raise typer.Exit(1)

    graph = KnowledgeGraph.load(bundle_path=target)
    results = graph.search(query=query, type_filter=type_filter, tag_filter=tag_filter)
    if not results:
        typer.echo(f"MISSING: No concepts found matching query '{query}'.")
        return

    typer.echo(f"FOUND: {len(results)} matching concepts:")
    for c in results:
        typer.echo(
            f"  - {c.id} ({c.type}) [{c.trust_tier.value}]: {c.title or c.description}"
        )


@app.command("init")
def okf_init_cmd(
    bundle_dir: str = typer.Argument(
        ".okf", help="Target directory for new OKF bundle"
    ),
    title: str = typer.Option(
        "Project Knowledge Base", "--title", help="Title of knowledge bundle"
    ),
    force: bool = typer.Option(False, "--force", help="Overwrite existing files"),
) -> None:
    """Initialize a brand-new conformant OKF v0.2 bundle (§3, §8, §9)."""
    target = Path(bundle_dir)
    target.mkdir(parents=True, exist_ok=True)

    root_index = target / "index.md"
    root_log = target / "log.md"
    sample_concept = target / "getting-started.md"

    if not force and (root_index.exists() or root_log.exists()):
        typer.echo(
            f"FAIL: Directory '{target}' already contains OKF files. Use --force to overwrite."
        )
        raise typer.Exit(1)

    # Scaffolding root index.md
    root_index.write_text(
        f'---\nokf_version: "0.2"\n---\n\n# {title}\n\n'
        f"A conformant Open Knowledge Format (OKF v0.2) knowledge bundle.\n\n"
        f"## Concepts\n\n* [Getting Started](getting-started.md) - Overview and getting started guide.\n",
        encoding="utf-8",
    )

    # Scaffolding root log.md
    from datetime import UTC, datetime

    today = datetime.now(UTC).date().isoformat()
    root_log.write_text(
        f"# Directory Update Log\n\n## {today}\n* **Creation**: Initialized OKF v0.2 knowledge bundle.\n",
        encoding="utf-8",
    )

    # Scaffolding starter concept
    sample_concept.write_text(
        f"---\n"
        f"type: Guide\n"
        f"title: Getting Started\n"
        f"description: Overview and getting started guide for this project.\n"
        f"tags: [guide, onboarding]\n"
        f"status: stable\n"
        f"generated:\n"
        f"  by: human:mvgeos\n"
        f"  at: '{today}'\n"
        f"verified:\n"
        f"  - by: human:mvgeos\n"
        f"    at: '{today}'\n"
        f"---\n\n"
        f"# Getting Started\n\nWelcome to the project knowledge base.\n",
        encoding="utf-8",
    )

    typer.echo(f"OK: Initialized conformant OKF v0.2 bundle at {target.resolve()}.")
