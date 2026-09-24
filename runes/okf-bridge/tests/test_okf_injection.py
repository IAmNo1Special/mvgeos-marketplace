"""Tests for budgeted working-concept injection.

Only concepts with explicit `context: auto` are injected (search-only and
missing-context concepts stay retrievable via concept_search). Injection is
capped at a token budget (default 2000), newest generated.at first, with a
description-only fallback when the full body no longer fits. Every injected
block carries its trust tier and stale state.
"""

from __future__ import annotations

from pathlib import Path

from mvgeos_runes_okf_bridge.graph import KnowledgeGraph
from mvgeos_runes_okf_bridge.prompt import estimate_tokens, render_working_concepts

CONCEPT_TMPL = """---
type: Note
title: {title}
description: {description}
context: {context}
{extra}
generated:
  by: human:tester
  at: '{at}'
---

{body}
"""


def _concept(
    root: Path,
    name: str,
    *,
    context: str = "auto",
    at: str = "2026-09-01",
    title: str | None = None,
    description: str = "A description.",
    body: str = "Body text.",
    extra: str = "",
) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / f"{name}.md").write_text(
        CONCEPT_TMPL.format(
            title=title or name,
            description=description,
            context=context,
            extra=extra,
            at=at,
            body=body,
        ),
        encoding="utf-8",
    )


def _load_single(tmp_path: Path) -> KnowledgeGraph:
    return KnowledgeGraph.load(bundle_path=tmp_path)


def test_empty_graph_renders_nothing(tmp_path: Path) -> None:
    assert render_working_concepts(_load_single(tmp_path)) == ""


def test_only_auto_context_is_injected(tmp_path: Path) -> None:
    _concept(tmp_path, "auto-note", context="auto")
    _concept(tmp_path, "search-note", context="search-only")
    xml = render_working_concepts(_load_single(tmp_path))
    assert 'id="auto-note"' in xml
    assert "search-note" not in xml


def test_missing_context_is_not_injected(tmp_path: Path) -> None:
    (tmp_path / "plain.md").write_text(
        "---\ntype: Note\ntitle: Plain\n---\nBody", encoding="utf-8"
    )
    xml = render_working_concepts(_load_single(tmp_path))
    assert xml == ""


def test_deprecated_concepts_are_not_injected(tmp_path: Path) -> None:
    _concept(tmp_path, "old-note", context="auto", extra="status: deprecated")
    xml = render_working_concepts(_load_single(tmp_path))
    assert xml == ""


def test_newest_generated_first(tmp_path: Path) -> None:
    _concept(tmp_path, "older", at="2026-01-01")
    _concept(tmp_path, "newer", at="2026-09-01")
    xml = render_working_concepts(_load_single(tmp_path))
    assert xml.index('id="newer"') < xml.index('id="older"')


def test_token_budget_is_respected(tmp_path: Path) -> None:
    big_body = "word " * 2000  # ~2000 tokens by the estimator
    for i in range(5):
        _concept(tmp_path, f"note-{i}", body=big_body)
    xml = render_working_concepts(_load_single(tmp_path), token_budget=2000)
    assert estimate_tokens(xml) <= 2000


def test_description_preferred_when_constrained(tmp_path: Path) -> None:
    big_body = "word " * 2000
    _concept(
        tmp_path,
        "big",
        body=big_body,
        description="Short desc.",
        at="2026-09-02",
    )
    _concept(tmp_path, "small", body="tiny body", at="2026-09-01")
    xml = render_working_concepts(_load_single(tmp_path), token_budget=2000)
    # big is newest so it is considered first; its body cannot fit, so the
    # description-only form is used and the concept is still present
    assert 'id="big"' in xml
    assert "Short desc." in xml
    assert "word word" not in xml
    assert 'id="small"' in xml
    assert estimate_tokens(xml) <= 2000


def test_trust_and_stale_annotations(tmp_path: Path) -> None:
    _concept(
        tmp_path,
        "trusted",
        extra="verified:\n  - by: human:malcom\n    at: '2026-09-01'",
    )
    _concept(tmp_path, "stale-one", extra="stale_after: '2020-01-01'")
    xml = render_working_concepts(_load_single(tmp_path))
    assert 'trust="human-reviewed"' in xml
    assert 'trust="unverified"' in xml
    assert 'stale="true"' in xml


def test_block_names_spells_for_model(tmp_path: Path) -> None:
    _concept(tmp_path, "note")
    xml = render_working_concepts(_load_single(tmp_path))
    assert "concept_search" in xml
    assert "concept_get" in xml
    assert "concept_write" in xml
    assert "<working_concepts" in xml
    assert "</working_concepts>" in xml
