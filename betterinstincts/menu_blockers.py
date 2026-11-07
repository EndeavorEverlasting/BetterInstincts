"""Main-menu blocking overlays the host must dismiss before Load Game.

LOCAL_OBSERVED 2026-11-07 bi002-lablab-reboot (1.121.361.1020 DX11): after reboot,
EA "MEMORY BOOST IS NOW ON" modal covered Load Game. Dismiss via modal X only —
never Resume, never READ FAQ (leaves host lane).

Pure policy + coordinate registry. SendInput belongs to scripts/menu_blockers.py.
"""
from __future__ import annotations

from typing import Mapping, Sequence

# Borderless 1920x1080 LOCAL_OBSERVED dismiss click (modal X top-right).
MEMORY_BOOST_DISMISS_X = (1427, 188)
FORBIDDEN = frozenset({"RESUME", "READ_FAQ", "STORE_TAB", "PLAY_SCENARIO"})


class MenuBlockerError(ValueError):
    pass


def blockers() -> tuple[dict, ...]:
    return (
        {
            "id": "memory_boost_on",
            "scene_id": "memory_boost_modal",
            "title": "MEMORY BOOST IS NOW ON",
            "dismiss_step": "DISMISS_MEMORY_BOOST",
            "click": list(MEMORY_BOOST_DISMISS_X),
            "forbidden": sorted(FORBIDDEN),
            "next_after_dismiss": "main_menu",
            "proof_ceiling": "COORDINATE_HINT_NOT_LIVE_CERT",
            "observed": {
                "run_id": "bi002-lablab-reboot",
                "game_version": "1.121.361.1020",
                "date": "2026-11-07",
                "capture_ref": "capture:memory-boost-modal-before",
            },
        },
    )


def plan_dismiss(observed_ids: Sequence[str] | None = None) -> dict:
    """Order host dismiss steps for known menu blockers.

    If observed_ids is None, return the full durable fallback chain (fail-open to
    try Memory Boost dismiss before Load Game). Explicit empty list means none.
    """
    catalog = {row["id"]: row for row in blockers()}
    if observed_ids is None:
        ordered = list(blockers())
    else:
        ordered = []
        for bid in observed_ids:
            if bid not in catalog:
                raise MenuBlockerError("UNKNOWN_MENU_BLOCKER:" + bid)
            ordered.append(catalog[bid])
    return {
        "state": "MENU_BLOCKER_PLAN",
        "steps": [
            {
                "step": row["dismiss_step"],
                "blocker_id": row["id"],
                "click": row["click"],
                "forbidden": row["forbidden"],
                "scene_id": row["scene_id"],
            }
            for row in ordered
        ],
        "forbidden": sorted(FORBIDDEN),
        "proof_ceiling": "HOST_MENU_BLOCKER_PLAN_NOT_SCREEN_PROOF",
    }


def assert_safe_action(action: str) -> None:
    if action.upper() in FORBIDDEN or action in FORBIDDEN:
        raise MenuBlockerError("FORBIDDEN_MENU_ACTION:" + action)
