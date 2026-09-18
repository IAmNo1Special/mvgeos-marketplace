"""Prompt generation and in-place context transformation for OKF knowledge catalog."""

from __future__ import annotations

import re
from typing import Any, cast

from mvgeos_runes_okf_bridge.graph import KnowledgeGraph
from mvgeos_runes_okf_bridge.types import TrustTier

_CATALOG_BLOCK_RE = re.compile(r"<knowledge_catalog.*?</knowledge_catalog>", re.DOTALL)


def render_knowledge_catalog(graph: KnowledgeGraph) -> str:
    """Render a compact <knowledge_catalog> XML block.

    Returns an empty string if no concepts are available (silent zero overhead).
    """
    if not graph.concepts:
        return ""

    bundle_path_str = graph.bundle_root.as_posix() if graph.bundle_root else ".okf/"
    lines: list[str] = [f'<knowledge_catalog path="{bundle_path_str}">']

    # Summary header
    trust = graph.trust_summary()
    stale = graph.stale_count()
    lines.append(
        f'  <summary total_concepts="{len(graph.concepts)}" '
        f'human_reviewed="{trust[TrustTier.HUMAN_REVIEWED.value]}" '
        f'machine_confirmed="{trust[TrustTier.MACHINE_CONFIRMED.value]}" '
        f'unverified="{trust[TrustTier.UNVERIFIED.value]}" '
        f'stale="{stale}" />'
    )

    # Concepts listing
    lines.append("  <concepts>")
    for cid, c in sorted(graph.concepts.items()):
        title_attr = f' title="{c.title}"' if c.title else ""
        desc_attr = f' description="{c.description}"' if c.description else ""
        stale_attr = ' stale="true"' if c.is_stale else ""
        lines.append(
            f'    <concept id="{cid}" type="{c.type}" trust="{c.trust_tier.value}"{title_attr}{desc_attr}{stale_attr} />'
        )
    lines.append("  </concepts>")

    # Instructions for model
    lines.append("  <instructions>")
    lines.append(
        "    The project maintains an Open Knowledge Format (.okf/) knowledge base.\n"
        "    To inspect complete definitions, schemas, or relations for any concept, use the 'okf_get' spell.\n"
        "    To search concepts, use 'okf_search'."
    )
    lines.append("  </instructions>")
    lines.append("</knowledge_catalog>")

    return "\n".join(lines)


def update_invocations_with_catalog(
    invocations: list[Any], catalog_xml: str
) -> list[Any]:
    """In-place replacement of <knowledge_catalog> in invocation messages to prevent context accumulation."""
    if not invocations:
        return invocations

    result = list(invocations)

    # Look for system or user message containing catalog block
    replaced = False
    for i, inv in enumerate(result):
        text = ""
        if hasattr(inv, "text"):
            text = getattr(inv, "text", "") or ""
        elif isinstance(inv, dict) and "content" in inv:
            text = str(inv["content"])

        if _CATALOG_BLOCK_RE.search(text):
            if catalog_xml:
                new_text = _CATALOG_BLOCK_RE.sub(catalog_xml, text)
            else:
                new_text = _CATALOG_BLOCK_RE.sub("", text).strip()

            if hasattr(inv, "text"):
                from dataclasses import is_dataclass, replace

                if is_dataclass(inv):
                    result[i] = replace(cast(Any, inv), text=new_text)
                else:
                    inv.text = new_text
            elif isinstance(inv, dict):
                result[i] = dict(inv, content=new_text)
            replaced = True
            break

    # If not found and we have catalog_xml, append to the first system or user invocation
    if not replaced and catalog_xml:
        first = result[0]
        if hasattr(first, "text"):
            old_t = getattr(first, "text", "") or ""
            new_t = f"{old_t}\n\n{catalog_xml}".strip()
            from dataclasses import is_dataclass, replace

            if is_dataclass(first):
                result[0] = replace(cast(Any, first), text=new_t)
            else:
                first.text = new_t
        elif isinstance(first, dict) and "content" in first:
            old_c = str(first["content"])
            result[0] = dict(first, content=f"{old_c}\n\n{catalog_xml}".strip())

    return result
