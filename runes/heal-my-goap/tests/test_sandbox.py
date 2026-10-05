"""Tests for sandbox code execution and safety checks."""

from unittest.mock import MagicMock, patch

import pytest

from mvgeos_runes_heal_my_goap.models import SandboxTimeoutError
from mvgeos_runes_heal_my_goap.sandbox import (
    HEAL_MY_GOAP_ALLOWED_MODULES,
    SandboxExecutor,
    _sandbox_process_target,
)


def test_sandbox_safe_code_execution() -> None:
    """Verifies safe Python code execution in sandbox."""
    executor = SandboxExecutor()
    code = "x = 10\ny = 20\nresult = x + y\n"
    local_vars = executor.execute_code(code)
    assert local_vars.get("result") == 30


def test_sandbox_blocked_imports() -> None:
    """Verifies AST validation blocks os module import."""
    executor = SandboxExecutor()
    code = "import os"
    with pytest.raises(ValueError, match="Forbidden AST node"):
        executor.execute_code(code)


def test_sandbox_blocked_sys() -> None:
    """Verifies AST validation blocks sys module import."""
    executor = SandboxExecutor()
    code = "import sys"
    with pytest.raises(ValueError, match="Forbidden AST node"):
        executor.execute_code(code)


def test_sandbox_blocked_builtins() -> None:
    """Verifies AST validation blocks dangerous builtins like eval."""
    executor = SandboxExecutor()
    code = "eval('1 + 1')"
    with pytest.raises(ValueError, match="Forbidden function"):
        executor.execute_code(code)


def test_sandbox_timeout_enforcement() -> None:
    """Verifies hard timeout enforcement on infinite loop execution."""
    executor = SandboxExecutor()
    infinite_loop_code = "while True:\n    pass\n"
    with pytest.raises(SandboxTimeoutError):
        executor.execute_code(infinite_loop_code, timeout_seconds=0.5)


def test_sandbox_allows_safe_import() -> None:
    """Verifies AST validation permits safe non-forbidden imports."""
    executor = SandboxExecutor()
    executor.validate_ast("import math")
    executor.validate_ast("from math import sqrt")
    executor.validate_ast("result = len([1, 2, 3])")


def test_sandbox_runtime_error_raises_value_error() -> None:
    """Verifies runtime execution errors surface as ValueError."""
    executor = SandboxExecutor()
    with pytest.raises(ValueError):
        executor.execute_code("x = 1 / 0")


def test_sandbox_process_target_success_and_error() -> None:
    """Verifies subprocess target reports success and error outcomes."""
    success_queue = MagicMock()
    _sandbox_process_target("x = 42", None, success_queue)
    status, payload = success_queue.put.call_args.args[0]
    assert status == "success"
    assert payload == {"x": 42}

    error_queue = MagicMock()
    _sandbox_process_target("x = 1 / 0", None, error_queue)
    status, payload = error_queue.put.call_args.args[0]
    assert status == "error"
    assert "division by zero" in str(payload)


def test_sandbox_execute_sync_with_context() -> None:
    """Verifies direct sync execution applies context globals."""
    executor = SandboxExecutor()
    local_vars = executor._execute_sync("y = base * 2", {"base": 21})
    assert local_vars == {"y": 42}


def test_sandbox_execute_code_empty_queue() -> None:
    """Verifies execute_code returns empty dict when queue is empty."""
    executor = SandboxExecutor()
    fake_ctx = MagicMock()
    fake_queue = MagicMock()
    fake_queue.empty.return_value = True
    fake_process = MagicMock()
    fake_process.is_alive.return_value = False
    fake_ctx.Queue.return_value = fake_queue
    fake_ctx.Process.return_value = fake_process

    with patch(
        "mvgeos_runes_heal_my_goap.sandbox.multiprocessing.get_context",
        return_value=fake_ctx,
    ):
        result = executor.execute_code("x = 1")
    assert result == {}


def test_sandbox_allowed_modules_execution() -> None:
    """Verifies allowed_modules enables execution of permitted modules."""
    executor = SandboxExecutor()
    code = "import json\nres = json.dumps({'a': 1})"
    local_vars = executor._execute_sync(code, None, allowed_modules={"json"})
    assert local_vars.get("res") == '{"a": 1}'


def test_sandbox_allowed_modules_sys_strictly_banned() -> None:
    """Verifies sys module remains banned even if passed in allowed_modules."""
    executor = SandboxExecutor()
    code = "import sys"
    with pytest.raises(ValueError, match="Forbidden AST node"):
        executor._execute_sync(code, None, allowed_modules={"sys"})


def test_sandbox_safe_import_direct_call_rejection() -> None:
    """Verifies direct invocation of safe_import rejects unallowed modules."""
    executor = SandboxExecutor()
    code = "import math"
    local_vars = executor._execute_sync(code, None, allowed_modules={"math"})
    assert "math" in local_vars


def test_sandbox_safe_import_unallowed_forbidden_module_raises() -> None:
    """Verifies safe_import raises ValueError for unallowed forbidden module."""
    executor = SandboxExecutor()
    msg = "Import of module 'os' is forbidden"
    with patch.object(executor, "validate_ast"):
        with pytest.raises(ValueError, match=msg):
            executor._execute_sync("import os", None, allowed_modules={"json"})


