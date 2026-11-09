#!/usr/bin/env python3
"""CLI: School Join vs Send Alone click plan + post-click verification.

Evaluate-only by default. `plan --execute` is optional and gated: it needs a
measured layout, a prior dialog observation, the detached native SendInput
executor and an explicit --operator-screen-released flag. The Cursor
computer-use overlay is forbidden as an executor. A dispatched click is never a
Send Alone claim; run `verify` against a fresh post-click observation.

Examples:
  python -m scripts.school_attend_click plan
  python -m scripts.school_attend_click plan --candidate 960 600
  python -m scripts.school_attend_click verify --lot-kind home --no-school-hud --no-dialog --source PRINTWINDOW --age-seconds 5
  python -m scripts.school_attend_click verify --observation observation.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Callable, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from betterinstincts.school_attend_click import (
    CALIBRATION_SOURCES,
    REQUIRED_EXECUTOR,
    SchoolAttendClickError,
    plan_send_alone_click,
    verify_post_click,
)

MAX_OBSERVATION_BYTES = 64_000


def _dump(payload: dict) -> int:
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _load_observation(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_OBSERVATION_BYTES:
        raise SchoolAttendClickError("OBSERVATION_FILE_UNSAFE")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SchoolAttendClickError("OBSERVATION_MUST_BE_OBJECT")
    return data


def _default_dispatch(point: tuple[int, int]) -> dict:
    from scripts.cas_quiz_okay import click_okay

    return click_okay(None, 0.0, point=point)


def run_plan(args: argparse.Namespace, dispatch: Optional[Callable[[tuple[int, int]], dict]] = None) -> tuple[int, dict]:
    plan = plan_send_alone_click(
        executor=args.executor,
        measured_join_y=args.measured_join_y,
        calibration_source=args.calibration_source,
        dialog_observed=args.dialog_observed,
        candidate_xy=args.candidate,
        client_width=args.client[0],
        client_height=args.client[1],
        execute=args.execute,
    )
    if not args.execute:
        return 0, plan
    gate: list[str] = []
    if not plan["ready_to_execute"]:
        gate.extend(plan["blockers"])
    if not args.operator_screen_released:
        gate.append("OPERATOR_SCREEN_RELEASE_REQUIRED")
    if gate:
        plan["execute_refused"] = sorted(set(gate))
        return 3, plan
    result = (dispatch or _default_dispatch)(tuple(plan["target_xy"]))
    plan["dispatch"] = result
    plan["next"] = "RUN_VERIFY_WITH_FRESH_POST_CLICK_OBSERVATION_DISPATCH_IS_NOT_A_SEND_ALONE_CLAIM"
    return 0, plan


def main(argv: list[str] | None = None, dispatch: Optional[Callable[[tuple[int, int]], dict]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    p_plan = commands.add_parser("plan", help="Plan (evaluate-only) a Send Alone click")
    p_plan.add_argument("--client", nargs=2, type=int, metavar=("W", "H"), default=[1920, 1080])
    p_plan.add_argument("--measured-join-y", type=int, default=None, help="PrintWindow/operator-measured Join pill center y")
    p_plan.add_argument("--calibration-source", choices=sorted(CALIBRATION_SOURCES), default=None)
    p_plan.add_argument("--dialog-observed", action="store_true", help="Join/Send Alone dialog observed pre-click")
    p_plan.add_argument("--candidate", nargs=2, type=int, metavar=("X", "Y"), default=None, help="Score an explicit target point")
    p_plan.add_argument("--executor", default=REQUIRED_EXECUTOR)
    p_plan.add_argument("--execute", action="store_true", help="Gated; default false")
    p_plan.add_argument("--operator-screen-released", action="store_true")
    p_ver = commands.add_parser("verify", help="Verify a post-click observation")
    p_ver.add_argument("--observation", type=Path, default=None)
    p_ver.add_argument("--lot-kind", choices=["home", "school", "unknown"], default="unknown")
    p_ver.add_argument("--school-hud", dest="school_hud", action="store_true", default=None)
    p_ver.add_argument("--no-school-hud", dest="school_hud", action="store_false")
    p_ver.add_argument("--dialog", dest="dialog", action="store_true", default=None)
    p_ver.add_argument("--no-dialog", dest="dialog", action="store_false")
    p_ver.add_argument("--text-cue", action="append", default=[])
    p_ver.add_argument("--source", default=None)
    p_ver.add_argument("--age-seconds", type=float, default=None)
    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            code, plan = run_plan(args, dispatch)
            _dump(plan)
            return code
        if args.observation is not None:
            observation = _load_observation(args.observation)
        else:
            observation = {
                "lot_kind": args.lot_kind,
                "school_hud_visible": args.school_hud,
                "dialog_present": args.dialog,
                "text_cues": args.text_cue,
                "source": args.source,
                "age_s": args.age_seconds,
            }
        result = verify_post_click(observation)
        _dump(result)
        return 0 if result["passed"] else 4
    except (SchoolAttendClickError, OSError, ValueError, RuntimeError) as exc:
        print(json.dumps({"error": str(exc)}, indent=2, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
