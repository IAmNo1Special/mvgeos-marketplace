"""Rune factory and lifecycle hook registration for okf-bridge."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mvgeos_runes.rune_api import RuneAPI
from mvgeos_runes.types import BeforeMvgeStartData, SigilHook, SpellDefinition

from mvgeos_runes_okf_bridge.graph import KnowledgeGraph
from mvgeos_runes_okf_bridge.prompt import (
    render_knowledge_catalog,
    update_invocations_with_catalog,
)
from mvgeos_runes_okf_bridge.validator import validate_okf_bundle
from mvgeos_runes_okf_bridge.visualizer import generate_html_graph


def rune_factory(api: RuneAPI) -> None:
    """Initialize and bind OKF bridge rune to session lifecycle."""
    runner = getattr(api, "_runner", None)
    ctx = getattr(runner, "context", None) if runner else None
    raw_cwd = getattr(ctx, "cwd", None) if ctx else None
    cwd: Path | None = Path(raw_cwd) if raw_cwd else None

    # In-memory knowledge graph
    graph = KnowledgeGraph.load(cwd=cwd)
    catalog_xml = render_knowledge_catalog(graph)

    # 1. Lifecycle Hooks
    async def on_session_start(_data: Any = None) -> None:
        nonlocal graph, catalog_xml
        # Refresh on session start
        graph = KnowledgeGraph.load(cwd=cwd)
        catalog_xml = render_knowledge_catalog(graph)

    async def on_before_mvge_start(data: Any = None) -> Any:
        nonlocal catalog_xml
        if not catalog_xml:
            return data

        if isinstance(data, BeforeMvgeStartData):
            data.base_prompt = f"{data.base_prompt}\n\n{catalog_xml}".strip()
            return data
        if isinstance(data, dict) and "base_prompt" in data:
            data["base_prompt"] = f"{data['base_prompt']}\n\n{catalog_xml}".strip()
            return data
        return data

    async def on_context_transform(invocations: Any = None) -> Any:
        if isinstance(invocations, list):
            return update_invocations_with_catalog(invocations, catalog_xml)
        return invocations

    async def on_session_shutdown(_data: Any = None) -> None:
        nonlocal graph, catalog_xml
        graph = KnowledgeGraph()
        catalog_xml = ""

    api.on(SigilHook.SESSION_START, on_session_start)
    api.on(SigilHook.BEFORE_MVGE_START, on_before_mvge_start)
    api.on(SigilHook.CONTEXT_TRANSFORM, on_context_transform)
    api.on(SigilHook.SESSION_SHUTDOWN, on_session_shutdown)

    # 2. Spells
    async def handle_okf_search(
        params: dict[str, Any] | None = None,
        *args: Any,
        arguments: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        payload = params if params is not None else arguments or {}
        q = str(payload.get("query", ""))
        type_filter = payload.get("type_filter")
        tag_filter = payload.get("tag_filter")

        results = graph.search(
            query=q,
            type_filter=str(type_filter) if type_filter else None,
            tag_filter=str(tag_filter) if tag_filter else None,
        )
        data = [
            {
                "id": c.id,
                "title": c.title or c.id,
                "type": c.type,
                "description": c.description,
                "trust_tier": c.trust_tier.value,
                "is_stale": c.is_stale,
                "tags": c.tags,
            }
            for c in results
        ]
        return json.dumps(data, indent=2)

    async def handle_okf_get(
        params: dict[str, Any] | None = None,
        *args: Any,
        arguments: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        payload = params if params is not None else arguments or {}
        cid = str(payload.get("concept_id", "")).strip()
        concept = graph.get(cid)
        if concept is None:
            return json.dumps(
                {"error": f"Concept '{cid}' not found in knowledge bundle."}
            )

        data = {
            "id": concept.id,
            "type": concept.type,
            "title": concept.title,
            "description": concept.description,
            "resource": concept.resource,
            "tags": concept.tags,
            "status": concept.status,
            "stale_after": concept.stale_after,
            "trust_tier": concept.trust_tier.value,
            "is_stale": concept.is_stale,
            "generated": concept.generated,
            "verified": concept.verified,
            "sources": [
                {
                    "id": s.id,
                    "resource": s.resource,
                    "title": s.title,
                    "author": s.author,
                    "usage_count": s.usage_count,
                    "last_modified": s.last_modified,
                }
                for s in concept.sources
            ],
            "links_to": graph.links_to(concept.id),
            "cited_by": graph.cited_by(concept.id),
            "body": concept.body,
        }
        return json.dumps(data, indent=2)

    async def handle_okf_validate(
        params: dict[str, Any] | None = None,
        *args: Any,
        arguments: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        payload = params if params is not None else arguments or {}
        target = payload.get("bundle_path")
        strict = bool(payload.get("strict", False))

        target_path = (
            Path(str(target))
            if target
            else (graph.bundle_root or (cwd / ".okf" if cwd else Path(".okf")))
        )
        report = validate_okf_bundle(target_path, strict=strict)
        data = {
            "valid": report.valid,
            "errors": [
                {"path": e.rel_path, "message": e.message} for e in report.errors
            ],
            "warnings": [
                {"path": w.rel_path, "message": w.message} for w in report.warnings
            ],
            "concepts_checked": report.concepts,
            "indexes_checked": report.indexes,
            "logs_checked": report.logs,
        }
        return json.dumps(data, indent=2)

    api.register_spell(
        SpellDefinition(
            name="okf_search",
            description="Search the project Open Knowledge Format (.okf/) knowledge base by query, type, or tags.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search keyword"},
                    "type_filter": {
                        "type": "string",
                        "description": "Filter by concept type",
                    },
                    "tag_filter": {"type": "string", "description": "Filter by tag"},
                },
            },
            handler=handle_okf_search,
        )
    )

    api.register_spell(
        SpellDefinition(
            name="okf_get",
            description="Retrieve detailed specifications, trust metadata, sources, and links for a specific OKF concept.",
            parameters={
                "type": "object",
                "properties": {
                    "concept_id": {
                        "type": "string",
                        "description": "Concept ID (relative path without .md)",
                    },
                },
                "required": ["concept_id"],
            },
            handler=handle_okf_get,
        )
    )

    api.register_spell(
        SpellDefinition(
            name="okf_validate",
            description="Validate an Open Knowledge Format bundle against the v0.2 specification (§11).",
            parameters={
                "type": "object",
                "properties": {
                    "bundle_path": {
                        "type": "string",
                        "description": "Optional path to bundle directory",
                    },
                    "strict": {
                        "type": "boolean",
                        "description": "Treat warnings as errors",
                    },
                },
            },
            handler=handle_okf_validate,
        )
    )

    # 3. Slash Commands
    async def okf_command(args: str = "") -> str:
        parts = args.strip().split()
        subcmd = parts[0] if parts else "status"

        if subcmd == "status":
            trust = graph.trust_summary()
            stale = graph.stale_count()
            types_str = (
                ", ".join(f"{k}: {v}" for k, v in sorted(graph.types_summary().items()))
                or "None"
            )
            return (
                f"OKF Knowledge Bundle Status:\n"
                f"  Directory:       {graph.bundle_root or 'MISSING: No bundle loaded'}\n"
                f"  Total Concepts:  {len(graph.concepts)}\n"
                f"  Types Breakdown: {types_str}\n"
                f"  Human-Reviewed:  {trust['human-reviewed']}\n"
                f"  Machine-Confirmed: {trust['machine-confirmed']}\n"
                f"  Unverified:      {trust['unverified']}\n"
                f"  Stale Concepts:  {stale}"
            )
        if subcmd == "search":
            query = " ".join(parts[1:])
            results = graph.search(query=query)
            if not results:
                return f"MISSING: No concepts found matching '{query}'."
            lines = [f"FOUND: {len(results)} concepts matching '{query}':"]
            for c in results[:10]:
                lines.append(
                    f"  - {c.id} ({c.type}) [{c.trust_tier.value}]: {c.title or c.description}"
                )
            return "\n".join(lines)
        if subcmd == "validate":
            rep = validate_okf_bundle(graph.bundle_root or Path(".okf"))
            status_text = (
                "OK: Bundle is conformant."
                if rep.valid
                else "FAIL: Bundle is non-conformant."
            )
            return (
                f"{status_text}\n"
                f"  Concepts: {rep.concepts}, Errors: {len(rep.errors)}, Warnings: {len(rep.warnings)}"
            )
        if subcmd == "graph":
            html = generate_html_graph(graph)
            out_file = (graph.bundle_root or Path(".okf")) / "viz.html"
            out_file.write_text(html, encoding="utf-8")
            return f"OK: Interactive graph rendered to {out_file}."

        return f"Unknown okf command: '{subcmd}'. Usage: /okf [status|search <query>|validate|graph]"

    api.register_command(
        "okf",
        description="Manage and query Open Knowledge Format bundle",
        handler=okf_command,
    )
