#!/usr/bin/env python3
"""CLI for per-profile lot floor maps (ensure / ingest / show)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from betterinstincts.lot_floor_map import (
    LotFloorMapError,
    assess_interaction_against_memorial,
    ensure_floor_map,
    floor_map_path,
    ingest_parts_buy_observations,
    invalidate_memorial,
    list_remap_targets,
    load_contract,
    load_floor_map,
    memorialize_object,
    on_build_mode_entered,
    record_room_landmarks,
    save_floor_map,
)
from betterinstincts.room_map_traverse import (
    DEFAULT_LANDMARK_HINT,
    plan_room_map_traverse,
)
from betterinstincts.camera_traverse import CameraTraverseError


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Lot floor map (per installation profile)")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("catalog")
    ens = sub.add_parser("ensure", help="Ensure skeleton floor map for profile+lot")
    ens.add_argument("--profile-id", default="default")
    ens.add_argument("--lot-key", required=True)
    bld = sub.add_parser("on-build", help="Simulate Build-mode auto-ensure trigger")
    bld.add_argument("--profile-id", default="default")
    bld.add_argument("--lot-key", required=True)
    sh = sub.add_parser("show", help="Show floor map doc")
    sh.add_argument("--profile-id", default="default")
    sh.add_argument("--lot-key", required=True)
    ing = sub.add_parser("ingest-parts-buy", help="Seed from parts-buy click ledger")
    ing.add_argument("--profile-id", default="default")
    ing.add_argument("--lot-key", default="household-n4-lab")
    ing.add_argument(
        "--ledger",
        type=Path,
        default=ROOT / "dist/game-host/parts-buy/click-ledger.v1.json",
    )
    rtp = sub.add_parser(
        "room-traverse-plan",
        help="Offline ROOM_MAP_TRAVERSE algorithm plan (no SendInput)",
    )
    rtp.add_argument("--goal-id", default=DEFAULT_LANDMARK_HINT["goal_id"])
    rtp.add_argument("--target-kind", default=DEFAULT_LANDMARK_HINT["target_kind"])
    rtp.add_argument("--target-id", default="")
    rtp.add_argument(
        "--seed-landmark",
        action="append",
        default=[],
        help="Repeatable landmark kinds (default: dining table + rug cluster)",
    )
    rec = sub.add_parser(
        "record-room-landmarks",
        help="Write dining/rugs→workbench graph into profile floor map",
    )
    rec.add_argument("--profile-id", default="default")
    rec.add_argument("--lot-key", default="household-n4-lab")
    rec.add_argument("--workbench-x", type=int, default=None)
    rec.add_argument("--workbench-y", type=int, default=None)
    rec.add_argument("--dining-x", type=int, default=None)
    rec.add_argument("--dining-y", type=int, default=None)
    rec.add_argument("--rug-x", type=int, default=None)
    rec.add_argument("--rug-y", type=int, default=None)
    rec.add_argument("--capture-ref", default="")
    rec.add_argument("--camera-revision", default="")
    mem = sub.add_parser("memorialize", help="Freeze a mapped object until it changes")
    mem.add_argument("--profile-id", default="default")
    mem.add_argument("--lot-key", required=True)
    mem.add_argument("--object-id", required=True)
    mem.add_argument(
        "--expect",
        action="append",
        default=[],
        help="Expected interaction label (repeatable), e.g. Order",
    )
    mem.add_argument("--note", default="")
    inv = sub.add_parser("invalidate", help="Mark memorialized object STALE_NEEDS_REMAP")
    inv.add_argument("--profile-id", default="default")
    inv.add_argument("--lot-key", required=True)
    inv.add_argument("--object-id", required=True)
    inv.add_argument(
        "--reason",
        default="EXPECTED_INTERACTION_MISSING",
        choices=[
            "EXPECTED_INTERACTION_MISSING",
            "WRONG_CONTROL_ON_MEMORIALIZED_TARGET",
            "EXPLICIT_OPERATOR_REMAP",
            "OBJECT_GONE_FROM_TOP_DOWN_CENSUS",
        ],
    )
    inv.add_argument("--observed", action="append", default=[], help="Observed pie labels")
    inv.add_argument("--note", default="")
    asm = sub.add_parser(
        "assess-interaction",
        help="Keep memorial or invalidate when expected interactions missing",
    )
    asm.add_argument("--profile-id", default="default")
    asm.add_argument("--lot-key", required=True)
    asm.add_argument("--object-id", required=True)
    asm.add_argument("--observed", action="append", default=[], help="Observed pie labels")
    rq = sub.add_parser("remap-queue", help="List STALE_NEEDS_REMAP object ids")
    rq.add_argument("--profile-id", default="default")
    rq.add_argument("--lot-key", required=True)
    args = p.parse_args(argv)

    try:
        if args.command == "catalog":
            cfg = load_contract()
            result = {
                "object_kinds": cfg.get("object_kinds"),
                "paths": cfg.get("paths"),
                "graph": cfg.get("graph"),
                "auto_on_build": cfg.get("auto_on_build"),
                "storage": cfg.get("storage"),
                "execute_allowed": False,
                "proof_ceiling": cfg["proof_ceiling"],
            }
        elif args.command == "ensure":
            result = ensure_floor_map(profile_id=args.profile_id, lot_key=args.lot_key)
        elif args.command == "on-build":
            result = on_build_mode_entered(
                profile_id=args.profile_id, lot_key=args.lot_key
            )
        elif args.command == "show":
            path = floor_map_path(profile_id=args.profile_id, lot_key=args.lot_key)
            result = load_floor_map(path) if path.is_file() else {"missing": str(path)}
        elif args.command == "ingest-parts-buy":
            if not args.ledger.is_file():
                raise LotFloorMapError("PARTS_BUY_LEDGER_MISSING")
            ledger = json.loads(args.ledger.read_text(encoding="utf-8"))
            # Append live computer HIT observation from 20261110 session
            ledger.setdefault("targets", {})["live.desk_computer"] = {
                "client_xy": [1299, 280],
                "status": "OBSERVED_COMPUTER_PIE_20261110",
                "note": "Green progress-bar computer; pie opened Write/Play/Career/More",
            }
            ledger.setdefault("targets", {})["live.desk_laptop"] = {
                "client_xy": [1000, 378],
                "status": "CANDIDATE",
            }
            result = ingest_parts_buy_observations(
                ledger, profile_id=args.profile_id, lot_key=args.lot_key
            )
        elif args.command == "room-traverse-plan":
            seeds = args.seed_landmark or list(DEFAULT_LANDMARK_HINT["seed_landmarks"])
            result = plan_room_map_traverse(
                goal_id=args.goal_id,
                target_kind=args.target_kind,
                target_id=args.target_id or None,
                seed_landmarks=seeds,
                adjacency_note=str(DEFAULT_LANDMARK_HINT["adjacency_note"]),
            )
        elif args.command == "record-room-landmarks":
            def _xy(x, y):
                if x is None or y is None:
                    return None
                return [int(x), int(y)]

            result = record_room_landmarks(
                profile_id=args.profile_id,
                lot_key=args.lot_key,
                workbench_xy=_xy(args.workbench_x, args.workbench_y),
                dining_xy=_xy(args.dining_x, args.dining_y),
                rug_xy=_xy(args.rug_x, args.rug_y),
                capture_ref=args.capture_ref,
                camera_revision=args.camera_revision or None,
            )
        elif args.command == "memorialize":
            if not args.expect:
                raise LotFloorMapError("EXPECTED_INTERACTIONS_REQUIRED")
            path = floor_map_path(profile_id=args.profile_id, lot_key=args.lot_key)
            doc = load_floor_map(path)
            row = memorialize_object(
                doc,
                object_id=args.object_id,
                expected_interactions=args.expect,
                note=args.note,
            )
            save_floor_map(doc, path)
            result = {
                "state": "MEMORIALIZED",
                "path": str(path),
                "object": row,
                "revision": doc["revision"],
                "execute_allowed": False,
            }
        elif args.command == "invalidate":
            path = floor_map_path(profile_id=args.profile_id, lot_key=args.lot_key)
            doc = load_floor_map(path)
            row = invalidate_memorial(
                doc,
                object_id=args.object_id,
                reason=args.reason,
                observed_interactions=args.observed,
                note=args.note,
            )
            save_floor_map(doc, path)
            result = {
                "state": "STALE_NEEDS_REMAP",
                "path": str(path),
                "object": row,
                "revision": doc["revision"],
                "execute_allowed": False,
            }
        elif args.command == "assess-interaction":
            path = floor_map_path(profile_id=args.profile_id, lot_key=args.lot_key)
            doc = load_floor_map(path)
            result = assess_interaction_against_memorial(
                doc,
                object_id=args.object_id,
                observed_interactions=args.observed,
            )
            if result.get("state") == "INVALIDATED_NEEDS_REMAP":
                save_floor_map(doc, path)
                result["path"] = str(path)
                result["revision"] = doc["revision"]
        elif args.command == "remap-queue":
            path = floor_map_path(profile_id=args.profile_id, lot_key=args.lot_key)
            doc = load_floor_map(path) if path.is_file() else {"objects": {}}
            result = {
                "state": "REMAP_QUEUE",
                "path": str(path),
                "stale_object_ids": list_remap_targets(doc),
                "execute_allowed": False,
            }
        else:
            raise LotFloorMapError("UNKNOWN_COMMAND")
    except (LotFloorMapError, CameraTraverseError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
