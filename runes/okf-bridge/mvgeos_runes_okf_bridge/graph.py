"""In-memory Directed Acyclic Graph (DAG) for OKF concepts and backlinks."""

from __future__ import annotations

import os
from collections import defaultdict
from pathlib import Path

from mvgeos_runes_okf_bridge.parser import parse_concept_file
from mvgeos_runes_okf_bridge.types import Concept, TrustTier

RESERVED_FILENAMES = {"index.md", "log.md"}


class KnowledgeGraph:
    """Represents a connected knowledge bundle with concept nodes and link edges."""

    def __init__(self, bundle_root: Path | None = None) -> None:
        self.bundle_root = bundle_root
        self.concepts: dict[str, Concept] = {}
        self._backlinks: dict[str, set[str]] = defaultdict(set)

    @classmethod
    def load(
        cls,
        cwd: Path | None = None,
        bundle_path: Path | None = None,
    ) -> KnowledgeGraph:
        """Discover and load an OKF bundle.

        Discovery order:
        1. Explicit bundle_path
        2. Workspace `<cwd>/.okf/` (canonical location)
        3. Standalone knowledge repository (`<cwd>/` if root contains `index.md` or concept files)

        If bundle directory is missing or empty, returns an empty KnowledgeGraph.
        """
        target_dir = bundle_path
        if target_dir is None and cwd is not None:
            okf_dir = cwd / ".okf"
            if okf_dir.is_dir():
                target_dir = okf_dir
            elif (cwd / "index.md").is_file():
                # Standalone knowledge repository
                target_dir = cwd

        if target_dir is None or not target_dir.is_dir():
            return cls(bundle_root=None)

        graph = cls(bundle_root=target_dir)
        graph.scan_and_index()
        return graph

    def scan_and_index(self) -> None:
        """Scan the bundle directory and index all concept files."""
        if self.bundle_root is None or not self.bundle_root.is_dir():
            return

        for root, _dirs, files in os.walk(self.bundle_root):
            root_path = Path(root)
            for f in files:
                if not f.endswith(".md") or f in RESERVED_FILENAMES:
                    continue

                full_path = root_path / f
                concept, _err = parse_concept_file(full_path, self.bundle_root)
                if concept is not None:
                    self.concepts[concept.id] = concept

        # Compute backlinks
        self._backlinks.clear()
        for cid, concept in self.concepts.items():
            for target in concept.links:
                self._backlinks[target].add(cid)
            # Internal sources also act as edges
            for s in concept.sources:
                res = s.resource.split("#")[0].split("?")[0].lstrip("/")
                res = res.removesuffix(".md")
                if res in self.concepts and res != cid:
                    self._backlinks[res].add(cid)

    def get(self, concept_id: str) -> Concept | None:
        """Retrieve a concept by ID."""
        clean_id = concept_id.removesuffix(".md").lstrip("/")
        return self.concepts.get(clean_id)

    def links_to(self, concept_id: str) -> list[str]:
        """List concept IDs linked by the given concept."""
        concept = self.get(concept_id)
        return list(concept.links) if concept else []

    def cited_by(self, concept_id: str) -> list[str]:
        """List concept IDs that cite or link to the given concept."""
        clean_id = concept_id.removesuffix(".md").lstrip("/")
        return sorted(self._backlinks.get(clean_id, set()))

    def search(
        self,
        query: str = "",
        type_filter: str | None = None,
        tag_filter: str | None = None,
    ) -> list[Concept]:
        """Search concepts matching query string, type, or tags."""
        q = query.lower().strip()
        results: list[tuple[int, Concept]] = []

        for concept in self.concepts.values():
            if type_filter and concept.type.lower() != type_filter.lower():
                continue
            if tag_filter and tag_filter.lower() not in [
                t.lower() for t in concept.tags
            ]:
                continue

            if not q:
                results.append((0, concept))
                continue

            score = 0
            if q in concept.id.lower():
                score += 10
            if q in concept.title.lower():
                score += 8
            if any(q in t.lower() for t in concept.tags):
                score += 5
            if q in concept.description.lower():
                score += 3
            if q in concept.body.lower():
                score += 1

            if score > 0:
                results.append((score, concept))

        results.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in results]

    def types_summary(self) -> dict[str, int]:
        """Return counts of concepts grouped by type."""
        summary: dict[str, int] = defaultdict(int)
        for c in self.concepts.values():
            summary[c.type] += 1
        return dict(summary)

    def trust_summary(self) -> dict[str, int]:
        """Return counts of concepts grouped by trust tier."""
        summary = {
            TrustTier.UNVERIFIED.value: 0,
            TrustTier.MACHINE_CONFIRMED.value: 0,
            TrustTier.HUMAN_REVIEWED.value: 0,
        }
        for c in self.concepts.values():
            summary[c.trust_tier.value] += 1
        return summary

    def stale_count(self) -> int:
        """Count how many concepts are past their stale_after date."""
        return sum(1 for c in self.concepts.values() if c.is_stale)
