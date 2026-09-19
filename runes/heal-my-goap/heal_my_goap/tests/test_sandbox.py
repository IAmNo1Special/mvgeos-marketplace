"""Tests for sandbox code execution and safety checks."""

from unittest.mock import MagicMock, patch

import pytest

from heal_my_goap.models import SandboxTimeoutError
from heal_my_goap.sandbox import SandboxExecutor, _sandbox_process_target


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
        "heal_my_goap.sandbox.multiprocessing.get_context",
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
