from __future__ import annotations
from pathlib import Path
from typing import Any

from mvgeos_core.spells import MvgeSpell, SpellExecutionMode
from mvgeos_provider.registry import RealmRegistry

from .dci_matcher import (
    DCISkillMatcher,
    SkillFile,
    SkillSearchError,
    _DEFAULT_SKILL_DIRS,
    _get_skill_roots,
)
from .skill_selector import SkillNLTSelector


class SkillSearchSpell(MvgeSpell):
    """
    Subclass MvgeSpell to discover skill .md files by query.
    Uses DCI (rg) + NLT selection, no embeddings, no YAML frontmatter.
    """

    def __init__(
        self,
        provider_registry: RealmRegistry,
        skill_dirs: list[Path] | None = None,
        rg_timeout: int = 15,
        nlt_model: str = "openrouter/free",
        nlt_api_key: str = "",
        agent_name: str | None = None,
    ) -> None:
        super().__init__(
            name="skill_search",
            description="Search for skills matching a task description",
            parameters={
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "What the user is trying to do",
                    },
                    "domain": {"type": "string", "description": "Domain hint"},
                    "max_results": {"type": "integer", "default": 3},
                },
                "required": ["task"],
            },
            execution_mode=SpellExecutionMode.SEQUENTIAL,
        )
        self._provider_registry = provider_registry
        self._skill_dirs = [p.resolve() for p in (skill_dirs or _DEFAULT_SKILL_DIRS)]
        self._rg_timeout = rg_timeout
        self._nlt_model = nlt_model
        self._nlt_api_key = nlt_api_key
        self._agent_name = agent_name

    async def execute(
        self,
        spell_cast_id: str,
        params: dict[str, Any],
        signal: Any | None = None,
        on_update: Any | None = None,
    ) -> dict[str, Any]:
        task = params.get("task", "")
        if not task:
            return {"skills_found": 0, "skills": [], "error": "empty task query"}
        try:
            max_results = max(1, int(params.get("max_results", 3)))
        except (ValueError, TypeError):
            max_results = 3

        matcher = DCISkillMatcher(
            skill_dirs=self._skill_dirs,
            rg_timeout=self._rg_timeout,
        )
        skill_dirs_available = matcher.discover_skill_dirs()

        try:
            candidates = await matcher.match_all(skill_dirs_available, task)
        except SkillSearchError as e:
            return {"skills_found": 0, "skills": [], "error": str(e)}

        if not candidates:
            return {"skills_found": 0, "skills": [], "error": None}

        selector = SkillNLTSelector(
            registry=self._provider_registry,
            model_id=self._nlt_model,
            api_key=self._nlt_api_key,
        )
        try:
            selected = await selector.select(task, candidates, max_results)
        except SkillSearchError as e:
            return {"skills_found": 0, "skills": [], "error": str(e)}

        return {
            "skills_found": len(selected),
            "skills": [s.to_dict() for s in selected],
            "error": None,
        }
