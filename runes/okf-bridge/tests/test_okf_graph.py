"""Unit tests for OKF KnowledgeGraph and backlink indexing."""

from __future__ import annotations

from pathlib import Path

from mvgeos_runes_okf_bridge.graph import KnowledgeGraph


def test_knowledge_graph_empty(tmp_path: Path) -> None:
    graph = KnowledgeGraph.load(cwd=tmp_path)
    assert len(graph.concepts) == 0
    assert graph.bundle_root is None
    assert graph.search("anything") == []
    assert graph.trust_summary()["human-reviewed"] == 0


def test_knowledge_graph_scan_and_backlinks(tmp_path: Path) -> None:
    okf_dir = tmp_path / ".okf"
    okf_dir.mkdir()

    # Concept A
    (okf_dir / "service-a.md").write_text(
        "---\n"
        "type: Service\n"
        "title: Service A\n"
        "tags: [core, api]\n"
        "verified:\n"
        "  - by: human:dan\n"
        "---\n"
        "Links to [Service B](/service-b.md).\n",
        encoding="utf-8",
    )

    # Concept B
    (okf_dir / "service-b.md").write_text(
        "---\n"
        "type: Service\n"
        "title: Service B\n"
        "tags: [storage]\n"
        "stale_after: '2020-01-01'\n"
        "verified:\n"
        "  - by: process:bot\n"
        "---\n"
        "Independent service.\n",
        encoding="utf-8",
    )

    # Reserved files should be ignored
    (okf_dir / "index.md").write_text("# Index\n", encoding="utf-8")
    (okf_dir / "log.md").write_text("# Log\n", encoding="utf-8")

    graph = KnowledgeGraph.load(cwd=tmp_path)
    assert len(graph.concepts) == 2
    assert "service-a" in graph.concepts
    assert "service-b" in graph.concepts

    # Backlinks
    assert graph.links_to("service-a") == ["service-b"]
    assert graph.cited_by("service-b") == ["service-a"]
    assert graph.cited_by("service-a") == []

    # Search
    results = graph.search(query="Service A")
    assert len(results) >= 1
    assert results[0].id == "service-a"

    # Search with filter
    storage_results = graph.search(query="", tag_filter="storage")
    assert len(storage_results) == 1
    assert storage_results[0].id == "service-b"

    # Summaries
    types = graph.types_summary()
    assert types["Service"] == 2

    trust = graph.trust_summary()
    assert trust["human-reviewed"] == 1
    assert trust["machine-confirmed"] == 1
    assert trust["unverified"] == 0

    assert graph.stale_count() == 1


def test_standalone_repo_discovery(tmp_path: Path) -> None:
    # Standalone bundle has root index.md
    (tmp_path / "index.md").write_text(
        '---\nokf_version: "0.2"\n---\n# Root\n', encoding="utf-8"
    )
    (tmp_path / "concept.md").write_text(
        "---\ntype: Guide\n---\nBody", encoding="utf-8"
    )

    graph = KnowledgeGraph.load(cwd=tmp_path)
    assert graph.bundle_root == tmp_path
    assert len(graph.concepts) == 1
