from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from mvgeos_core.spells import MvgeSpell, SpellExecutionMode
from mvgeos_provider.registry import RealmRegistry

from .dci_matcher import DCISkillMatcher, SkillSearchError, _get_skill_roots
from .skill_selector import SkillNLTSelector


class SkillExecuteSpell(MvgeSpell):
    """Execute a discovered skill's scripts."""

    def __init__(
        self,
        provider_registry: RealmRegistry,
        skill_dirs: list[Path] | None = None,
        agent_name: str | None = None,
        rg_timeout: int = 15,
        nlt_model: str = "openrouter/free",
        nlt_api_key: str = "",
    ) -> None:
        super().__init__(
            name="skill_execute",
            description="Execute a script from a discovered skill's scripts/ directory.",
            parameters={
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "Name or directory name of the skill",
                    },
                    "script": {
                        "type": "string",
                        "description": "Script filename under scripts/ to execute (e.g. 'helper.py')",
                    },
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional CLI arguments to pass to the script",
                    },
                },
                "required": ["skill_name", "script"],
            },
            execution_mode=SpellExecutionMode.SEQUENTIAL,
        )
        self._provider_registry = provider_registry
        self._skill_dirs = skill_dirs
        self._agent_name = agent_name
        self._rg_timeout = rg_timeout
        self._nlt_model = nlt_model
        self._nlt_api_key = nlt_api_key

    async def execute(
        self,
        spell_cast_id: str,
        params: dict[str, Any],
        signal: Any | None = None,
        on_update: Any | None = None,
    ) -> dict[str, Any]:
        skill_name = params.get("skill_name", "").strip()
        script = params.get("script", "").strip()
        args = params.get("args", [])
        if not skill_name or not script:
            return {"status": "error", "error": "skill_name and script are required"}

        roots = _get_skill_roots(self._skill_dirs)
        target_script: Path | None = None
        target_skill_dir: Path | None = None

        for root in roots:
            cand = root / skill_name
            if cand.is_dir():
                sfile = cand / "scripts" / script
                if sfile.is_file():
                    target_script = sfile
                    target_skill_dir = cand
                    break

        if not target_script or not target_skill_dir:
            return {
                "status": "error",
                "error": f"Script '{script}' not found in skill '{skill_name}/scripts'",
            }

        cmd: list[str]
        if target_script.suffix == ".py":
            cmd = [sys.executable, str(target_script)]
        elif target_script.suffix == ".sh":
            cmd = ["bash", str(target_script)]
        else:
            cmd = [str(target_script)]
        cmd.extend(str(a) for a in args)

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(target_skill_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=30.0)
            stdout = stdout_b.decode("utf-8", errors="replace")
            stderr = stderr_b.decode("utf-8", errors="replace")
            return {
                "status": "success" if proc.returncode == 0 else "failure",
                "exit_code": proc.returncode,
                "stdout": stdout,
                "stderr": stderr,
            }
        except TimeoutError:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            return {"status": "error", "error": "Execution timed out"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
