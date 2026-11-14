"""Read-only local opportunity inspector: no game focus, clicks, keys or save reads.

A host-local agent supplies one independently inspected, fresh JSON snapshot.
Run from repo root: python -m scripts.opportunistic_actions --observation PATH
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from betterinstincts.opportunistic_actions import (
    OpportunisticActionError, plan_school_homework_window, plan_targeted_chat_whim,
)

MAX_OBSERVATION_BYTES = 32_000
SIX = frozenset({"hunger", "bladder", "energy", "hygiene", "fun", "social"})


def inspect(path: Path) -> dict:
    if (path.is_symlink() or not path.is_file()
            or path.stat().st_size > MAX_OBSERVATION_BYTES):
        raise OpportunisticActionError("OPPORTUNITY_FILE_UNSAFE")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise OpportunisticActionError("OPPORTUNITY_OBSERVATION_OBJECT_REQUIRED")
    needs = raw.get("needs")
    if (not isinstance(needs, dict) or set(needs) != SIX
            or any(type(x) not in (float, int) or not 0 <= x <= 1
                   for x in needs.values())):
        raise OpportunisticActionError("SIX_NEEDS_REQUIRED")
    if not isinstance(raw.get("queue"), list):
        raise OpportunisticActionError("QUEUE_REQUIRED")
    context = {key: raw.get(key) for key in (
        "capture_ref", "school_phase", "school_day_active", "location_kind",
        "homework_pending", "inventory_has_homework", "player_directed",
        "already_busy", "multitasking",
    )}
    snap = {"capture_ref": context["capture_ref"],
            "queue": raw["queue"], "player_directed": context["player_directed"] is True,
            "already_busy": context["already_busy"] is True,
            "survival_critical": [key for key in ("hunger", "bladder", "energy")
                                  if needs[key] < 0.35],
            "multitasking": context["multitasking"]}
    homework = plan_school_homework_window(
        raw.get("school_homework_window"), capture_ref=snap["capture_ref"],
        school_phase=context["school_phase"] or "morning_free_time",
        school_day_active=context["school_day_active"] is True,
        location_kind=context["location_kind"] or "unknown",
        homework_pending=context["homework_pending"] is True,
        inventory_has_homework=context["inventory_has_homework"],
        queue=snap["queue"], player_directed=snap["player_directed"],
        already_busy=snap["already_busy"],
        survival_critical=snap["survival_critical"],
        multitasking=snap["multitasking"],
    )
    chat = plan_targeted_chat_whim(
        raw.get("whims") or [], raw.get("sim_library") or [],
        queued_social_targets=raw.get("queued_social_targets") or [],
        **snap,
    )
    return {
        "schema": "betterinstincts.opportunistic-inspection/v1",
        "school_homework_window": homework,
        "targeted_chat_whim": chat,
        "execute_allowed": False,
        "proof_ceiling": "OFFLINE_OBSERVATION_ONLY_NOT_SIM_ACTION",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observation", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(inspect(args.observation), indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError,
            json.JSONDecodeError, OpportunisticActionError) as exc:
        print(json.dumps({"state": "OPPORTUNITY_BLOCKED", "error": str(exc)},
                         sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
