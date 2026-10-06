"""The sandbox seam ``GoapEngine`` depends on.

The executor itself is the engine's. ``MvgeOS host sandbox executor``
(``mvgeos_core.sandbox.MvgeSandbox``) owns the AST visitor, the import policy
and the subprocess isolation, and this Rune used to keep a near-duplicate of
all three.

That copy drifted once already. It carried the same permissive import rule
that let ``os.system`` and ``subprocess.run`` through an attribute, and had to
be given the identical fix. Two copies of a security control are one finding
and two fixes, so the copy is gone and only the seam it expressed remains:

``GoapEngine`` takes any executor satisfying this protocol, and the host
supplies the engine's through ``api.sandbox``. A standalone caller that
constructs ``GoapEngine()`` with no executor gets the engine's too, rather than
a second implementation that can fall behind.

Widen the privilege set in the engine, not here. See ADR 0015.
"""

from typing import Any, Protocol, runtime_checkable

#: Imports an LLM-synthesized GOAP action may reach.
#:
#: This list is a budget, not a wish list. Every entry is a capability handed
#: to code a model wrote this run, from a gap description the model itself
#: built out of world state it observed. Four entries have already been
#: removed as policy rather than as defect:
#:
#: - ``os`` and ``subprocess`` were listed, and with the visitor inspecting
#:   only bare ``ast.Name`` call targets that granted command execution
#:   outright.
#: - ``pathlib`` and ``urllib`` granted the two irreversible capabilities:
#:   a file written outlives the run, and an exfiltration leaves nothing to
#:   notice. Nothing shipped used either -- the synthesiser's own prompt asks
#:   the model for ``"code_payload": null``, so the executed-code path is the
#:   exception rather than the routine.
#:
#: What remains is pure computation: parse and match. If an action later needs
#: to read a file or reach a network, the answer is a host-mediated capability
#: with an audit record, not a standard-library import added here. Do not widen
#: this list without deciding what the action surface is allowed to do.
HEAL_MY_GOAP_ALLOWED_MODULES = frozenset(
    {
        "json",
        "re",
    }
)


@runtime_checkable
class BaseSandboxExecutor(Protocol):
    """Structural interface for code execution sandboxes."""

    def execute_code(
        self,
        code_str: str,
        context_globals: dict[str, Any] | None = None,
        timeout_seconds: float = 5.0,
        allowed_modules: set[str] | None = None,
    ) -> dict[str, Any]:
        """Safely executes Python code within sandbox isolation.

        Args:
            code_str: Python code string to execute.
            context_globals: Optional dict of global execution variables.
            timeout_seconds: Hard timeout in seconds.
            allowed_modules: Optional set of allowed module names. A forbidden
                module is refused even when listed.

        Returns:
            Dict containing local variables resulting from execution.

        Raises:
            SandboxTimeoutError: If execution exceeds timeout_seconds.
            ValueError: If code violates safety AST constraints or errors.
        """
        ...
