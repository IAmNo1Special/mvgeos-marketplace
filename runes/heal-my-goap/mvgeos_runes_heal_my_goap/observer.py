"""Runtime state delta observer for GOAP state formalization.

Provides ``BaseObserver`` and ``DeltaObserver`` to observe state differences
before and after action execution and compute observed predicate effects.
"""

from abc import ABC, abstractmethod
from typing import Any

from heal_my_goap.models import WorldState

__all__ = ["BaseObserver", "DeltaObserver"]

DEFAULT_IGNORED_KEYS: set[str] = {
    "uptime_minutes",
    "network_bytes_sent",
    "network_bytes_recv",
    "top_process_cpu_pct",
    "load_avg_1m",
    "cpu_usage_pct",
    "disk_io_read_bytes",
    "disk_io_write_bytes",
    "process_memory_rss",
}


class BaseObserver(ABC):
    """Abstract interface for GOAP runtime state observers."""

    @abstractmethod
    def compute_delta(
        self,
        before: dict[str, Any] | WorldState,
        after: dict[str, Any] | WorldState,
    ) -> dict[str, Any]:
        """Computes observed predicate changes between before and after states.

        Args:
            before: State dictionary or WorldState snapshot prior to execution.
            after: State dictionary or WorldState snapshot post execution.

        Returns:
            Dictionary of observed predicate key-value changes.
        """

    @abstractmethod
    def merge_effects(
        self,
        existing_effects: dict[str, Any],
        observed_delta: dict[str, Any],
    ) -> dict[str, Any]:
        """Merges newly observed deltas into an action's existing effects.

        Args:
            existing_effects: Existing action effects dictionary.
            observed_delta: Newly observed state delta dictionary.

        Returns:
            Merged effects dictionary according to the observer's policy.
        """


class DeltaObserver(BaseObserver):
    """Observes runtime state deltas and filters ambient OS noise.

    Attributes:
        ignored_keys: Set of predicate names to ignore during comparison.
        numeric_tolerance: Minimum threshold for numeric changes to record.
        merge_strategy: Policy for combining observed deltas with existing
            effects ("update", "preserve_existing", or "overwrite").
    """

    def __init__(
        self,
        ignored_keys: set[str] | None = None,
        numeric_tolerance: float = 1.0,
        merge_strategy: str = "update",
    ) -> None:
        """Initializes DeltaObserver.

        Args:
            ignored_keys: Custom set of keys to ignore, or None for defaults.
            numeric_tolerance: Threshold for float/int changes (default 1.0).
            merge_strategy: Merging policy: "update" (default),
                "preserve_existing", or "overwrite".
        """
        self.ignored_keys: set[str] = (
            set(ignored_keys)
            if ignored_keys is not None
            else set(DEFAULT_IGNORED_KEYS)
        )
        self.numeric_tolerance: float = numeric_tolerance
        self.merge_strategy: str = merge_strategy

    def compute_delta(
        self,
        before: dict[str, Any] | WorldState,
        after: dict[str, Any] | WorldState,
    ) -> dict[str, Any]:
        """Computes observed predicate changes between before and after states.

        Args:
            before: State dictionary or WorldState snapshot prior to execution.
            after: State dictionary or WorldState snapshot post execution.

        Returns:
            Dictionary mapping changed predicate names to their new values.
        """
        before_dict = (
            before.to_dict() if isinstance(before, WorldState) else before
        )
        after_dict = after.to_dict() if isinstance(after, WorldState) else after

        delta: dict[str, Any] = {}
        for key, after_val in after_dict.items():
            if key in self.ignored_keys:
                continue

            if key not in before_dict:
                delta[key] = after_val
                continue

            before_val = before_dict[key]
            if before_val is None and after_val is None:
                continue

            if isinstance(after_val, (int, float)) and isinstance(
                before_val, (int, float)
            ):
                if (
                    abs(float(after_val) - float(before_val))
                    >= self.numeric_tolerance
                ):
                    delta[key] = after_val
            elif before_val != after_val:
                delta[key] = after_val

        return delta

    def merge_effects(
        self,
        existing_effects: dict[str, Any],
        observed_delta: dict[str, Any],
    ) -> dict[str, Any]:
        """Merges newly observed deltas into an action's existing effects.

        Args:
            existing_effects: Existing action effects dictionary.
            observed_delta: Newly observed state delta dictionary.

        Returns:
            Merged effects dictionary matching configured merge_strategy.
        """
        if self.merge_strategy == "overwrite":
            return dict(observed_delta)
        elif self.merge_strategy == "preserve_existing":
            merged = dict(existing_effects)
            for k, v in observed_delta.items():
                if k not in merged:
                    merged[k] = v
            return merged
        else:  # "update" (default)
            merged = dict(existing_effects)
            merged.update(observed_delta)
            return merged
