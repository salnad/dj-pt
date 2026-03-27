"""Optional prompt-optimization integration points."""

from __future__ import annotations


def prompt_optimization_available() -> bool:
    try:
        import dspy  # noqa: F401
    except ImportError:
        return False
    return True
