"""Registry so test_determinism can replay every scripted scenario twice (FR-029)."""

from collections.abc import Callable

SCENARIOS: dict[str, Callable[[], list]] = {}


def scenario(name: str):
    """Decorator: register a zero-arg function that returns script items."""

    def deco(fn: Callable[[], list]) -> Callable[[], list]:
        SCENARIOS[name] = fn
        return fn

    return deco
