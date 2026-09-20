"""Shared fixtures for heal-my-goap tests."""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def _clean_proxy_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip proxy env vars for every test.

    A bare IPv6 no_proxy entry (e.g. fd8b:...::1 without brackets) makes
    httpx raise InvalidURL at client construction, which has nothing to do
    with the code under test. Test-only hardening; production code untouched.
    """
    for var in list(os.environ):
        if var.lower().endswith("_proxy"):
            monkeypatch.delenv(var, raising=False)
