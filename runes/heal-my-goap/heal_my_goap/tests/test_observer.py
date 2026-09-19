"""Tests for the observer module."""

from typing import Any

from heal_my_goap.models import WorldState
from heal_my_goap.observer import DeltaObserver


def test_compute_delta_int_float_bool_str_changes() -> None:
    """Verifies DeltaObserver detects int, float, bool, and str changes."""
    observer = DeltaObserver(ignored_keys=set(), numeric_tolerance=0.1)

    ws_before_kwargs: dict[str, Any] = {
        "files": 10,
        "temp": 98.6,
        "connected": False,
        "status": "idle",
    }
    ws_after_kwargs: dict[str, Any] = {
        "files": 0,
        "temp": 65.0,
        "connected": True,
        "status": "done",
    }
    before = WorldState(**ws_before_kwargs)
    after = WorldState(**ws_after_kwargs)

    delta = observer.compute_delta(before, after)
    assert delta == {
        "files": 0,
        "temp": 65.0,
        "connected": True,
        "status": "done",
    }


def test_compute_delta_filters_default_ignored_keys() -> None:
    """Verifies DeltaObserver ignores volatile default keys."""
    observer = DeltaObserver()

    before = {"uptime_minutes": 10.0, "ram_usage_pct": 50.0, "door_open": False}
    after = {"uptime_minutes": 12.0, "ram_usage_pct": 50.0, "door_open": True}

    delta = observer.compute_delta(before, after)
    assert delta == {"door_open": True}


def test_compute_delta_custom_ignored_keys() -> None:
    """Verifies DeltaObserver accepts custom ignored keys."""
    observer = DeltaObserver(ignored_keys={"custom_noise"})

    before = {"custom_noise": 100, "active": False}
    after = {"custom_noise": 200, "active": True}

    delta = observer.compute_delta(before, after)
    assert delta == {"active": True}


def test_compute_delta_numeric_tolerance() -> None:
    """Verifies DeltaObserver ignores changes below numeric_tolerance."""
    observer = DeltaObserver(ignored_keys=set(), numeric_tolerance=5.0)

    before = {"cpu_pct": 20.0, "ram_pct": 40.0}
    after = {"cpu_pct": 22.0, "ram_pct": 50.0}  # cpu changed by 2.0 (< 5.0)

    delta = observer.compute_delta(before, after)
    assert delta == {"ram_pct": 50.0}


def test_compute_delta_handles_new_keys_and_nones() -> None:
    """Verifies DeltaObserver handles new keys or None values."""
    observer = DeltaObserver(ignored_keys=set())

    before = {"existing": None, "v1": 1}
    after = {"existing": None, "v1": 1, "new_key": "val"}

    delta = observer.compute_delta(before, after)
    assert delta == {"new_key": "val"}


def test_compute_delta_returns_empty_when_identical() -> None:
    """Verifies DeltaObserver returns empty dict when states are identical."""
    observer = DeltaObserver(ignored_keys=set())
    before = {"a": 1, "b": "test"}
    after = {"a": 1, "b": "test"}

    assert observer.compute_delta(before, after) == {}


def test_merge_effects_strategies() -> None:
    """Verifies merge_effects for all merge strategies."""
    obs_update = DeltaObserver(merge_strategy="update")
    obs_preserve = DeltaObserver(merge_strategy="preserve_existing")
    obs_overwrite = DeltaObserver(merge_strategy="overwrite")

    existing = {"door_open": False, "has_key": True}
    delta = {"door_open": True, "fresh_predicate": 100}

    assert obs_update.merge_effects(existing, delta) == {
        "door_open": True,
        "has_key": True,
        "fresh_predicate": 100,
    }

    assert obs_preserve.merge_effects(existing, delta) == {
        "door_open": False,
        "has_key": True,
        "fresh_predicate": 100,
    }

    assert obs_overwrite.merge_effects(existing, delta) == {
        "door_open": True,
        "fresh_predicate": 100,
    }
