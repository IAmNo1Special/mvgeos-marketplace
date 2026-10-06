"""The GOAP action surface may not reach the host.

This suite tests one thing: what an LLM-synthesised action can do when it runs.
The executor itself is the engine's, and the engine tests it -- see
``mvgeos-agent/tests/unit/sandbox.py`` for the AST visitor, the import policy
and the subprocess isolation. Re-testing those here is what let a vendored copy
drift once and need the same security fix twice.

What belongs to this Rune is the privilege set: ``HEAL_MY_GOAP_ALLOWED_MODULES``
is the whole capability surface of code a model wrote this run, so its contents
are a policy decision and are pinned here. See ADR 0015.
"""

import pytest
from mvgeos_core.sandbox import MvgeSandbox

from mvgeos_runes_heal_my_goap.engine import GoapEngine
from mvgeos_runes_heal_my_goap.sandbox import HEAL_MY_GOAP_ALLOWED_MODULES


def _executor() -> MvgeSandbox:
    """The executor ``GoapEngine`` uses when the host injects none."""
    return MvgeSandbox()


def test_allowlist_grants_no_command_execution() -> None:
    """``os`` and ``subprocess`` must never reappear in the privilege set.

    They were listed once, and with the visitor inspecting only bare
    ``ast.Name`` call targets that granted command execution outright. The
    engine refuses them now regardless; this pins the ask as well as the grant.
    """
    assert "os" not in HEAL_MY_GOAP_ALLOWED_MODULES
    assert "subprocess" not in HEAL_MY_GOAP_ALLOWED_MODULES
    assert "sys" not in HEAL_MY_GOAP_ALLOWED_MODULES


def test_allowlist_grants_no_write_or_egress() -> None:
    """The two irreversible capabilities stay out.

    Command execution and credential theft fail loudly inside the run. A file
    written outlives it, and an exfiltration leaves nothing to notice, so
    neither is recoverable afterwards. That asymmetry is why these two were
    removed as policy while the others were removed as a defect.
    """
    assert "pathlib" not in HEAL_MY_GOAP_ALLOWED_MODULES
    assert "urllib" not in HEAL_MY_GOAP_ALLOWED_MODULES


def test_allowlist_refuses_a_pathlib_write() -> None:
    """Prove the refusal by execution, not by inspecting the constant."""
    with pytest.raises(ValueError, match="Forbidden"):
        _executor().execute_code(
            "import pathlib\npathlib.Path('x').write_text('pwned')",
            allowed_modules=set(HEAL_MY_GOAP_ALLOWED_MODULES),
            timeout_seconds=5.0,
        )


def test_allowlist_refuses_urllib_egress() -> None:
    """Same for network egress."""
    with pytest.raises(ValueError, match="Forbidden"):
        _executor().execute_code(
            "import urllib.request\n"
            "urllib.request.urlopen('http://example.invalid')",
            allowed_modules=set(HEAL_MY_GOAP_ALLOWED_MODULES),
            timeout_seconds=5.0,
        )


def test_allowlist_refuses_credential_read() -> None:
    """Reading os.environ needs no call, so a Subscript is enough to steal."""
    with pytest.raises(ValueError, match="Forbidden"):
        _executor().execute_code(
            "import os\nleaked = os.environ['OPENROUTER_API_KEY']",
            allowed_modules=set(HEAL_MY_GOAP_ALLOWED_MODULES),
            timeout_seconds=5.0,
        )


def test_allowlist_still_permits_the_planned_action_surface() -> None:
    """Narrowing must not break what an action actually needs: parse, match."""
    result = _executor().execute_code(
        "import json\nimport re\n"
        "out = json.dumps({'hit': re.match('a', 'ab') is not None})",
        allowed_modules=set(HEAL_MY_GOAP_ALLOWED_MODULES),
        timeout_seconds=10.0,
    )
    assert result["out"] == '{"hit": true}'


def test_visitor_refuses_escape_even_when_allowlist_grants_it() -> None:
    """The backstop for a future edit that adds a forbidden name back.

    If the privilege set is widened by mistake, the import policy alone is not
    the last line: every capability must still be refused at use.
    """
    hostile = {"pathlib", "subprocess", "os", "urllib", "json", "re"}
    for code in (
        "import os\nos.system('echo x')",
        "import subprocess\nsubprocess.run(['echo', 'x'])",
        "import os\nos.popen('echo x')",
        "import os\nos.remove('/tmp/x')",
        "import os\nleaked = os.environ['OPENROUTER_API_KEY']",
    ):
        with pytest.raises(ValueError, match="Forbidden"):
            _executor().validate_ast(code, allowed_modules=hostile)


def test_import_policy_refuses_forbidden_name_in_allowlist() -> None:
    """A forbidden name is refused at the import, not tolerated until use."""
    for code in ("import os", "import subprocess", "from os import path"):
        with pytest.raises(ValueError, match="Forbidden"):
            _executor().validate_ast(code, allowed_modules={"os", "subprocess"})


def test_engine_defaults_to_the_engine_executor() -> None:
    """No second implementation may reappear behind this default.

    The Rune used to vendor its own copy of the visitor, the import policy and
    the isolation. It drifted once. The default must be the engine's, so the
    standalone path cannot fall behind the hosted one.
    """
    assert isinstance(GoapEngine().sandbox, MvgeSandbox)


def test_engine_accepts_an_injected_executor() -> None:
    """The seam is the protocol, so a caller may supply its own."""
    injected = MvgeSandbox()
    assert GoapEngine(sandbox=injected).sandbox is injected
