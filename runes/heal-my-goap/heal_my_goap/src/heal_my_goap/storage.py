"""JSON-file storage for synthesized GOAP actions."""

import hashlib
import json
import os
from abc import ABC, abstractmethod
from typing import Any

from heal_my_goap.models import Action, Gap


class BaseActionStorage(ABC):
    """Abstract interface for Action persistence layers."""

    @abstractmethod
    def save_action(
        self, action: Action, code_payload: str | None = None
    ) -> str:
        """Persists an Action model and returns its canonical SHA-256 hash.

        Args:
            action: Action instance to persist.
            code_payload: Optional string of code associated with action.

        Returns:
            SHA-256 hash string for the stored action.
        """

    @abstractmethod
    def load_actions(self) -> list[Action]:
        """Loads all persisted Action models.

        Returns:
            List of Action models.
        """

    @abstractmethod
    def find_action_for_gap(self, gap: Gap) -> Action | None:
        """Finds an action in storage matching missing gap predicates.

        Args:
            gap: Diagnostic Gap object.

        Returns:
            Matching Action instance if found, None otherwise.
        """

    @abstractmethod
    def clear(self) -> None:
        """Clears all stored actions."""


class ActionStorage(BaseActionStorage):
    """JSON-file based persistence layer for synthesized GOAP actions.

    Attributes:
        file_path: Target JSON file path string.
    """

    def __init__(self, file_path: str = ".goap_actions.json") -> None:
        """Initializes ActionStorage.

        Args:
            file_path: Target file path string for JSON persistence.
        """
        self.file_path = file_path

    def compute_action_hash(
        self,
        preconditions: dict[str, Any],
        effects: dict[str, Any],
        code_payload: str | None = None,
    ) -> str:
        """Computes canonical SHA-256 hash for an action specification.

        Args:
            preconditions: Preconditions mapping.
            effects: Effects mapping.
            code_payload: Optional executable code payload.

        Returns:
            Canonical hex SHA-256 string.
        """
        payload_repr = code_payload or ""
        canonical_str = json.dumps(
            {
                "preconditions": preconditions,
                "effects": effects,
                "code_payload": payload_repr,
            },
            sort_keys=True,
        )
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    def _read_data(self) -> dict[str, dict[str, Any]]:
        """Reads stored action dictionary data from disk.

        Returns:
            Dictionary mapping SHA-256 hashes to action specifications.
        """
        if not os.path.exists(self.file_path):
            return {}
        try:
            with open(self.file_path, encoding="utf-8") as f:
                data: dict[str, dict[str, Any]] = json.load(f)
                return data
        except (json.JSONDecodeError, OSError):
            return {}

    def _write_data(self, data: dict[str, dict[str, Any]]) -> None:
        """Writes action dictionary data to disk.

        Args:
            data: Dictionary mapping SHA-256 hashes to action definitions.
        """
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def save_action(
        self, action: Action, code_payload: str | None = None
    ) -> str:
        """Saves an Action to disk.

        Args:
            action: Action instance.
            code_payload: Optional python code payload string.

        Returns:
            Calculated SHA-256 action hash string.
        """
        data = self._read_data()
        action_hash = self.compute_action_hash(
            action.preconditions, action.effects, code_payload
        )
        action_dict = {
            "name": action.name,
            "preconditions": action.preconditions,
            "effects": action.effects,
            "cost": action.cost,
            "code_payload": code_payload,
        }
        # Evict old hashes for same action name to prevent storage bloat
        data = {k: v for k, v in data.items() if v.get("name") != action.name}
        data[action_hash] = action_dict
        self._write_data(data)
        return action_hash

    def load_actions(self) -> list[Action]:
        """Loads all persisted actions from disk.

        Returns:
            List of Action objects.
        """
        data = self._read_data()
        actions: list[Action] = []
        for item in data.values():
            action = Action(
                name=str(item["name"]),
                preconditions=dict(item["preconditions"]),
                effects=dict(item["effects"]),
                cost=int(item.get("cost", 10)),
            )
            actions.append(action)
        return actions

    def find_action_for_gap(self, gap: Gap) -> Action | None:
        """Finds matching action in storage for missing gap.

        Args:
            gap: Diagnostic Gap object.

        Returns:
            Matching Action if present, None otherwise.
        """
        actions = self.load_actions()
        for action in actions:
            if gap.is_satisfied_by_effects(action.effects):
                return action
        return None

    def clear(self) -> None:
        """Deletes the persistence storage file from disk."""
        if os.path.exists(self.file_path):
            try:
                os.remove(self.file_path)
            except OSError:
                pass
