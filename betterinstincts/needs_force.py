"""Plan critical-needs force routes — MAP_TRAVEL first, never in-frame walk thrash."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "needs-force.v1.json"
MAX_BYTES = 48_000


class NeedsForceError(ValueError):
    pass


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise NeedsForceError("NEEDS_FORCE_CONTRACT_UNSAFE")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    if cfg.get("schema") != "betterinstincts.needs-force/v1":
        raise NeedsForceError("BAD_NEEDS_FORCE_SCHEMA")
    if "IN_FRAME_WALK_THRASH" not in set(cfg.get("forbidden_always", [])):
        raise NeedsForceError("WALK_THRASH_MUST_STAY_FORBIDDEN")
    return cfg


def plan_force(
    *,
    location_kind: str = "unknown",
    objects_on_current_lot: bool = False,
    disposition: str = "OPTIMIZE",
) -> dict:
    """Return ordered host steps. Prefer Manage Worlds travel when off-lot."""
    cfg = load_contract()
    by_id = {row["id"]: row for row in cfg["steps"] if isinstance(row, dict)}
    if disposition == "EMULATE" and objects_on_current_lot:
        return {
            "state": "NEEDS_FORCE_SKIP_EMULATE_LOCAL",
            "route": "LOCAL_EMULATE",
            "steps": [],
            "forbidden": list(cfg["forbidden_always"]),
            "note": "Good local queue — listener emulates; no force travel.",
            "proof_ceiling": cfg.get("proof_ceiling"),
        }

    off_lot = location_kind in {"school", "community", "work", "unknown"} and not objects_on_current_lot
    if off_lot or location_kind != "home":
        ordered = [
            "pause_live",
            "cancel_fluff_queue",
            "open_manage_worlds",
            "save_and_go_manage_worlds_if_prompted",
            "select_home_lot_bargain_bend",
            "confirm_play_home_lot",
            "force_eat_home_fridge",
            "unpause_speed2",
        ]
        route = "MAP_TRAVEL"
    else:
        ordered = [
            "pause_live",
            "cancel_fluff_queue",
            "force_eat_home_fridge",
            "unpause_speed2",
        ]
        route = "LOCAL_OBJECT_AFTER_CANCEL_FLUFF"

    steps = []
    for sid in ordered:
        row = by_id.get(sid)
        if row is None:
            raise NeedsForceError("MISSING_FORCE_STEP:" + sid)
        steps.append({
            "id": sid,
            "gate": row.get("gate"),
            "execution": row.get("execution"),
            "click": row.get("click"),
            "note": row.get("note"),
        })
    return {
        "state": "NEEDS_FORCE_PLANNED",
        "route": route,
        "location_kind": location_kind,
        "disposition": disposition,
        "steps": steps,
        "forbidden": list(cfg["forbidden_always"]),
        "decision_rule": cfg.get("decision_rule"),
        "proof_ceiling": cfg.get("proof_ceiling"),
        "commands": cfg.get("host_commands"),
    }