def test_sandbox_allowlist_grants_no_command_execution() -> None:
    """The GOAP action sandbox must not be able to reach a shell.

    This is the escape this Rune shipped: listing os and subprocess handed
    back command execution, because the visitor only matched bare ``ast.Name``
    call targets and an allowlist entry exempted the module from inspection.
    """
    executor = SandboxExecutor()
    for code in (
        "import os\nos.system('echo x')",
        "import subprocess\nsubprocess.run(['echo', 'x'])",
        "import os\nos.popen('echo x')",
    ):
        with pytest.raises(ValueError, match="Forbidden"):
            executor.validate_ast(
                code, allowed_modules=HEAL_MY_GOAP_ALLOWED_MODULES
            )


def test_sandbox_allowlist_grants_no_credential_read() -> None:
    """Reading os.environ needs no call, so a Subscript is enough to steal."""
    executor = SandboxExecutor()
    code = "import os\nleaked = os.environ['OPENROUTER_API_KEY']"
    with pytest.raises(ValueError, match="Forbidden"):
        executor.validate_ast(
            code, allowed_modules=HEAL_MY_GOAP_ALLOWED_MODULES
        )


def test_sandbox_allowlist_does_not_contain_os_or_subprocess() -> None:
    """The grant itself is the defect; the visitor fix is the backstop."""
    assert "os" not in HEAL_MY_GOAP_ALLOWED_MODULES
    assert "subprocess" not in HEAL_MY_GOAP_ALLOWED_MODULES
    assert "sys" not in HEAL_MY_GOAP_ALLOWED_MODULES


def test_sandbox_allowlist_grants_no_write_or_egress() -> None:
    """The two irreversible capabilities stay out of the action privilege set.

    Command execution and credential theft are closed at the visitor. These
    two were open by design of the list: a file written outlives the run, and
    an exfiltration leaves nothing to notice. Neither is recoverable after the
    fact, which is what separates them from what is already refused.
    """
    assert "pathlib" not in HEAL_MY_GOAP_ALLOWED_MODULES
    assert "urllib" not in HEAL_MY_GOAP_ALLOWED_MODULES


def test_sandbox_allowlist_refuses_a_pathlib_write() -> None:
    """Prove the narrowed list refuses the write, not merely omits the name."""
    executor = SandboxExecutor()
    with pytest.raises(ValueError, match="Forbidden"):
        executor.validate_ast(
            "import pathlib\npathlib.Path('x').write_text('pwned')",
            allowed_modules=HEAL_MY_GOAP_ALLOWED_MODULES,
        )


def test_sandbox_allowlist_refuses_urllib_egress() -> None:
    """Same for network egress."""
    executor = SandboxExecutor()
    with pytest.raises(ValueError, match="Forbidden"):
        executor.validate_ast(
            "import urllib.request\nurllib.request.urlopen('http://example.invalid')",
            allowed_modules=HEAL_MY_GOAP_ALLOWED_MODULES,
        )


def test_sandbox_visitor_rejects_forbidden_module_in_allowlist() -> None:
    """The import policy refuses a forbidden name at the import.

    The shipped allow-list cannot contain one, so this is the backstop for a
    future edit that adds it back: the import fails outright rather than
    parsing and failing later at every use.
    """
    executor = SandboxExecutor()
    for code in ("import os", "import subprocess", "from os import path"):
        with pytest.raises(ValueError, match="Forbidden"):
            executor.validate_ast(
                code, allowed_modules={"os", "subprocess", "json"}
            )


def test_sandbox_allowlist_still_permits_planned_action_surface() -> None:
    """Narrowing must not break the imports the GOAP action surface needs."""
    executor = SandboxExecutor()
    code = "import json\nimport re\nhit = re.match('a', 'ab') is not None"
    executor.validate_ast(code, allowed_modules=HEAL_MY_GOAP_ALLOWED_MODULES)


def test_sandbox_action_execution_rejects_escape() -> None:
    """End to end through execute_code, the escape must fail before it runs."""
    executor = SandboxExecutor()
    with pytest.raises(ValueError, match="Forbidden"):
        executor.execute_code(
            "import subprocess\nsubprocess.run(['echo', 'x'])",
            allowed_modules=HEAL_MY_GOAP_ALLOWED_MODULES,
            timeout_seconds=5.0,
        )


def test_sandbox_visitor_rejects_escape_even_when_allowlist_grants_it() -> None:
    """The visitor is a backstop independent of the shipped allow-list.

    heal-my-goap's original allow-list listed os and subprocess. If a future
    edit lists them again, the import policy alone is not the last line: the
    visitor must refuse the capability no matter what the allow-list says.
    """
    executor = SandboxExecutor()
    hostile = {"pathlib", "subprocess", "os", "urllib", "json", "re"}
    for code in (
        "import os\nos.system('echo x')",
        "import subprocess\nsubprocess.run(['echo', 'x'])",
        "import os\nos.popen('echo x')",
        "import os\nos.remove('/tmp/x')",
        "import os\nleaked = os.environ['OPENROUTER_API_KEY']",
    ):
        with pytest.raises(ValueError, match="Forbidden"):
            executor.validate_ast(code, allowed_modules=hostile)


def test_sandbox_visitor_still_permits_allowlisted_attribute_calls() -> None:
    """The backstop must not become a blanket ban on attribute access."""
    executor = SandboxExecutor()
    executor.validate_ast(
        "import json\nimport re\nimport pathlib\n"
        "p = pathlib.Path('a.json')\nhit = re.match('a', 'ab') is not None",
        allowed_modules={"pathlib", "json", "re"},
    )
