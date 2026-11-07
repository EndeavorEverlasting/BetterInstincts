#!/usr/bin/env python3
"""Execute the durable Sims host-menu reboot journey.

Codified transitions (not agentic rediscovery):
  splash wait → dismiss MEMORY BOOST → LOAD GAME → Play LabLab
  → pick LabLab domicile on map → lot Play
  → SELECT A SIM TO PLAY (Charlee) → Play into Live

Resume from any known scene:
  python -m scripts.host_menu run --from-scene select_sim_to_play --process-id PID --execute

Never Resume / Delete / Richardson.

Examples:
  python -m scripts.host_menu plan --journey reboot
  python -m scripts.host_menu plan --from-scene manage_worlds_or_map
  python -m scripts.host_menu run --journey reboot --process-id PID --execute --run-id bi002-lablab-reboot
  python -m scripts.host_menu run --from-scene select_sim_to_play --process-id PID --execute
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from betterinstincts.host_menu import HostMenuError, plan_from_scene, plan_journey
from betterinstincts.menu_blockers import assert_safe_action
from scripts.win32_input import send_click as _send_click

OUTPUT = ROOT / "dist" / "game-host"


class GateError(ValueError):
    pass


def _focus(process_id: int | None) -> None:
    from scripts.game_host import focus

    focus(process_id=process_id)


def run_journey(
    *,
    journey: str,
    process_id: int | None,
    execute: bool,
    from_step: str | None,
    from_scene: str | None,
    run_id: str | None,
    settle_sec: float,
) -> dict:
    if from_scene:
        plan = plan_from_scene(from_scene, journey=journey)
    else:
        plan = plan_journey(journey, from_step=from_step)
    out: dict = {
        "plan": plan,
        "execute": bool(execute),
        "run_id": run_id,
        "process_id": process_id,
        "from_scene": from_scene,
        "proof_ceiling": "HOST_MENU_CLICK_DISPATCH_NOT_LIVE_CERT",
    }
    if plan.get("state") == "HOST_MENU_ALREADY_AT_TERMINAL":
        out["state"] = "ALREADY_AT_TERMINAL"
        out["next"] = plan.get("next")
        return out
    if not execute:
        out["state"] = "DRY_RUN"
        out["next"] = (
            "python -m scripts.host_menu run --from-scene SCENE --process-id PID "
            "--execute --run-id RUN"
        )
        return out
    if sys.platform != "win32":
        raise GateError("LOCAL_WINDOWS_GAME_HOST_REQUIRED")
    _focus(process_id)
    dispatched = []
    for step in plan["steps"]:
        assert_safe_action(step["gate"])
        if step["execution"] == "HOST_WAIT_ONLY":
            dispatched.append({
                "id": step["id"],
                "state": "WAIT_DEFERRED_TO_CALLER",
                "note": step.get("note"),
            })
            continue
        if step["execution"] != "HOST_SENDINPUT":
            raise GateError("UNSUPPORTED_EXECUTION:" + str(step["execution"]))
        x, y = step["click"]
        _send_click(int(x), int(y))
        time.sleep(max(0.3, min(5.0, settle_sec)))
        dispatched.append({
            "id": step["id"],
            "gate": step["gate"],
            "substep": step.get("substep"),
            "scene_id": step.get("scene_id"),
            "click": [x, y],
            "state": "CLICK_DISPATCHED",
            "to": step["to"],
            "forbidden": step.get("forbidden"),
        })
    out["steps"] = dispatched
    out["state"] = "HOST_MENU_JOURNEY_DISPATCHED"
    out["next"] = (
        "python -m scripts.game_capture --process-id PID --analyze; "
        "confirm Live CONTENT_PRESENT before needs clicks; "
        "use ENTER_BUILD_BUY_UNSTICK if black"
    )
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    plan_p = sub.add_parser("plan")
    plan_p.add_argument("--journey", default="reboot")
    plan_p.add_argument("--from-step", default=None)
    plan_p.add_argument("--from-scene", default=None,
                        help="Resume at scene substeps (e.g. select_sim_to_play)")
    run_p = sub.add_parser("run")
    run_p.add_argument("--journey", default="reboot")
    run_p.add_argument("--from-step", default=None,
                       help="Resume journey at this transition id (e.g. play_lablab_slot)")
    run_p.add_argument("--from-scene", default=None,
                       help="Resume at scene substeps (domicile/map/profile/…)")
    run_p.add_argument("--process-id", type=int, default=None)
    run_p.add_argument("--execute", action="store_true")
    run_p.add_argument("--run-id", default=None)
    run_p.add_argument("--settle-sec", type=float, default=1.2)
    run_p.add_argument("--receipt", type=Path, default=None)
    args = p.parse_args(argv)
    try:
        if args.command == "plan":
            if args.from_scene:
                result = plan_from_scene(args.from_scene, journey=args.journey)
            else:
                result = plan_journey(args.journey, from_step=args.from_step)
        else:
            result = run_journey(
                journey=args.journey,
                process_id=args.process_id,
                execute=bool(args.execute),
                from_step=args.from_step,
                from_scene=args.from_scene,
                run_id=args.run_id,
                settle_sec=float(args.settle_sec),
            )
            if args.receipt is not None:
                path = args.receipt if args.receipt.is_absolute() else ROOT / args.receipt
                path = path.resolve()
                if not path.is_relative_to(OUTPUT.resolve()):
                    raise GateError("RECEIPT_OUTSIDE_DIST_GAME_HOST")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                                encoding="utf-8")
                result["receipt"] = str(path.relative_to(ROOT))
        print(json.dumps(result, sort_keys=True))
        return 0
    except (HostMenuError, GateError, OSError, ValueError, TypeError) as exc:
        print(json.dumps({"state": "BLOCKED", "reason": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
