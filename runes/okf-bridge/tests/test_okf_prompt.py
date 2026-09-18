"""Unit tests for OKF prompt injection and in-place context transformation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mvgeos_runes_okf_bridge.graph import KnowledgeGraph
from mvgeos_runes_okf_bridge.prompt import (
    render_knowledge_catalog,
    update_invocations_with_catalog,
)


@dataclass
class DummyInvocation:
    text: str


def test_render_knowledge_catalog_empty() -> None:
    graph = KnowledgeGraph()
    xml = render_knowledge_catalog(graph)
    assert xml == ""


def test_render_knowledge_catalog_with_concepts(tmp_path: Path) -> None:
    okf = tmp_path / ".okf"
    okf.mkdir()
    (okf / "c1.md").write_text(
        "---\ntype: Service\ntitle: Auth Service\ndescription: Authentication API\n---\nBody",
        encoding="utf-8",
    )

    graph = KnowledgeGraph.load(cwd=tmp_path)
    xml = render_knowledge_catalog(graph)
    assert "<knowledge_catalog" in xml
    assert 'id="c1"' in xml
    assert 'type="Service"' in xml
    assert "Auth Service" in xml
    assert "okf_get" in xml
    assert "</knowledge_catalog>" in xml


def test_update_invocations_with_catalog_append_and_replace() -> None:
    invs = [DummyInvocation(text="Initial system prompt")]

    # 1. Append when not present
    catalog_v1 = "<knowledge_catalog>V1</knowledge_catalog>"
    updated = update_invocations_with_catalog(invs, catalog_v1)
    assert len(updated) == 1
    assert (
        "Initial system prompt\n\n<knowledge_catalog>V1</knowledge_catalog>"
        == updated[0].text
    )

    # 2. In-place replace on next turn
    catalog_v2 = "<knowledge_catalog>V2</knowledge_catalog>"
    updated_v2 = update_invocations_with_catalog(updated, catalog_v2)
    assert len(updated_v2) == 1
    assert (
        "Initial system prompt\n\n<knowledge_catalog>V2</knowledge_catalog>"
        == updated_v2[0].text
    )
    assert "V1" not in updated_v2[0].text

    # 3. Empty catalog_xml removes catalog block
    cleared = update_invocations_with_catalog(updated_v2, "")
    assert len(cleared) == 1
    assert cleared[0].text == "Initial system prompt"

    # 4. Dict invocations
    dict_invs = [{"role": "system", "content": "System message"}]
    dict_updated = update_invocations_with_catalog(
        dict_invs, "<knowledge_catalog>Test</knowledge_catalog>"
    )
    assert (
        "System message\n\n<knowledge_catalog>Test</knowledge_catalog>"
        in dict_updated[0]["content"]
    )

    dict_replaced = update_invocations_with_catalog(
        dict_updated, "<knowledge_catalog>New</knowledge_catalog>"
    )
    assert (
        "System message\n\n<knowledge_catalog>New</knowledge_catalog>"
        in dict_replaced[0]["content"]
    )

    # 5. Empty invocations
    assert update_invocations_with_catalog([], "test") == []
