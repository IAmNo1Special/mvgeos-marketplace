from __future__ import annotations
import re as _re
from typing import Any
from pathlib import Path

from mvgeos_core.spells import MvgeSpell, SpellExecutionMode
from mvgeos_provider.registry import RealmRegistry

from .router import DCIRouter, SpellFileMatch, SpellSearchError
from .nlt_selector import NLTSelector
from .lazy_loader import LazySpellRegistry


class ToolSearchSpell(MvgeSpell):
    """Subclass MvgeSpell to provide custom execute()."""

    def __init__(
        self,
        provider_registry: RealmRegistry,
        spells_root: Path | None = None,
        rg_timeout: int = 10,
        nlt_model: str = "openrouter/free",
        nlt_api_key: str = "",
        agent_name: str | None = None,
        rune_api: Any | None = None,
    ) -> None:
        super().__init__(
            name="tool_search",
            description="Search for spells by describing what you need",
            parameters={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "description": "What you want to do",
                    },
                    "target": {"type": "string", "description": "Target subject"},
                    "grimoire_hint": {"type": "string", "description": "Domain hint"},
                    "max_results": {"type": "integer", "default": 5, "minimum": 1},
                },
                "required": ["operation"],
            },
            execution_mode=SpellExecutionMode.SEQUENTIAL,
        )
        self._provider_registry = provider_registry
        self._spells_root = spells_root or Path(".agents/.mvgeos/spells")
        self._rg_timeout = rg_timeout
        self._nlt_model = nlt_model
        self._nlt_api_key = nlt_api_key
        self._agent_name = agent_name
        self._rune_api = rune_api
        self._spell_registry = LazySpellRegistry()

    async def execute(
        self,
        spell_cast_id: str,
        params: dict[str, Any],
        signal: Any | None = None,
        on_update: Any | None = None,
    ) -> dict[str, Any]:
        max_results = params.get("max_results", 5)

        # Stage 1: DCI router
        router = DCIRouter(
            spells_root=self._spells_root,
            rg_timeout=self._rg_timeout,
        )
        try:
            matches = await router.route(params)
        except SpellSearchError as e:
            return {"spells_found": 0, "results": [], "error": str(e)}

        if not matches:
            return {"spells_found": 0, "results": [], "error": None}

        # Exact match fast path: single match where query normalises into filename stem
        operation = params.get("operation", "")
        if len(matches) == 1 and operation and _is_stem_match(operation, matches[0]):
            selected = [matches[0]]
        else:
            # Stage 2: NLT selection â€” returns file matches, not MvgeSpell objects
            selector = NLTSelector(
                self._provider_registry,
                model_id=self._nlt_model,
                api_key=self._nlt_api_key,
            )
            try:
                selected = await selector.select(params, matches)
            except SpellSearchError as e:
                return {"spells_found": 0, "results": [], "error": str(e)}

        if not selected:
            return {"spells_found": 0, "results": [], "error": None}

        # Trim before lazy load to avoid pointless schema imports
        selected = selected[:max_results]

        # Stage 3: Lazy schema load â€” load full JSON from source files
        try:
            results = await self._spell_registry.load_selected(selected)
        except Exception as e:
            return {
                "spells_found": 0,
                "results": [],
                "error": f"schema load failed: {e}",
            }

        return {"spells_found": len(results), "results": results, "error": None}


def _is_stem_match(query: str, match: SpellFileMatch) -> bool:
    """True if the query normalises into the file stem.
    Handles multi-word queries: normalises both query and stem by replacing
    spaces/underscores/hyphens with a single space, then checks containment
    with word boundaries. Applies Unicode NFKC normalization to both sides.
    """
    import unicodedata

    stem = unicodedata.normalize("NFKC", match.source_path.stem.lower())
    q = unicodedata.normalize("NFKC", query.lower().strip())
    if not q:
        return False
    stem_normalised = _re.sub(r"[_\s-]+", " ", stem)
    q_normalised = _re.sub(r"[_\s-]+", " ", q)
    if stem_normalised == q_normalised:
        return True
    for token in q_normalised.split():
        if not _re.search(rf"\b{_re.escape(token)}\b", stem_normalised):
            return False
    return True
