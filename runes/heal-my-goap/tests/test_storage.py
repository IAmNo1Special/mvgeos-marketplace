"""Tests for JSON-file action storage persistence layer."""

from typing import Any
from unittest.mock import patch

import pytest

from heal_my_goap.models import Action, Gap
from heal_my_goap.storage import ActionStorage


@pytest.fixture
def temp_storage(tmp_path: Any) -> ActionStorage:
    """Fixture providing temporary ActionStorage instance."""
    json_file = str(tmp_path / "actions.json")
    return ActionStorage(file_path=json_file)


def test_canonical_hash_generation() -> None:
    """Verifies deterministic SHA-256 canonical hash computation."""
    storage = ActionStorage()
    hash1 = storage.compute_action_hash(
        preconditions={"has_key": True},
        effects={"door_open": True},
        code_payload="pass",
    )
    hash2 = storage.compute_action_hash(
        preconditions={"has_key": True},
        effects={"door_open": True},
        code_payload="pass",
    )
    hash3 = storage.compute_action_hash(
        preconditions={"has_key": True},
        effects={"door_open": True},
        code_payload="print('hello')",
    )
    assert hash1 == hash2
    assert hash1 != hash3


def test_save_load_clear_actions(temp_storage: ActionStorage) -> None:
    """Verifies saving, loading, and clearing actions in storage."""
    action = Action(
        name="synth_open_door_123",
        preconditions={"has_key": True},
        effects={"door_open": True},
        cost=10,
    )

    action_hash = temp_storage.save_action(action)
    assert isinstance(action_hash, str)

    loaded = temp_storage.load_actions()
    assert len(loaded) == 1
    assert loaded[0].name == "synth_open_door_123"
    assert loaded[0].preconditions == {"has_key": True}
    assert loaded[0].effects == {"door_open": True}

    temp_storage.clear()
    assert not temp_storage.load_actions()


def test_find_action_for_gap(temp_storage: ActionStorage) -> None:
    """Verifies searching stored actions by gap predicate matching."""
    action = Action(
        name="synth_find_key",
        preconditions={"in_room": True},
        effects={"has_key": True},
        cost=10,
    )
    temp_storage.save_action(action)

    gap = Gap(missing_predicate={"has_key": True})
    found = temp_storage.find_action_for_gap(gap)
    assert found is not None
    assert found.name == "synth_find_key"

    unmatched_gap = Gap(missing_predicate={"has_wand": True})
    assert temp_storage.find_action_for_gap(unmatched_gap) is None


def test_storage_clear_handles_oserror(temp_storage: ActionStorage) -> None:
    """Verifies clear() tolerates file removal OSError."""
    temp_storage.save_action(
        Action(
            name="synth_test",
            preconditions={},
            effects={"cleared": True},
            cost=10,
        )
    )
    with patch(
        "heal_my_goap.storage.os.remove",
        side_effect=OSError("Permission denied"),
    ):
        temp_storage.clear()
    assert temp_storage.load_actions()
