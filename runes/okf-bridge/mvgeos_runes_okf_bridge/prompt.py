"""Budgeted working-concept injection for OKF knowledge.

Only concepts with explicit `context: auto` are injected; `search-only`
(and unset) concepts stay retrievable via the concept_search spell.
Injection is capped at WORKING_CONCEPTS_TOKEN_BUDGET tokens (default 2000):
newest generated.at first, full body preferred, description-only fallback
when the body no longer fits. The block is replaced in place each turn so
context never accumulates.
"""

from __future__ import annotations

import re
from typing import Any, cast
from xml.sax.saxutils import escape

from mvgeos_runes_okf_bridge.graph import KnowledgeGraph
from mvgeos_runes_okf_bridge.types import Concept, TrustTier

_BLOCK_RE = re.compile(r"<working_concepts.*?</working_concepts>", re.DOTALL)

# Default cap for auto-injected working concepts (Malcom's call, 2026-09-24).
WORKING_CONCEPTS_TOKEN_BUDGET = 2000


def estimate_tokens(text: str) -> int:
    """Rough token estimate (chars/4). Documented approximation, not a count."""
    return max(1, len(text) // 4)


def _attr(value: str) -> str:
    return escape(value, {'"': "&quot;"})


def _generated_at(concept: Concept) -> str:
    return str(concept.generated.get("at", ""))


def _render_concept_block(concept: Concept, *, full_body: bool) -> str:
    stale_attr = ' stale="true"' if concept.is_stale else ""
    lines = [
        (
            f'  <concept id="{_attr(concept.id)}" type="{_attr(concept.type)}" '
            f'trust="{concept.trust_tier.value}"{stale_attr}>'
        ),
        f"    <title>{escape(concept.title)}</title>",
        f"    <description>{escape(concept.description)}</description>",
    ]
    if full_body:
        lines.append(f"    <body>{escape(concept.body)}</body>")
    else:
        lines.append("    <body-truncated/>")
    lines.append("  </concept>")
    return "\n".join(lines)


def render_working_concepts(
    graph: KnowledgeGraph, token_budget: int = WORKING_CONCEPTS_TOKEN_BUDGET
) -> str:
    """Render a budgeted <working_concepts> XML block.

    Returns an empty string when no auto-injectable concepts exist
    (silent zero overhead).
    """
    candidates = [
        c
        for c in graph.concepts.values()
        if c.context == "auto" and c.status != "deprecated"
    ]
    if not candidates:
        return ""

    # Newest generated.at first; concepts without a stamp sort last.
    candidates.sort(key=_generated_at, reverse=True)

    header_open = "<working_concepts>"
    instructions = (
        "  <instructions>\n"
        "    Working concepts are auto-loaded project knowledge. "
        "Trust rises unverified < machine-confirmed < human-reviewed; "
        "stale concepts may be outdated.\n"
        "    Use 'concept_search' to find more concepts, 'concept_get' for full "
        "detail, and 'concept_write' to record durable knowledge "
        "(machine-written concepts are stamped with the writing actor and held "
        "at unverified trust until a human verifies them with 'concept_verify').\n"
        "  </instructions>"
    )
    overhead = estimate_tokens(f"{header_open}\n{instructions}\n</working_concepts>")

    included: list[tuple[Concept, bool]] = []
    used = overhead

    # Pass 1: full bodies, newest first, while they fit.
    deferred: list[Concept] = []
    for concept in candidates:
        block = _render_concept_block(concept, full_body=True)
        cost = estimate_tokens(block)
        if used + cost <= token_budget:
            included.append((concept, True))
            used += cost
        else:
            deferred.append(concept)

    # Pass 2: description-only for the rest, newest first, while they fit.
    for concept in deferred:
        block = _render_concept_block(concept, full_body=False)
        cost = estimate_tokens(block)
        if used + cost <= token_budget:
            included.append((concept, False))
            used += cost

    if not included:
        return ""

    trust = graph.trust_summary()
    lines = [
        (
            f'<working_concepts budget_tokens="{token_budget}" '
            f'used_tokens="{used}" total="{len(candidates)}" '
            f'human_reviewed="{trust[TrustTier.HUMAN_REVIEWED.value]}" '
            f'machine_confirmed="{trust[TrustTier.MACHINE_CONFIRMED.value]}" '
            f'unverified="{trust[TrustTier.UNVERIFIED.value]}">'
        )
    ]
    for concept, full_body in included:
        lines.append(_render_concept_block(concept, full_body=full_body))
    lines.append(instructions)
    lines.append("</working_concepts>")
    return "\n".join(lines)


def update_invocations_with_concepts(
    invocations: list[Any], block_xml: str
) -> list[Any]:
    """In-place replacement of <working_concepts> in invocation messages."""
    if not invocations:
        return invocations

    result = list(invocations)

    replaced = False
    for i, inv in enumerate(result):
        text = ""
        if hasattr(inv, "text"):
            text = getattr(inv, "text", "") or ""
        elif isinstance(inv, dict) and "content" in inv:
            text = str(inv["content"])

        if _BLOCK_RE.search(text):
            if block_xml:
                new_text = _BLOCK_RE.sub(block_xml, text)
            else:
                new_text = _BLOCK_RE.sub("", text).strip()

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

    if not replaced and block_xml:
        first = result[0]
        if hasattr(first, "text"):
            old_t = getattr(first, "text", "") or ""
            new_t = f"{old_t}\n\n{block_xml}".strip()
            from dataclasses import is_dataclass, replace

            if is_dataclass(first):
                result[0] = replace(cast(Any, first), text=new_t)
            else:
                first.text = new_t
        elif isinstance(first, dict) and "content" in first:
            old_c = str(first["content"])
            result[0] = dict(first, content=f"{old_c}\n\n{block_xml}".strip())

    return result
