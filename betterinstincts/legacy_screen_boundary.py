"""Central fail-closed boundary for unadopted legacy desktop input scripts.

These scripts have raw Win32 focus/SendInput paths without shared idle, scene,
save and exact-target admission. A classification in a JSON inventory is not a
runtime permit. Deliberately no bypass flag, token, environment override, or
host-side Windows API. Convert each legacy script to the canonical
`admitted_screen_lease` contract with fresh observations, independent
regressions and a reviewed adapter status before replacing this rejection.
"""
from __future__ import annotations

from typing import NoReturn


class UnadoptedLiveEffectError(RuntimeError):
    """A risky legacy path refused before focus, keyboard or mouse mutation."""


def deny_unadopted_live_effect(adapter_path: str) -> NoReturn:
    """Fail closed for unadopted raw-screen paths, including imported callers.

    The caller's import/execute CLI remains compatible for read-only planning.
    Never infer authorization from --execute, a claimed idle cursor, a Windows
    PID alone, an agent instruction, or operator-screen-released.
    """
    if not isinstance(adapter_path, str) or not adapter_path.startswith("scripts/"):
        raise UnadoptedLiveEffectError("UNCLASSIFIED_LEGACY_ADAPTER_DENIED")
    raise UnadoptedLiveEffectError(
        "UNADOPTED_LEGACY_INPUT_DENIED:" + adapter_path
    )
