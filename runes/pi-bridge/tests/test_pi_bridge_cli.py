"""CLI tests for pi-bridge (typer CliRunner, no engine install needed for parse)."""

from __future__ import annotations

from pathlib import Path

from mvgeos_runes_pi_bridge.cli import app
from typer.testing import CliRunner

FIX = Path(__file__).parent / "fixtures"
V3 = FIX / "pi_v3_sample.jsonl"
runner = CliRunner()


def test_cli_dry_run():
    result = runner.invoke(app, [str(V3), "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "v3sess-001" in result.output
    assert "dry run" in result.output
    assert "message: 4" in result.output


def test_cli_missing_file():
    result = runner.invoke(app, ["/nope/missing.jsonl", "--dry-run"])
    assert result.exit_code == 1
    assert "ERROR" in result.output


def test_cli_bad_format(tmp_path):
    p = tmp_path / "bad.jsonl"
    p.write_text('{"hello": "world"}\n', encoding="utf-8")
    result = runner.invoke(app, [str(p), "--dry-run"])
    assert result.exit_code == 1
    assert "unsupported Pi session header" in result.output


def test_cli_full_import(tmp_path):
    tome_dir = tmp_path / "sessions"
    result = runner.invoke(
        app, [str(V3), "--tome-dir", str(tome_dir), "--tome-id", "cli-test"]
    )
    assert result.exit_code == 0, result.output
    assert (tome_dir / "cli-test.jsonl").is_file()
    assert "mvgeos --resume" in result.output
