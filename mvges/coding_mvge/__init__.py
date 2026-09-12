from __future__ import annotations

try:
    from .mvge import root_mvge
except ImportError:
    from coding_mvge.mvge import root_mvge

__all__ = ["root_mvge"]
